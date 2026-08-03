# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Vijdon Taxi — a taxi-dispatch backend for a ride-hailing service (Uzbekistan). It's a single Django app (`taxi/`) that serves three different front-ends (operator panel, driver app, client app) plus a Telegram bot, backing two thin Flutter WebView shells. UI strings, model `verbose_name`s, and most comments are in Uzbek — match that in new code.

## Commands

```bash
# Environment
source venv/bin/activate
pip install -r requirements.txt

# Dev server
python manage.py runserver

# DB
python manage.py makemigrations taxi
python manage.py migrate
python manage.py createsuperuser

# Tests (taxi/tests.py is currently just Django's empty boilerplate — no real
# suite exists yet; this is how you'd run one if you add tests)
python manage.py test
python manage.py test taxi.tests.SomeTestCase.test_method   # single test

# Static files (whitenoise serves these in production)
python manage.py collectstatic

python manage.py shell
```

Flutter apps (`vijdon_driver_app/`, `vijdon_client_app/`) are built independently from within their own directories (`flutter pub get`, `flutter run`, `flutter build apk`) — they are not part of the Django build.

Settings live in `config/settings.py` (DB credentials, `TELEGRAM_BOT_TOKEN`, VAPID keys for web push, `SITE_URL` are hardcoded there rather than via env vars — this is a small-scale single-deployment setup, not 12-factor). `DATABASES` is PostgreSQL only; ignore the stray `db.sqlite3` file in the repo root if you see it, it isn't wired up. Production deploys via WSGI/Passenger (see `TaxiConfig._should_start_scheduler` in `taxi/apps.py`, which special-cases `runserver`).

## Architecture

### Three server-rendered front-ends, one Django app

| Surface | URL prefix | Views/urls | Auth | Templates |
|---|---|---|---|---|
| Operator panel | `/panel/` | `views.py` (~2700 lines) + `urls.py` | Django session, `@login_required(login_url='taxi:panel_login')` | `taxi/templates/taxi/` |
| Driver app | `/driver/` | `driver_views.py` + `driver_urls.py` | Custom `@driver_login_required` (session → `request.user.driver_profile`, redirects to `driver/pending.html` if not yet approved) | `taxi/templates/driver/` |
| Client app | `/client/` | `client_views.py` + `client_urls.py` | Custom `@client_login_required` (session → `request.user.client_profile`, renders `client/blocked.html` if blocked) | `taxi/templates/client/` |

All three are wired from `config/urls.py` via `include()`. Root `/` redirects to `/panel/`.

### The Flutter apps are WebView shells, not native UIs

`vijdon_driver_app` and `vijdon_client_app` are thin `webview_flutter` wrappers (see `main.dart`'s `kBaseUrl`) that load the live `/driver/` and `/client/` web apps described above. The actual UI and business logic live in Django templates, not Dart. The Flutter layer only adds native-only capabilities on top: a foreground service for background GPS + order polling (`core/order_poll_task_handler.dart`), native push notifications (`core/notification_service.dart`), camera/permissions.

### A separate token-authenticated REST API also exists (`api_views.py` + `serializers.py`)

Endpoints like `/api/driver/register/`, `/api/orders/<id>/accept/`, etc., using DRF `TokenAuthentication` (see `REST_FRAMEWORK` in settings and `rest_framework.authtoken`). This duplicates a lot of what `driver_views.py` does for the web app. The shipped Flutter apps use the WebView approach above, not this API — before assuming code changes need to touch both `driver_views.py` and `api_views.py`, check which one actually matters for the surface you're changing.

### Telegram bot is hand-rolled HTTP, not aiogram

`aiogram` is in `requirements.txt` but unused. The bot is implemented via raw `urllib` calls to the Telegram Bot API (`send_telegram`, `send_telegram_photo` in `utils.py`), with inbound updates handled by a webhook view (`operator_bot_webhook`, mounted at `/panel/bot/operator-webhook/`). It serves two roles:
1. **Notifications** — order events, low balance, daily/weekly/monthly reports pushed to configured Telegram group(s).
2. **An admin command bot** — ops staff can run text commands directly in the group/DM (`/bekor <id>`, `/qayta <id>`, `/balans`, `/tarix <id>`, `/tolovtasdiq <id>`, etc.), dispatched through a large if/elif chain inside `operator_bot_webhook`.

### In-process scheduler for recurring Telegram reports

`TaxiConfig.ready()` (`taxi/apps.py`) starts a daemon thread (`scheduler.start()`, only under real `runserver`/WSGI, not one-off `manage.py` commands) that ticks every 30s and fires report functions from `utils.py` (`tg_daily_summary`, `tg_weekly_summary`, `tg_monthly_financial_report`, etc.) at scheduled hours. Each is gated by an atomic conditional `UPDATE` against a `BotSettings.last_*_date` field so it fires exactly once per day even with multiple worker processes. `taxi/management/commands/send_*.py` wrap these *same* `utils.py` functions for external cron — they're an alternative trigger for identical logic, not a separate implementation.

### Order lifecycle & commission model

`Order.STATUS_CHOICES`: `pending → accepted → on_way → arrived → completed`, or `cancelled` at any point. `Order.ACTIVE_STATUSES = ('accepted', 'on_way', 'arrived')`.

- **Dispatch** (`dispatch_order()` in `utils.py`): tries the nearest driver by haversine distance, up to `TariffSettings.max_dispatch_attempts`, tracking rejections via `order.rejected_by`. If the order has no lat/lng (manually-typed address) or attempts run out, it falls back to a shared pending pool visible to all drivers (`dispatched_to = None`).
- **Accepting** an order deducts `Order.commission` (a snapshot of `TariffSettings.commission` taken at order creation) from `Driver.balance` immediately (`driver_views.py`, `update_order_status`, action=`accept`).
- **Cancelling or deleting** an order that's still in `ACTIVE_STATUSES` refunds that commission via the shared `_refund_order_commission()` helper in `views.py`. It's called from `order_update_status`, `order_delete`, the bot's `/bekor`, plus the pre-existing `order_cancel_reassign` and bot `/qayta` (reopen) flows.
- Drivers **can self-cancel** an accepted order from the driver app (`driver_views.py`, `driver_order_action`, action=`cancel`), but must pick a reason first via the shared cancel-reason modal (`taxi/templates/driver/base.html`, `openCancelReasonModal()`). Reason keys are defined once in `DRIVER_CANCEL_REASONS` (`driver_views.py`) — each maps to display text plus a `reassign` flag. Commission is always refunded (via `_refund_order_commission()`). If `reassign` is `True` (driver-fault reasons: car trouble, got busy, incident en route), the order is reopened to other drivers exactly like the operator's `order_cancel_reassign` (status back to `pending`, `rejected_by` gets the cancelling driver, `dispatch_order()` re-runs). If `False` (client-fault reasons, or free-text "boshqa"), the order is fully `cancelled` with no re-dispatch. The chosen/typed reason is stored on `Order.cancel_reason`.

### The balance ledger (`BalanceLog`) has a known accuracy gap

`BalanceLog` records manual admin add/deduct, approved topup requests, and commission refunds — but **not** the automatic commission deduction that happens on order-accept (see above; that code path mutates `Driver.balance` directly with no `BalanceLog` entry). So aggregating `BalanceLog` for "total commission collected" undercounts reality. For accurate commission revenue, sum `Order.commission` over `status='completed'` orders instead — this is what the Moliya (Finance) section does. Keep this in mind before trusting any new "total deducted" metric built from `BalanceLog` alone.

### Panel sections (`/panel/`, sidebar defined in `taxi/templates/taxi/base.html`)

- **Dashboard** (`panel_dashboard`) — today's KPIs, weekly trend + week-over-week growth, and alert cards (low-balance drivers, inactive drivers, aging topup requests, expiring legal documents, open security incidents).
- **Statistika** (`statistics`) — order/revenue analytics over a period or custom date range, hourly load, top pickup addresses, top drivers/clients.
- **Moliya** (`finance_dashboard`) — GMV vs. company commission revenue vs. driver share, payment-type/car-type breakdown, top drivers by commission (see the ledger gap above).
- **To'lovlar** (`topup_list`) — balance topup requests (approve/reject with a reason) plus the full `BalanceLog` history (paginated, filterable), PDF receipt generation (`build_balance_receipt_pdf` in `utils.py`), and manual recharge.
- **Xavfsizlik** (`security_dashboard`) — `SecurityIncident` log (defamation/blackmail/legal-dispute tracking) and `LegalDocument` store (license/certificate uploads with expiry tracking).
- Drivers/Clients/Orders/SOS/Tasks/contract e-signature/flyer-voucher-redemption/bot & tariff & maps & SMS & AI settings round out the rest — fairly standard CRUD-style panel views.

Both **Statistika** and **Moliya** share one date-range helper — `_statistics_range(request)` in `views.py` parses `?start=&end=` or `?period=week|month|year`. Reuse it for any new date-ranged report instead of reimplementing the parsing.

### AI growth-insights feature

`AiSettings` (singleton) holds an OpenAI API key + model choice, configured from the panel. `generate_growth_insights()` (`utils.py`) calls OpenAI to produce Uzbek-language growth recommendations and flags a "top driver/client of the month," which ops can mark as rewarded (`AiRewardLog`, unique per person per month via a `UniqueConstraint`).

### Singleton "site settings" models

`BotSettings`, `TariffSettings`, `SmsSettings`, `AiSettings`, `MapsSettings`, `ContractSettings` are all get-or-create singletons: `save()` forces `pk=1`, and a `.get()` classmethod fetches/creates the one row. `BotSettings` additionally holds ~30 `notify_*` booleans (one per notification type) and the `last_*_date` fields the scheduler uses for its once-per-day guard. Follow this same singleton pattern for any new "site-wide config" model.

## Conventions

- **Local imports inside function bodies** (e.g. `from taxi.models import X` inside a view) are the norm in `views.py`/`driver_views.py`/`utils.py`, apparently to avoid circular imports between those three large modules. Match the existing style in whichever file you're editing rather than hoisting imports to module scope.
- Panel templates extend `taxi/templates/taxi/base.html`, use Tailwind utility classes, and load Chart.js per-page via `{% block extra_js %}` for any charts. Every modal is driven by the shared `openModal()`/`closeModal()` JS helpers defined in `base.html` — new modals should use those rather than ad-hoc show/hide code.
- Badge counts shown in the sidebar nav (e.g. pending topups, open security incidents) come from `taxi/context_processors.py`, injected into every template's context — add new sidebar badges there, not per-view.
