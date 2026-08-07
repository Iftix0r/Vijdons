from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Order, Driver, Client, TariffSettings, ChatMessage, MapsSettings, DriverActivityLog, BotSettings, BotAdmin, SosAlert, BalanceLog, BalanceTopupRequest, GroupMessage, PanelEvent, PanelSound, SmsSettings, AiSettings, AiRewardLog, Task, ContractSettings, DriverContractSignature, FlyerVoucher, VizitkaRewardLog, LegalDocument, SecurityIncident, VoiceParticipant, VoiceSignal, SavedAddress, Employee, EmployeeTask, EmployeeShift, EmployeeAttendance
from .utils import haversine, send_telegram, dispatch_order, tg_new_order, tg_driver_registered, tg_driver_approved, tg_driver_rejected, tg_driver_blocked, tg_driver_unblocked, tg_balance_changed, tg_order_cancelled, tg_order_deleted, log_panel_event, reverse_geocode_address, sms_order_status, send_sms, generate_growth_insights, build_contract_pdf, build_flyer_pdf, generate_voucher_codes, tg_flyer_voucher_redeemed, build_balance_receipt_pdf, build_flyer_business_card_pdf, voice_prune_stale, voice_participants_list, voice_target_kwargs, voice_signal_sender_info, voice_broadcast_audio
import csv
import json

ONLINE_THRESHOLD_SECONDS = 120  # last_seen shundan yangi bo'lsa — online (yashil)
PENDING_ORDER_AGING_SECONDS = 120  # buyurtma shuncha vaqt haydovchisiz tursa — operator e'tiboriga chiqadi
TOPUP_AGING_HOURS = 3  # to'lov so'rovi shuncha soat hal qilinmasa — dashboardda ogohlantirish chiqadi

# Diqqat (xavfsizlik): oddiy login_required faqat "session autentifikatsiya
# qilinganmi" ni tekshiradi — driver/client ilovalari HAM shu bilan bir xil
# Django autentifikatsiya tizimidan (bir xil User modeli, bir xil sessiya
# cookie) foydalangani uchun, agar panel view'lari ham shunchaki login_required
# bilan cheklansa, o'z hisobiga kirgan HAR QANDAY haydovchi yoki mijoz ham
# panel URL'lariga (jumladan balans o'zgartiruvchilariga) to'g'ridan-to'g'ri
# kirib ketishi mumkin edi — aynan shu sabab bilan bir haydovchi panelga kirib,
# o'z balansini o'zgartirib olgan edi. Shuning uchun panelning BARCHA
# view'lari uchun `is_staff`ni ham tekshiruvchi shu decorator ishlatiladi.
panel_login_required = user_passes_test(
    lambda u: u.is_authenticated and u.is_staff, login_url='taxi:panel_login')

# Diqqat: "Tizim" (dasturchi/DevOps) sahifalari — backup, tizim diagnostikasi,
# tarif/bot/SMS/AI kabi sozlamalar — endi oddiy operatordan (is_staff) yuqori
# huquq (is_superuser) talab qiladi va butunlay alohida panelda (/system/,
# alohida login sahifasi bilan) joylashadi. Oddiy admin/operator hisoblari
# bu bo'limni sidebar'da UMUMAN ko'rmaydi va to'g'ridan-to'g'ri manzilga
# kirishga urinsa ham (is_superuser bo'lmagani uchun) /system/login/ ga
# qaytariladi.
system_login_required = user_passes_test(
    lambda u: u.is_authenticated and u.is_staff and u.is_superuser, login_url='system:system_login')

# ── DB backup (Tizim holati sahifasi) ───────────────────────────────────────
# Diqqat (xavfsizlik): backup fayl nomlari HAR DOIM shu qat'iy formatga mos
# kelishi shart — download/delete view'lari foydalanuvchidan kelgan `filename`
# ni to'g'ridan-to'g'ri fayl tizimi yo'liga aylantirgani uchun, agar bu
# tekshiruv bo'lmasa "../../config/settings.py" kabi yo'l bilan path traversal
# qilish mumkin bo'lardi.
import re as _re
BACKUP_FILENAME_RE = _re.compile(r'^vijdon_backup_\d{8}_\d{6}\.sql\.gz$')


def _backups_dir():
    import os
    from django.conf import settings as django_settings
    d = os.path.join(str(django_settings.BASE_DIR), 'backups')
    os.makedirs(d, exist_ok=True)
    return d


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Order ──────────────────────────────────────────────────────────────────────

@panel_login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client', 'driver', 'dispatched_to')
             .prefetch_related('rejected_by', 'dispatch_attempts__driver'),
        pk=pk
    )
    client_orders = Order.objects.filter(client=order.client).order_by('-created_at')[:10]
    return render(request, 'taxi/order_detail.html', {
        'order':         order,
        'client_orders': client_orders,
        'drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
    })


@panel_login_required
def client_detail(request, pk):
    from django.db.models import Sum, Count
    client = get_object_or_404(Client, pk=pk)
    orders = Order.objects.filter(client=client).select_related('driver').order_by('-created_at')
    stats = orders.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        total_spent=Sum('price', filter=Q(status='completed')),
    )
    return render(request, 'taxi/client_detail.html', {
        'client': client,
        'orders': orders,
        'stats':  stats,
    })


@panel_login_required
@require_POST
def order_field_transcribe(request):
    """Buyurtma oynasidagi mikrofon tugmalari (manzil/telefon/ism/izoh) —
    yozilgan ovozni (o'zbekcha) matnga o'giradi (OpenAI Whisper,
    taxi.utils.transcribe_audio_uz). mode='phone' bo'lsa, natija qo'shimcha
    ravishda telefon raqam formatiga o'giriladi (taxi.utils.parse_uz_spoken_phone)."""
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'ok': False, 'error': 'Audio topilmadi'}, status=400)
    from taxi.utils import transcribe_audio_uz, parse_uz_spoken_phone
    text, error = transcribe_audio_uz(audio.read(), filename=audio.name or 'speech.webm')
    if error:
        return JsonResponse({'ok': False, 'error': error}, status=400)
    if request.POST.get('mode') == 'phone':
        text, error = parse_uz_spoken_phone(text)
        if error:
            return JsonResponse({'ok': False, 'error': error}, status=400)
    return JsonResponse({'ok': True, 'text': text})


@panel_login_required
@require_POST
def order_notify_creating(request):
    """Yangi buyurtma oynasi ochilganda chaqiriladi — haydovchilar guruhiga
    "buyurtma yaratilmoqda" ogohlantirishini yuboradi."""
    from taxi.utils import tg_order_creating
    tg_order_creating()
    return JsonResponse({'ok': True})


@panel_login_required
def order_create(request):
    if request.method == 'POST':
        phone_number  = request.POST.get('phone_number', '').strip()
        customer_name = request.POST.get('customer_name', '').strip()
        from_address = request.POST.get('from_address', '').strip()
        to_address   = request.POST.get('to_address', '').strip()
        driver_id    = request.POST.get('driver_id') or None

        from_lat = request.POST.get('from_lat')
        from_lng = request.POST.get('from_lng')
        to_lat   = request.POST.get('to_lat')
        to_lng   = request.POST.get('to_lng')

        if phone_number and from_address:
            tariff = TariffSettings.get()
            client, _ = Client.objects.get_or_create(phone_number=phone_number)
            if client.is_blocked:
                from django.contrib import messages
                messages.error(request, f"🚫 {client.full_name or phone_number} — bloklangan mijoz! Buyurtma berish uchun avval blokdan chiqaring.")
                return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))
            if customer_name and not client.full_name:
                client.full_name = customer_name
                client.save(update_fields=['full_name'])
            driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None

            f_lat = float(from_lat) if from_lat else None
            f_lng = float(from_lng) if from_lng else None
            t_lat = float(to_lat) if to_lat else None
            t_lng = float(to_lng) if to_lng else None

            is_delivery = request.POST.get('is_delivery') == 'on'

            distance_km = None
            price = None
            if f_lat and f_lng and t_lat and t_lng:
                distance_km = haversine(f_lat, f_lng, t_lat, t_lng)
                if distance_km:
                    price = tariff.calc_price(distance_km)

            # Yetkazib berish (dastavka) — narx kamida 10 000 so'mdan boshlanadi,
            # haydovchidan olinadigan komissiya esa qat'iy 3000 so'm bo'ladi
            # (odatiy tarif komissiyasi o'rniga)
            if is_delivery:
                price = max(price or 0, 10000)
                delivery_commission = 3000

            # Avtomatik taqsimlash — FAQAT haritadan koordinata belgilangan bo'lsa
            # Manzil qo'lda yozilsa (from_lat yo'q) → umumiy tabloga tushadi, hammaga ko'rinadi
            has_coords = bool(f_lat and f_lng)

            payment_type = request.POST.get('payment_type', 'cash')
            car_type     = request.POST.get('car_type', Driver.CAR_TYPE_LIGHT)
            note         = request.POST.get('note', '').strip()

            order = Order.objects.create(
                client=client,
                from_address=from_address,
                from_lat=f_lat, from_lng=f_lng,
                to_address=to_address,
                to_lat=t_lat, to_lng=t_lng,
                distance_km=distance_km,
                price=price,
                commission=delivery_commission if is_delivery else tariff.commission,
                driver=driver,
                payment_type=payment_type,
                car_type=car_type,
                is_delivery=is_delivery,
                note=note,
                status='pending',
            )

            # Operator haydovchini qo'lda tanlagan bo'lsa (dropdown yoki xaritadan
            # belgi bosib) — buyurtma FAQAT o'sha haydovchiga ko'rinishi kerak
            # (taxi/driver_views.py'dagi pending ro'yxati `dispatched_to`ga qarab
            # filtrlaydi, `driver` maydoniga emas). Shuningdek, avtomatik
            # dispatch bilan bir xil push/Telegram bildirishnoma va
            # dispatch_timeout taymeri ham ishga tushiriladi — aks holda
            # haydovchi javob bermasa (masalan hozir band/uxlab yotgan bo'lsa),
            # buyurtma abadiy shu haydovchiga "osilib qolar", vaqt o'tib umumiy
            # ro'yxatda ko'rinsa ham hech kim qabul qila olmasdi (dispatched_to
            # hech qachon tozalanmagani uchun).
            if driver is not None:
                from django.utils import timezone
                from .utils import notify_driver_new_order, start_dispatch_timeout, _log_dispatch_attempt
                order.dispatched_to = driver
                order.dispatched_at = timezone.now()
                order.save(update_fields=['dispatched_to', 'dispatched_at'])
                manual_dist = haversine(f_lat, f_lng, driver.latitude, driver.longitude) if has_coords else None
                _log_dispatch_attempt(order, driver, manual_dist)
                notify_driver_new_order(order, driver)
                start_dispatch_timeout(order, driver, tariff.dispatch_timeout)

            # Telegram xabar
            tg_new_order(order)

            # Dispatch — faqat koordinata belgilangan VA "Avtomatik taqsimlash"
            # yoqilgan bo'lsa eng yaqin/adolatli haydovchiga yuboriladi.
            # Koordinata yo'q (qo'lda yozilgan manzil) yoki auto_dispatch
            # o'chirilgan bo'lsa → umumiy tabloda qoladi, hammaga ko'rinadi
            # (boshqa barcha dispatch chaqiruvlari — client_views.py,
            # driver_views.py, bot buyruqlari — shu bayroqni tekshiradi,
            # bu yerda ham xuddi shunday bo'lishi kerak).
            # Diqqat: SINXRON chaqiriladi (thread ichida emas) — aks holda order
            # yaratilgandan keyin dispatch_order `dispatched_to`ni belgilagunga
            # qadar bo'sh oraliqda buyurtma hammaga (umumiy tablo sifatida)
            # ko'rinib, eng yaqin bo'lmagan haydovchi ham birinchi bo'lib qabul
            # qilib olishi mumkin edi.
            if has_coords and driver is None and tariff.auto_dispatch:
                dispatch_order(order)

            from .utils import log_system_event
            log_system_event(
                'order_created',
                f"Buyurtma #{order.id} yaratildi — {from_address} → {to_address or '?'}"
                + (f" ({driver.full_name}ga tayinlandi)" if driver else ''),
                request=request,
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:panel_dashboard'))


def _refund_order_commission(order, driver, reason):
    """Buyurtma haydovchi tomonidan qabul qilingan holatda (accepted/on_way/
    arrived) bekor qilinsa yoki o'chirilsa, ilgari undan yechilgan komissiyani
    balansiga qaytaradi — haydovchi o'z aybisiz pulini yo'qotmasligi uchun."""
    from decimal import Decimal
    from .utils import send_fcm

    commission = order.commission or TariffSettings.get().commission
    driver.balance += Decimal(str(commission))
    driver.save(update_fields=['balance'])
    BalanceLog.objects.create(
        driver=driver, action=BalanceLog.ACTION_ADD, amount=commission,
        balance_after=driver.balance,
        note=f"Komissiya qaytarildi — buyurtma #{order.id} {reason}",
    )
    send_fcm(
        driver.fcm_token,
        title='Komissiya qaytarildi',
        body=f"Buyurtma #{order.id} bekor qilindi. {commission} so'm balansingizga qaytarildi.",
        data={'type': 'order_cancelled', 'order_id': str(order.id)},
    )
    return commission


@panel_login_required
def order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        old_status = order.status
        old_driver = order.driver
        new_status = request.POST.get('status')
        driver_id  = request.POST.get('driver_id') or None
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
        reassigned_driver = None
        prev_dispatched_id = order.dispatched_to_id
        if driver_id:
            order.driver = Driver.objects.filter(pk=driver_id).first()
            # Buyurtma hali "pending" bo'lib qolayotgan bo'lsa (masalan operator
            # boshqa haydovchiga qayta yo'naltirsa) — dispatched_to'ni ham shu
            # haydovchiga o'rnatamiz, aks holda taxi/driver_views.py'dagi pending
            # ro'yxati buni "umumiy tablo"ga tushgan deb hisoblab, HAMMA
            # haydovchiga ko'rsatib yuborardi (order_create'dagi bilan bir xil bug).
            if order.status == 'pending' and order.driver:
                from django.utils import timezone
                order.dispatched_to = order.driver
                order.dispatched_at = timezone.now()
                reassigned_driver = order.driver
        order.save()

        # order_create'dagi bilan bir xil: qo'lda qayta yo'naltirilgan haydovchiga
        # ham push/Telegram xabar va javob bermasa avtomatik bo'shatuvchi taymer.
        if reassigned_driver:
            from .utils import notify_driver_new_order, start_dispatch_timeout, _log_dispatch_attempt, _resolve_dispatch_attempt
            from .models import DispatchAttempt
            if prev_dispatched_id and prev_dispatched_id != reassigned_driver.id:
                _resolve_dispatch_attempt(order, prev_dispatched_id, DispatchAttempt.RESULT_CANCELLED)
            manual_dist = haversine(order.from_lat, order.from_lng, reassigned_driver.latitude, reassigned_driver.longitude) if order.from_lat and order.from_lng else None
            _log_dispatch_attempt(order, reassigned_driver, manual_dist)
            notify_driver_new_order(order, reassigned_driver)
            start_dispatch_timeout(order, reassigned_driver, TariffSettings.get().dispatch_timeout)

        # Buyurtma qabul qilingan holatda bo'lib, endi bekor qilinsa — haydovchidan
        # ilgari yechilgan komissiya balansiga qaytariladi
        refunded = False
        if new_status == 'cancelled' and old_status in Order.ACTIVE_STATUSES and old_driver:
            _refund_order_commission(order, old_driver, "operator tomonidan bekor qilindi")
            refunded = True

        if new_status in ('accepted', 'arrived', 'completed', 'cancelled'):
            sms_order_status(order, new_status)
        # Haydovchiga FCM yuborish — buyurtma bekor qilinsa yoki yakunlansa
        # (komissiya qaytarilganda alohida xabar allaqachon yuborilgan)
        if new_status in ('cancelled', 'completed') and order.driver and not refunded:
            from .utils import send_fcm
            send_fcm(
                order.driver.fcm_token,
                title='Buyurtma holati o\'zgardi',
                body=f'Buyurtma #{order.id} — {order.get_status_display()}',
                data={'type': 'order_update', 'order_id': str(order.id), 'status': new_status},
            )

        from .utils import log_system_event
        log_system_event(
            'order_status_changed',
            f"Buyurtma #{order.id}: {old_status} → {order.status}"
            + (f" (haydovchi: {order.driver.full_name})" if order.driver else ''),
            request=request,
        )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))


@panel_login_required
def order_cancel_reassign(request, pk):
    """Haydovchi operatorga qo'ng'iroq qilib buyurtmani bekor qilishni so'raganda
    ishlatiladi: haydovchidan yechilgan komissiya unga qaytariladi, buyurtma undan
    yechib olinib qayta 'kutilmoqda' holatiga o'tkaziladi — shu bilan boshqa
    haydovchilar uni qabul qilishi mumkin bo'ladi."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST' and order.driver_id and order.status in ('accepted', 'on_way', 'arrived'):
        from decimal import Decimal
        from .utils import send_fcm

        old_driver = order.driver
        commission = order.commission or TariffSettings.get().commission
        old_driver.balance += Decimal(str(commission))
        old_driver.save(update_fields=['balance'])
        BalanceLog.objects.create(
            driver=old_driver, action=BalanceLog.ACTION_ADD, amount=commission,
            balance_after=old_driver.balance,
            note=f"Komissiya qaytarildi — buyurtma #{order.id} operator tomonidan bekor qilindi",
        )

        order.rejected_by.add(old_driver)
        order.driver = None
        order.dispatched_to = None
        order.dispatched_at = None
        order.status = 'pending'
        order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'updated_at'])

        log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — {old_driver.full_name} dan bekor qilindi, qayta ochildi")
        from .utils import log_system_event
        log_system_event(
            'order_cancelled_reassigned',
            f"Buyurtma #{order.id} — {old_driver.full_name}dan bekor qilindi, qayta ochildi",
            request=request,
        )
        send_fcm(
            old_driver.fcm_token,
            title='Buyurtma bekor qilindi',
            body=f"Buyurtma #{order.id} operator tomonidan bekor qilindi. {commission} so'm balansingizga qaytarildi.",
            data={'type': 'order_cancelled', 'order_id': str(order.id)},
        )

        tariff = TariffSettings.get()
        if tariff.auto_dispatch:
            dispatch_order(order)

        messages.success(
            request,
            f"Buyurtma #{order.id} bekor qilindi — {old_driver.full_name}ga {commission} so'm qaytarildi, buyurtma qayta ochildi.",
        )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))


@panel_login_required
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        # Buyurtma hali yakunlanmagan holatda haydovchiga biriktirilgan bo'lsa
        # (komissiya balansidan allaqachon yechilgan) — o'chirishdan oldin qaytariladi
        if order.driver_id and order.status in Order.ACTIVE_STATUSES:
            _refund_order_commission(order, order.driver, "o'chirildi")
        log_panel_event('panel_order_deleted', f"Buyurtma #{order.id} — {order.from_address}")
        from .utils import log_system_event
        log_system_event('order_deleted', f"Buyurtma #{order.id} — {order.from_address} o'chirildi", level='warning', request=request)
        tg_order_deleted(order)
        order.delete()
    return redirect('taxi:order_list')


# ── Driver ─────────────────────────────────────────────────────────────────────

@panel_login_required
def driver_create(request):
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        car_model    = request.POST.get('car_model', '').strip()
        car_number   = request.POST.get('car_number', '').strip()
        car_type     = request.POST.get('car_type', Driver.CAR_TYPE_LIGHT)
        if full_name and phone_number:
            driver = Driver.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                car_model=car_model,
                car_number=car_number,
                car_type=car_type,
                approval_status=Driver.APPROVAL_APPROVED,
                is_active=True,
            )
            tg_driver_registered(driver)
            from .utils import log_system_event
            log_system_event('driver_created', f"Yangi haydovchi qo'shildi: {driver.full_name} ({driver.phone_number})", request=request)
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@panel_login_required
def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        from .utils import log_system_event
        log_system_event('driver_deleted', f"Haydovchi o'chirildi: {driver.full_name} ({driver.phone_number})", level='warning', request=request)
        if driver.user:
            driver.user.delete()
        else:
            driver.delete()
    return redirect('taxi:driver_list')


@panel_login_required
def driver_toggle_active(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.is_active = not driver.is_active
        driver.save(update_fields=['is_active'])
        action = DriverActivityLog.ACTION_UNBLOCK if driver.is_active else DriverActivityLog.ACTION_BLOCK
        detail = 'Admin tomonidan ' + ('blok ochildi' if driver.is_active else 'bloklandi')
        DriverActivityLog.objects.create(driver=driver, action=action, detail=detail,
            ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
        if driver.is_active:
            tg_driver_unblocked(driver)
        else:
            tg_driver_blocked(driver)
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@panel_login_required
def driver_toggle_frozen(request, pk):
    """Admin haydovchini qo'lda muzlatishi/muzlashni bekor qilishi mumkin —
    avtomatik muzlatish (3+ kun onlayn bo'lmagani uchun, utils.freeze_inactive_drivers)
    bilan bir xil `is_frozen` maydonidan foydalanadi, faqat jurnal yozuvida
    "Admin tomonidan" deb ko'rsatiladi."""
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.is_frozen = not driver.is_frozen
        driver.save(update_fields=['is_frozen'])
        action = DriverActivityLog.ACTION_FREEZE if driver.is_frozen else DriverActivityLog.ACTION_UNFREEZE
        detail = 'Admin tomonidan ' + ('muzlatildi' if driver.is_frozen else 'muzlash bekor qilindi')
        DriverActivityLog.objects.create(
            driver=driver, action=action, detail=detail,
            ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@panel_login_required
def driver_approve(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        from .utils import log_system_event
        if action == 'approve':
            driver.approval_status = Driver.APPROVAL_APPROVED
            driver.is_active = True
            if driver.user:
                driver.user.is_active = True
                driver.user.save(update_fields=['is_active'])
            tg_driver_approved(driver)
            log_system_event('driver_approved', f"Haydovchi tasdiqlandi: {driver.full_name} ({driver.phone_number})", request=request)
        elif action == 'reject':
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
            tg_driver_rejected(driver)
            log_system_event('driver_rejected', f"Haydovchi rad etildi: {driver.full_name} ({driver.phone_number})", level='warning', request=request)
        driver.save(update_fields=['approval_status', 'is_active'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@panel_login_required
def driver_recharge(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        action = request.POST.get('action', 'add')
        from decimal import Decimal
        try:
            amount = Decimal(amount)
            if action == 'deduct':
                driver.balance -= amount
                detail = f"-{amount} UZS (admin ayirdi)"
            else:
                driver.balance += amount
                detail = f"+{amount} UZS (admin qo'shdi)"
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=action, amount=amount,
                balance_after=driver.balance, note=request.POST.get('note', '')
            )
            DriverActivityLog.objects.create(driver=driver, action=DriverActivityLog.ACTION_BALANCE, detail=detail,
                ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            tg_balance_changed(driver, amount, action)
        except (ValueError, TypeError, Exception):
            pass
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


# ── Driver Detail ─────────────────────────────────────────────────────────────

@panel_login_required
def driver_detail(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    logs   = driver.activity_logs.all()[:100]
    orders = driver.orders.select_related('client').order_by('-created_at')[:20]
    contract = ContractSettings.get()
    contract_signature = driver.contract_signatures.filter(version=contract.version).first()
    return render(request, 'taxi/driver_detail.html', {
        'driver': driver,
        'logs':   logs,
        'orders': orders,
        'contract_signature': contract_signature,
    })


# ── Client ─────────────────────────────────────────────────────────────────────

@panel_login_required
def client_create(request):
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if phone_number:
            Client.objects.get_or_create(
                phone_number=phone_number,
                defaults={'full_name': full_name},
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:client_list'))


@panel_login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
    return redirect('taxi:client_list')


@panel_login_required
def client_block_toggle(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.is_blocked = not client.is_blocked
        client.save(update_fields=['is_blocked'])
    return redirect('taxi:client_list')


@panel_login_required
def client_send_sms(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if not text:
            messages.error(request, 'SMS matni bo\'sh bo\'lishi mumkin emas.')
        else:
            ok, message = send_sms(client.phone_number, text)
            if ok:
                messages.success(request, f"SMS {client.phone_number} raqamiga yuborildi.")
            else:
                messages.error(request, f"SMS yuborilmadi: {message}")
    return redirect(request.META.get('HTTP_REFERER', 'taxi:client_list'))


# ── Pages ──────────────────────────────────────────────────────────────────────

@panel_login_required
def panel_dashboard(request):
    from django.utils import timezone
    from django.db.models import Sum, Avg, Count
    from decimal import Decimal

    today = timezone.now().date()
    online_threshold = timezone.now() - timezone.timedelta(minutes=2)
    aging_cutoff = timezone.now() - timezone.timedelta(seconds=PENDING_ORDER_AGING_SECONDS)
    orders = Order.objects.select_related('client', 'driver').order_by('-created_at')[:10]
    aging_orders = Order.objects.select_related('client').filter(
        status='pending', created_at__lte=aging_cutoff
    ).order_by('created_at')
    pending_drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).order_by('-registered_at')
    on_duty_drivers = Driver.objects.filter(
        is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED
    ).count()
    online_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED,
        last_seen__gte=online_threshold
    ).count()

    completed_qs = Order.objects.filter(status='completed')
    today_qs     = Order.objects.filter(created_at__date=today)

    total_revenue   = completed_qs.aggregate(s=Sum('price'))['s'] or Decimal('0')
    today_revenue   = today_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or Decimal('0')
    today_orders    = today_qs.count()
    avg_price       = completed_qs.aggregate(a=Avg('price'))['a'] or Decimal('0')
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    all_orders_count = Order.objects.count()
    cancellation_rate = round(cancelled_orders / all_orders_count * 100, 1) if all_orders_count else 0

    # So'nggi 7 kunlik statistika (grafik uchun)
    from datetime import timedelta
    weekly_labels, weekly_revenue, weekly_counts = [], [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        weekly_labels.append(day.strftime('%d/%m'))
        weekly_revenue.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        weekly_counts.append(day_qs.count())

    # Shu hafta vs o'tgan hafta o'sish foizi (daromad va buyurtmalar soni)
    this_week_start = today - timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end    = this_week_start - timedelta(days=1)
    this_week_qs = Order.objects.filter(created_at__date__gte=this_week_start, created_at__date__lte=today)
    last_week_qs = Order.objects.filter(created_at__date__gte=last_week_start, created_at__date__lte=last_week_end)
    this_week_revenue = float(this_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    last_week_revenue = float(last_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    this_week_orders  = this_week_qs.count()
    last_week_orders  = last_week_qs.count()
    revenue_growth_pct = round((this_week_revenue - last_week_revenue) / last_week_revenue * 100, 1) if last_week_revenue else None
    orders_growth_pct  = round((this_week_orders - last_week_orders) / last_week_orders * 100, 1) if last_week_orders else None

    # Ogohlantirishlar: balansi kam va uzoq faol bo'lmagan haydovchilar
    tariff_for_alerts = TariffSettings.get()
    low_balance_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, balance__lt=tariff_for_alerts.commission
    ).order_by('balance')
    inactive_cutoff = timezone.now() - timedelta(days=3)
    inactive_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, is_on_duty=False
    ).filter(Q(last_seen__lt=inactive_cutoff) | Q(last_seen__isnull=True))

    topup_aging_cutoff = timezone.now() - timedelta(hours=TOPUP_AGING_HOURS)
    aging_topups = BalanceTopupRequest.objects.select_related('driver').filter(
        status=BalanceTopupRequest.STATUS_PENDING, created_at__lte=topup_aging_cutoff
    ).order_by('created_at')

    expiring_documents = LegalDocument.objects.filter(
        expires_at__isnull=False, expires_at__lte=today + timedelta(days=DOCUMENT_EXPIRY_WARNING_DAYS)
    ).order_by('expires_at')
    open_security_incidents = SecurityIncident.objects.exclude(status=SecurityIncident.STATUS_RESOLVED)

    # Hozir yo'lda (taksometr yurgan) buyurtmalar — dashboarddagi "Yo'lda
    # haydovchilar" bloki uchun. Faqat on_way/arrived holatida, chunki
    # tmx_dist_km faqat shu holatlarda jonli yangilanadi (driver_meter_update).
    orders_on_route = Order.objects.select_related('driver', 'client').filter(
        status__in=('on_way', 'arrived')
    ).order_by('-tmx_start_time')

    context = {
        'orders':               orders,
        'total_orders':         Order.objects.count(),
        'total_drivers':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'on_duty_drivers':      on_duty_drivers,
        'online_drivers':       online_drivers,
        'total_clients':        Client.objects.count(),
        'pending_orders':       Order.objects.filter(status='pending').count(),
        'completed_orders':     completed_qs.count(),
        'cancelled_orders':     cancelled_orders,
        'active_drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'pending_drivers':      pending_drivers,
        'pending_driver_count': pending_drivers.count(),
        'aging_orders':         aging_orders,
        'aging_order_count':    aging_orders.count(),
        'aging_threshold_minutes': PENDING_ORDER_AGING_SECONDS // 60,
        'tariff':               TariffSettings.get(),
        'total_revenue':        total_revenue,
        'today_revenue':        today_revenue,
        'today_orders':         today_orders,
        'avg_price':            avg_price,
        'weekly_labels':        weekly_labels,
        'weekly_revenue':       weekly_revenue,
        'weekly_counts':        weekly_counts,
        'cancellation_rate':    cancellation_rate,
        'revenue_growth_pct':   revenue_growth_pct,
        'orders_growth_pct':    orders_growth_pct,
        'low_balance_drivers':  low_balance_drivers,
        'low_balance_driver_count': low_balance_drivers.count(),
        'inactive_drivers':     inactive_drivers,
        'inactive_driver_count': inactive_drivers.count(),
        'aging_topups':      aging_topups,
        'aging_topup_count': aging_topups.count(),
        'topup_aging_hours': TOPUP_AGING_HOURS,
        'expiring_documents':      expiring_documents,
        'expiring_document_count': expiring_documents.count(),
        'open_security_incident_count': open_security_incidents.count(),
        'orders_on_route':      orders_on_route,
        'orders_on_route_count': orders_on_route.count(),
    }
    return render(request, 'taxi/panel.html', context)


@panel_login_required
def aging_orders_count(request):
    from django.utils import timezone
    cutoff = timezone.now() - timezone.timedelta(seconds=PENDING_ORDER_AGING_SECONDS)
    count = Order.objects.filter(status='pending', created_at__lte=cutoff).count()
    return JsonResponse({'count': count})


@panel_login_required
def orders_on_route_poll(request):
    """Dashboarddagi "Yo'lda haydovchilar" blokini jonli yangilash uchun."""
    from django.utils import timezone
    orders = Order.objects.select_related('driver', 'client').filter(status__in=('on_way', 'arrived'))
    data = []
    for o in orders:
        started = o.tmx_start_time or o.created_at
        data.append({
            'id':           o.id,
            'status':       o.status,
            'driver_id':    o.driver_id,
            'driver_name':  o.driver.full_name if o.driver else '',
            'photo_url':    o.driver.photo.url if o.driver and o.driver.photo else '',
            'car_model':    o.driver.car_model if o.driver else '',
            'car_number':   o.driver.car_number if o.driver else '',
            'client_name':  o.client.full_name if o.client else '',
            'from_address': o.from_address,
            'to_address':   o.to_address,
            'dist_km':      float(o.tmx_dist_km or 0),
            'price':        float(o.price or 0),
            'started_at':   started.isoformat(),
        })
    data.sort(key=lambda x: x['started_at'], reverse=True)
    return JsonResponse({'orders': data})


@panel_login_required
def order_list(request):
    from django.core.paginator import Paginator
    from django.template.loader import render_to_string

    qs = Order.objects.select_related('client', 'driver')
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    sort   = request.GET.get('sort', '').strip()
    if q:
        qs = qs.filter(
            Q(client__full_name__icontains=q) |
            Q(client__phone_number__icontains=q) |
            Q(from_address__icontains=q) |
            Q(to_address__icontains=q) |
            Q(driver__full_name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    if sort == 'top_price':
        qs = qs.order_by('-price', '-created_at')
    else:
        qs = qs.order_by('-created_at')

    drivers = Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED)
    page_obj = Paginator(qs, 40).get_page(request.GET.get('page'))

    # Pastga tushirilganda keyingi sahifa shu yerdan AJAX orqali yuklanadi
    # (base.html'dagi initInfiniteScroll) — faqat qo'shimcha qatorlar
    # HTML'i qaytariladi, butun sahifa emas.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('taxi/_order_rows.html', {'orders': page_obj, 'drivers': drivers}, request=request)
        return JsonResponse({'html': html, 'has_next': page_obj.has_next()})

    context = {
        'orders':      page_obj,
        'total_count': page_obj.paginator.count,
        'drivers':     drivers,
        'q':           q,
        'status':      status,
        'sort':        sort,
        'statuses':    Order.STATUS_CHOICES,
    }
    return render(request, 'taxi/order_list.html', context)


@panel_login_required
def driver_list(request):
    from django.db.models import Case, When, Value, IntegerField
    from django.utils import timezone
    from django.core.paginator import Paginator
    from django.template.loader import render_to_string

    q    = request.GET.get('q', '').strip()
    tab  = request.GET.get('tab', 'approved')
    sort = request.GET.get('sort', '').strip()
    online_cutoff = timezone.now() - timezone.timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    qs  = Driver.objects.annotate(
        completed_count=Count('orders', filter=Q(orders__status='completed')),
        cancelled_count=Count('orders', filter=Q(orders__status='cancelled')),
        is_online=Case(
            When(last_seen__gte=online_cutoff, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(phone_number__icontains=q) |
            Q(car_model__icontains=q) |
            Q(car_number__icontains=q)
        )
    if tab == 'pending':
        qs = qs.filter(approval_status=Driver.APPROVAL_PENDING)
    elif tab == 'rejected':
        qs = qs.filter(approval_status=Driver.APPROVAL_REJECTED)
    else:
        qs = qs.filter(approval_status=Driver.APPROVAL_APPROVED)

    if sort == 'top_completed':
        qs = qs.order_by('-is_online', '-completed_count', '-id')
    elif sort == 'top_cancelled':
        qs = qs.order_by('-is_online', '-cancelled_count', '-id')
    elif sort == 'top_rating':
        qs = qs.order_by('-is_online', '-rating', '-id')
    elif sort == 'top_balance':
        qs = qs.order_by('-is_online', '-balance', '-id')
    elif sort == 'newest':
        qs = qs.order_by('-is_online', '-registered_at', '-id')
    else:
        qs = qs.order_by('-is_online', '-last_seen', '-id')

    # Kutilmoqda (pending) yorliq katta kartochkalarda ko'rsatiladi va odatda
    # kam sonli bo'ladi — faqat tasdiqlangan/rad etilgan jadval ro'yxati
    # sahifalanadi (pastga tushirilganda AJAX orqali qolgani yuklanadi).
    if tab != 'pending':
        page_obj = Paginator(qs, 40).get_page(request.GET.get('page'))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('taxi/_driver_rows.html', {'drivers': page_obj, 'tab': tab}, request=request)
            return JsonResponse({'html': html, 'has_next': page_obj.has_next()})
        qs = page_obj

    return render(request, 'taxi/driver_list.html', {
        'drivers':        qs,
        'q':              q,
        'tab':            tab,
        'sort':           sort,
        'pending_count':  Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count(),
        'approved_count': Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count(),
        'rejected_count': Driver.objects.filter(approval_status=Driver.APPROVAL_REJECTED).count(),
    })


PING_STALE_MINUTES = 5   # shundan eski o'lchov — "noma'lum" deb hisoblanadi
PING_WARN_MS = 250        # shundan yuqori — o'rtacha (sariq)
PING_BAD_MS  = 700        # shundan yuqori — sekin (qizil)


@panel_login_required
def ping_dashboard(request):
    """Hozir navbatda turgan haydovchilarning internet ulanish sifati
    (ping) ro'yxati — aloqasi yomon/noma'lum haydovchilar yuqorida
    chiqadi, shu orqali operator ularga qo'ng'iroq qilib yordam bera
    oladi (masalan simkarta/tarmoq bo'yicha maslahat)."""
    from django.utils import timezone
    import datetime

    stale_cutoff = timezone.now() - datetime.timedelta(minutes=PING_STALE_MINUTES)

    rows = []
    for d in Driver.objects.filter(is_active=True, is_on_duty=True):
        fresh = bool(d.last_ping_at and d.last_ping_at >= stale_cutoff)
        if not fresh:
            status, sort_key = 'unknown', 1
        elif d.last_ping_ms < PING_WARN_MS:
            status, sort_key = 'good', 0
        elif d.last_ping_ms < PING_BAD_MS:
            status, sort_key = 'warn', 2
        else:
            status, sort_key = 'bad', 3
        rows.append({
            'driver': d,
            'ping_ms': d.last_ping_ms if fresh else None,
            'last_ping_at': d.last_ping_at,
            'status': status,
            'sort_key': sort_key,
        })
    # Yordam kerak bo'lganlar (bad/warn/unknown) tepada, yaxshi aloqalilar pastda
    rows.sort(key=lambda r: (-r['sort_key'], -(r['ping_ms'] or 0)))

    return render(request, 'taxi/ping_dashboard.html', {
        'rows': rows,
        'bad_count': sum(1 for r in rows if r['status'] == 'bad'),
    })


@panel_login_required
def client_list(request):
    from django.core.paginator import Paginator
    from django.template.loader import render_to_string

    q      = request.GET.get('q', '').strip()
    filter_ = request.GET.get('filter', '').strip()
    sort    = request.GET.get('sort', '').strip()
    qs = Client.objects.annotate(orders_count=Count('orders'))
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone_number__icontains=q))
    if filter_ == 'blocked':
        qs = qs.filter(is_blocked=True)
    elif filter_ == 'active':
        qs = qs.filter(is_blocked=False)
    if sort == 'top_orders':
        qs = qs.order_by('-orders_count')
    else:
        qs = qs.order_by('-id')

    page_obj = Paginator(qs, 40).get_page(request.GET.get('page'))

    # Ro'yxatni pastga tushirganda keyingi sahifa shu yerdan AJAX orqali
    # yuklanadi (base.html'dagi initInfiniteScroll) — butun sahifa emas,
    # faqat qatorlar HTML'i qaytariladi.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('taxi/_client_rows.html', {'clients': page_obj}, request=request)
        return JsonResponse({'html': html, 'has_next': page_obj.has_next()})

    return render(request, 'taxi/client_list.html', {
        'clients': page_obj,
        'total_count': page_obj.paginator.count,
        'q': q, 'filter': filter_, 'sort': sort,
    })


# ── Tariff Settings ────────────────────────────────────────────────────────────

@system_login_required
def bot_settings(request):
    from django.conf import settings as django_settings
    bot = BotSettings.get()
    if request.method == 'POST':
        bot.bot_token = request.POST.get('bot_token', '').strip()
        bot.group_id  = request.POST.get('group_id', '').strip()
        bot.extra_group_ids = request.POST.get('extra_group_ids', '').strip()
        bot.client_bot_token = request.POST.get('client_bot_token', '').strip()
        bot.driver_group_id = request.POST.get('driver_group_id', '').strip()
        bot.driver_extra_group_ids = request.POST.get('driver_extra_group_ids', '').strip()
        bot.notify_driver_group    = 'notify_driver_group'    in request.POST
        bot.notify_new_order       = 'notify_new_order'       in request.POST
        bot.notify_dispatched      = 'notify_dispatched'      in request.POST
        bot.notify_accepted        = 'notify_accepted'        in request.POST
        bot.notify_on_way          = 'notify_on_way'          in request.POST
        bot.notify_arrived         = 'notify_arrived'         in request.POST
        bot.notify_completed       = 'notify_completed'       in request.POST
        bot.notify_cancelled       = 'notify_cancelled'       in request.POST
        bot.notify_rejected        = 'notify_rejected'        in request.POST
        bot.notify_deleted         = 'notify_deleted'         in request.POST
        bot.notify_driver_register = 'notify_driver_register' in request.POST
        bot.notify_driver_approved = 'notify_driver_approved' in request.POST
        bot.notify_driver_rejected = 'notify_driver_rejected' in request.POST
        bot.notify_driver_blocked  = 'notify_driver_blocked'  in request.POST
        bot.notify_driver_login    = 'notify_driver_login'    in request.POST
        bot.notify_duty_changed    = 'notify_duty_changed'    in request.POST
        bot.notify_balance_changed = 'notify_balance_changed' in request.POST
        bot.notify_low_balance     = 'notify_low_balance'     in request.POST
        bot.notify_balance_changed_to_driver_group = 'notify_balance_changed_to_driver_group' in request.POST
        bot.notify_low_balance_to_driver_group     = 'notify_low_balance_to_driver_group'     in request.POST
        bot.notify_freeze_warning  = 'notify_freeze_warning'  in request.POST
        bot.notify_morning_greeting    = 'notify_morning_greeting'    in request.POST
        bot.notify_evening_top_drivers = 'notify_evening_top_drivers' in request.POST
        bot.notify_night_greeting      = 'notify_night_greeting'      in request.POST
        bot.notify_weekly_top_drivers  = 'notify_weekly_top_drivers'  in request.POST
        bot.notify_monthly_top_drivers = 'notify_monthly_top_drivers' in request.POST
        bot.notify_inactive_drivers    = 'notify_inactive_drivers'    in request.POST
        bot.notify_low_rating          = 'notify_low_rating'          in request.POST
        bot.notify_surge_alert         = 'notify_surge_alert'         in request.POST
        bot.notify_driver_milestone    = 'notify_driver_milestone'    in request.POST
        bot.notify_sos_to_driver_group = 'notify_sos_to_driver_group' in request.POST
        bot.notify_top_hours_drivers   = 'notify_top_hours_drivers'   in request.POST
        bot.notify_high_rejection      = 'notify_high_rejection'      in request.POST
        bot.notify_daily_summary       = 'notify_daily_summary'       in request.POST
        bot.notify_weekly_summary      = 'notify_weekly_summary'      in request.POST
        bot.notify_daily_highlight     = 'notify_daily_highlight'     in request.POST
        bot.notify_flyer_redeemed      = 'notify_flyer_redeemed'      in request.POST
        bot.notify_monthly_financial_report = 'notify_monthly_financial_report' in request.POST
        bot.notify_driver_engagement   = 'notify_driver_engagement'   in request.POST
        bot.notify_driver_fun_stats    = 'notify_driver_fun_stats'    in request.POST
        bot.save()
        from .utils import log_system_event
        log_system_event('settings_changed', 'Bot sozlamalari o\'zgartirildi', request=request)
        # SITE_URL ni settings ga yozish
        site_url = request.POST.get('site_url', '').strip()
        if site_url:
            django_settings.SITE_URL = site_url
        # Test xabar yuborish
        if 'test' in request.POST and bot.bot_token and bot.group_id:
            from .utils import send_telegram
            send_telegram('✅ <b>VijdonTaxi bot ulanishi muvaffaqiyatli!</b>\nBu test xabari.')
        # Haydovchilar guruhiga erkin matnli e'lon yuborish
        announce_text = request.POST.get('announce_text', '').strip()
        if 'announce' in request.POST and announce_text and bot.bot_token:
            from .utils import tg_group_announcement
            tg_group_announcement(announce_text)
        return redirect('system:bot_settings')
    site_url = getattr(django_settings, 'SITE_URL', '')
    order_notifs = [
        ('notify_new_order',  'Yangi buyurtma',          '🚨', bot.notify_new_order),
        ('notify_dispatched', 'Buyurtma yuborildi',       '📡', bot.notify_dispatched),
        ('notify_accepted',   'Buyurtma qabul qilindi',   '✅', bot.notify_accepted),
        ('notify_on_way',     "Haydovchi yo'lda",         '🚗', bot.notify_on_way),
        ('notify_arrived',    'Haydovchi yetib keldi',    '📍', bot.notify_arrived),
        ('notify_completed',  'Buyurtma yakunlandi',      '🏁', bot.notify_completed),
        ('notify_cancelled',  'Buyurtma bekor qilindi',   '❌', bot.notify_cancelled),
        ('notify_rejected',   'Buyurtma rad etildi',      '🔄', bot.notify_rejected),
        ('notify_deleted',    "Buyurtma o'chirildi",      '🗑️', bot.notify_deleted),
    ]
    driver_notifs = [
        ('notify_driver_register', "Yangi haydovchi ro'yxatdan o'tdi", '🆕', bot.notify_driver_register),
        ('notify_driver_approved', 'Haydovchi tasdiqlandi',             '✅', bot.notify_driver_approved),
        ('notify_driver_rejected', 'Haydovchi rad etildi',              '🚫', bot.notify_driver_rejected),
        ('notify_driver_blocked',  'Haydovchi bloklandi/ochildi',       '🔒', bot.notify_driver_blocked),
        ('notify_driver_login',    'Haydovchi kirdi (login)',           '🔑', bot.notify_driver_login),
        ('notify_duty_changed',    "Navbat holati o'zgardi",            '🟢', bot.notify_duty_changed),
        ('notify_balance_changed', "Balans o'zgardi",                   '💰', bot.notify_balance_changed),
        ('notify_low_balance',     'Balans kam ogohlantirish',          '⚠️', bot.notify_low_balance),
        ('notify_balance_changed_to_driver_group', "Balans to'ldirilganda haydovchilar guruhiga ham yuborish", '💚', bot.notify_balance_changed_to_driver_group),
        ('notify_low_balance_to_driver_group',     'Balans kam qolganda haydovchilar guruhiga ham yuborish',   '⚠️', bot.notify_low_balance_to_driver_group),
        ('notify_freeze_warning',      "Muzlashga 1 kun qolganda ogohlantirish (03:00)", '⏰', bot.notify_freeze_warning),
        ('notify_morning_greeting',    'Ertalabki salomlashuv (07:00)',        '🌅', bot.notify_morning_greeting),
        ('notify_evening_top_drivers', 'Kechqurungi TOP-10 (20:00)',           '🏆', bot.notify_evening_top_drivers),
        ('notify_night_greeting',      'Tungi navbatchilarga salom (23:00)',   '🌙', bot.notify_night_greeting),
        ('notify_weekly_top_drivers',  'Haftalik TOP-10 (yakshanba 21:00)',    '📅', bot.notify_weekly_top_drivers),
        ('notify_monthly_top_drivers', 'Oylik TOP-10 (oy oxiri 21:00)',        '🗓️', bot.notify_monthly_top_drivers),
        ('notify_inactive_drivers',    "Faol bo'lmagan haydovchilar (10:00)",  '😴', bot.notify_inactive_drivers),
        ('notify_low_rating',          'Reyting pasayganda ogohlantirish',     '⭐', bot.notify_low_rating),
        ('notify_surge_alert',         'Talab yuqori bo\'lganda ogohlantirish','📈', bot.notify_surge_alert),
        ('notify_driver_milestone',    'Haydovchi yubileyi (safarlar soni)',   '🎉', bot.notify_driver_milestone),
        ('notify_sos_to_driver_group', 'SOS ni haydovchilar guruhiga ham yuborish', '🆘', bot.notify_sos_to_driver_group),
        ('notify_top_hours_drivers',   "Eng ko'p soat ishlagan (21:00)",       '⏱️', bot.notify_top_hours_drivers),
        ('notify_high_rejection',      "Ko'p rad etish haqida ogohlantirish (19:00)", '🚫', bot.notify_high_rejection),
        ('notify_daily_summary',       'Kunlik umumiy hisobot (22:00)',        '📊', bot.notify_daily_summary),
        ('notify_weekly_summary',      'Haftalik umumiy hisobot (yakshanba 22:00)', '📈', bot.notify_weekly_summary),
        ('notify_daily_highlight',     "Kunning yorqin lahzalari (20:00)",     '🌟', bot.notify_daily_highlight),
        ('notify_flyer_redeemed',      'Flayer kuponi ishlatilganda xabar',    '🎁', bot.notify_flyer_redeemed),
        ('notify_monthly_financial_report', "Oylik moliyaviy hisobot (har oy 1-kuni 09:00)", '🗓️', bot.notify_monthly_financial_report),
        ('notify_driver_engagement', "Motivatsion/maslahat/hazil xabarlar (12:00, 18:00)", '💡', bot.notify_driver_engagement),
        ('notify_driver_fun_stats',  "Kunlik qiziqarli statistika (16:00)",                 '📊', bot.notify_driver_fun_stats),
    ]
    return render(request, 'taxi/bot_settings.html', {
        'bot': bot,
        'site_url': site_url,
        'order_notifs': order_notifs,
        'driver_notifs': driver_notifs,
        'admins': BotAdmin.objects.all(),
    })


@system_login_required
def sms_settings(request):
    sms = SmsSettings.get()
    saved = False
    test_result = None
    if request.method == 'POST':
        if 'test' in request.POST:
            test_phone = request.POST.get('test_phone', '').strip()
            ok, message = send_sms(test_phone, 'Vijdon Taxi: bu test SMS xabari.')
            test_result = {'ok': ok, 'message': message}
        else:
            new_email    = request.POST.get('email', '').strip()
            new_password = request.POST.get('password', '').strip()
            if new_email != sms.email or new_password != sms.password:
                # Kirish ma'lumotlari o'zgardi — eski token endi yaroqsiz
                sms.token = ''
                sms.token_updated_at = None
            sms.email    = new_email
            sms.password = new_password
            sms.nickname = request.POST.get('nickname', '').strip() or '4546'
            sms.sms_accepted  = 'sms_accepted'  in request.POST
            sms.sms_arrived   = 'sms_arrived'   in request.POST
            sms.sms_completed = 'sms_completed' in request.POST
            sms.sms_cancelled = 'sms_cancelled' in request.POST
            sms.save()
            saved = True
            from .utils import log_system_event
            log_system_event('settings_changed', 'SMS sozlamalari o\'zgartirildi', request=request)
    sms_notifs = [
        ('sms_accepted',  'Buyurtma qabul qilindi',  '✅', sms.sms_accepted),
        ('sms_arrived',   'Haydovchi yetib keldi',   '📍', sms.sms_arrived),
        ('sms_completed', 'Buyurtma yakunlandi',     '🏁', sms.sms_completed),
        ('sms_cancelled', 'Buyurtma bekor qilindi',  '❌', sms.sms_cancelled),
    ]
    return render(request, 'taxi/sms_settings.html', {
        'sms': sms,
        'saved': saved,
        'test_result': test_result,
        'sms_notifs': sms_notifs,
    })


# ── AI o'sish tavsiyalari ─────────────────────────────────────────────────────

@system_login_required
def ai_settings(request):
    cfg = AiSettings.get()
    saved = False
    if request.method == 'POST':
        cfg.api_key = request.POST.get('api_key', '').strip()
        cfg.model   = request.POST.get('model', cfg.model)
        cfg.save()
        saved = True
        from .utils import log_system_event
        log_system_event('settings_changed', 'AI sozlamalari o\'zgartirildi', request=request)
    return render(request, 'taxi/ai_settings.html', {
        'cfg': cfg,
        'saved': saved,
        'model_choices': AiSettings.MODEL_CHOICES,
    })


@system_login_required
def system_status(request):
    """Dasturchi/operator uchun tizim diagnostikasi: xotira, disk, protsessor
    yuklamasi, DB ulanishi va scheduler threadining "tirikligi" — ilova
    qotib qolgan/muammoli bo'lsa shu yerdan tezda bilib olish uchun."""
    import os
    import sys
    import time
    import shutil
    import platform
    import django
    from django.conf import settings as django_settings
    from django.db import connection
    from . import scheduler
    from .apps import TaxiConfig, PROCESS_STARTED_AT

    now = time.time()

    # ── Ilova jarayoni (worker) ──────────────────────────────────────────────
    uptime_sec = now - PROCESS_STARTED_AT
    _days, _rem = divmod(int(uptime_sec), 86400)
    _hours, _rem = divmod(_rem, 3600)
    _minutes, _ = divmod(_rem, 60)
    if _days:
        uptime_human = f"{_days} kun {_hours} soat"
    elif _hours:
        uptime_human = f"{_hours} soat {_minutes} daqiqa"
    else:
        uptime_human = f"{_minutes} daqiqa"

    # ── Xotira (faqat Linux'da /proc/meminfo mavjud — shared hosting shunday) ──
    memory = None
    try:
        meminfo = {}
        with open('/proc/meminfo') as f:
            for line in f:
                key, _, rest = line.partition(':')
                meminfo[key] = int(rest.strip().split()[0])  # KB
        total_kb     = meminfo.get('MemTotal', 0)
        available_kb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
        used_kb      = total_kb - available_kb
        memory = {
            'total_mb':     round(total_kb / 1024, 1),
            'available_mb': round(available_kb / 1024, 1),
            'used_mb':      round(used_kb / 1024, 1),
            'used_pct':     round(used_kb / total_kb * 100, 1) if total_kb else None,
        }
    except Exception:
        pass

    # ── Shu Python jarayonining o'zi ishlatayotgan xotira (RSS) ─────────────
    process_memory_mb = None
    try:
        import resource
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        process_memory_mb = round(rss_kb / 1024, 1)  # Linux'da ru_maxrss KB da
    except Exception:
        pass

    # ── Disk (dastur joylashgan diskda) ──────────────────────────────────────
    disk = None
    try:
        total, used, free = shutil.disk_usage(django_settings.BASE_DIR)
        disk = {
            'total_gb': round(total / 1024**3, 1),
            'used_gb':  round(used / 1024**3, 1),
            'free_gb':  round(free / 1024**3, 1),
            'used_pct': round(used / total * 100, 1),
        }
    except Exception:
        pass

    # ── Protsessor yuklamasi (faqat POSIX) ───────────────────────────────────
    load_avg = None
    try:
        load_avg = os.getloadavg()  # (1min, 5min, 15min)
    except (AttributeError, OSError):
        pass
    cpu_count = os.cpu_count()

    # ── Ma'lumotlar bazasi ulanishi va javob tezligi ─────────────────────────
    db = {'ok': False, 'latency_ms': None, 'size_mb': None, 'error': None}
    try:
        t0 = time.time()
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        db['latency_ms'] = round((time.time() - t0) * 1000, 1)
        db['ok'] = True
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT pg_database_size(current_database())')
                db['size_mb'] = round(cur.fetchone()[0] / 1024**2, 1)
        except Exception:
            pass
    except Exception as e:
        db['error'] = str(e)

    # ── Kesh (cache) ──────────────────────────────────────────────────────────
    # Diqqat: loyihada Redis/Memcached ULANMAGAN — CACHES sozlanmagani uchun
    # Django standart bo'yicha LocMemCache (jarayon xotirasida, workerlar
    # o'rtasida ULASHILMAYDI) ishlatadi. Shu yerda qaysi backend ishlayotgani
    # va u haqiqatan yozish/o'qishga qodirligi tekshiriladi.
    from django.core.cache import cache as _cache
    cache_info = {'ok': False, 'backend': _cache.__class__.__name__, 'latency_ms': None, 'error': None}
    try:
        t0 = time.time()
        _cache_key = '_system_status_check'
        _cache.set(_cache_key, 'ok', 10)
        cache_info['ok'] = _cache.get(_cache_key) == 'ok'
        cache_info['latency_ms'] = round((time.time() - t0) * 1000, 1)
        if not cache_info['ok']:
            cache_info['error'] = "Yozilgan qiymat qayta o'qib bo'lmadi"
    except Exception as e:
        cache_info['error'] = str(e)

    # ── Fon rejalashtiruvchi (Telegram kunlik/haftalik xabarlar) ─────────────
    sched = {'enabled': TaxiConfig._should_start_scheduler(), 'last_tick_ago_sec': None, 'healthy': None}
    if scheduler.last_tick_at:
        sched['last_tick_ago_sec'] = round(now - scheduler.last_tick_at, 1)
        # Har 30s da bir tick bo'lishi kerak — 3 barobaridan ko'p kechiksa
        # (~90s), thread qotib qolgan/o'lgan bo'lishi mumkin.
        sched['healthy'] = sched['last_tick_ago_sec'] < 90

    counts = {
        'orders':  Order.objects.count(),
        'active_orders': Order.objects.filter(status__in=Order.ACTIVE_STATUSES).count(),
        'drivers': Driver.objects.count(),
        'clients': Client.objects.count(),
    }

    # ── Deploy holati: joriy git commit, branch, saqlanmagan o'zgarishlar ───
    # Serverda `git pull` haqiqatan ham ishlaganini/qaysi versiya joriy
    # ishlab turganini bilish uchun — kod deploy qilingandan keyin ham eski
    # worker jarayoni ishlab turishi mumkin (shuning uchun "Ishlab turgan
    # vaqt" bilan solishtirib ko'ring: agar u bu commit sanasidan OLDIN
    # boshlangan bo'lsa, worker hali qayta ishga tushirilmagan).
    git_info = None
    try:
        import subprocess
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=str(django_settings.BASE_DIR), capture_output=True, text=True, timeout=5)
        if commit.returncode == 0:
            branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=str(django_settings.BASE_DIR), capture_output=True, text=True, timeout=5)
            log = subprocess.run(['git', 'log', '-1', '--format=%s|%ci'], cwd=str(django_settings.BASE_DIR), capture_output=True, text=True, timeout=5)
            status_out = subprocess.run(['git', 'status', '--porcelain'], cwd=str(django_settings.BASE_DIR), capture_output=True, text=True, timeout=5)
            msg, _, date = log.stdout.strip().partition('|')
            git_info = {
                'commit': commit.stdout.strip(),
                'branch': branch.stdout.strip() if branch.returncode == 0 else None,
                'message': msg,
                'date': date,
                'dirty': bool(status_out.stdout.strip()) if status_out.returncode == 0 else None,
            }
    except Exception:
        pass

    # ── Qo'llanilmagan migratsiyalar ─────────────────────────────────────────
    migrations_pending = None
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        migrations_pending = [f'{m.app_label}.{m.name}' for m, backwards in plan if not backwards]
    except Exception:
        migrations_pending = None

    # ── Django'ning o'zining deploy xavfsizlik tekshiruvi (manage.py check
    # --deploy bilan bir xil) — HTTPS/cookie/SECRET_KEY kabi sozlamalar
    # haqida.
    django_checks = []
    try:
        from django.core.checks import run_checks, WARNING
        for issue in run_checks(include_deployment_checks=True):
            if issue.level >= WARNING:
                django_checks.append({'id': issue.id, 'msg': issue.msg, 'is_error': issue.level >= 40})
    except Exception:
        pass

    # ── Muhit (environment) ──────────────────────────────────────────────────
    env_info = {
        'debug': django_settings.DEBUG,
        'allowed_hosts': django_settings.ALLOWED_HOSTS,
        'secret_key_default': django_settings.SECRET_KEY.startswith('django-insecure-'),
    }

    # ── Static fayllar manifesti ─────────────────────────────────────────────
    # Diqqat: aynan shu tekshiruv yo'qligi sabab bir marta butun sayt 500 berib
    # qolgan edi (`collectstatic` ishga tushirilmagani uchun manifest'da
    # yozuv yo'q edi) — endi buni oldindan shu yerda ko'rish mumkin.
    static_info = {'ok': False, 'error': None}
    try:
        from django.templatetags.static import static as _static_url
        _static_url('taxi/img/logo.png')
        static_info['ok'] = True
    except Exception as e:
        static_info['error'] = str(e)

    # ── Integratsiyalar holati ────────────────────────────────────────────────
    # Diqqat: hech qanday tokenning o'zi ko'rsatilmaydi — faqat "bormi/yo'qmi"
    # (masalan bir joyni ekranga proyeksiya qilinsa ham, maxfiy kalitlar
    # sizib chiqmasin). "Nega bot/SMS/AI ishlamayapti" degan savolga tezkor
    # javob berish uchun.
    bot_cfg = BotSettings.get()
    sms_cfg = SmsSettings.get()
    ai_cfg  = AiSettings.get()
    maps_cfg = MapsSettings.get()
    integrations = [
        {'name': 'Telegram Bot', 'icon': 'fab fa-telegram', 'ok': bool(bot_cfg.bot_token and bot_cfg.group_id)},
        {'name': 'SMS (Eskiz.uz)', 'icon': 'fas fa-comment-sms', 'ok': bool(sms_cfg.email and sms_cfg.password)},
        {'name': 'AI (o\'sish tavsiyalari)', 'icon': 'fas fa-robot', 'ok': bool(ai_cfg.api_key)},
        {'name': 'Maps / Geocoding', 'icon': 'fas fa-map-marked-alt', 'ok': bool(maps_cfg.is_active and (maps_cfg.api_key or maps_cfg.provider == MapsSettings.PROVIDER_NOMINATIM))},
    ]

    # ── Mavjud DB backuplar ───────────────────────────────────────────────────
    backups = []
    try:
        from datetime import datetime
        d = _backups_dir()
        for fn in sorted(os.listdir(d), reverse=True):
            if BACKUP_FILENAME_RE.match(fn):
                fp = os.path.join(d, fn)
                backups.append({
                    'name': fn,
                    'size_mb': round(os.path.getsize(fp) / 1024**2, 2),
                    'created_at': datetime.fromtimestamp(os.path.getmtime(fp)),
                })
    except Exception:
        pass

    # ── Umumiy holat (yuqoridagi banner uchun) ───────────────────────────────
    problems = []
    if not db['ok']:
        problems.append("Ma'lumotlar bazasiga ulanib bo'lmayapti")
    if sched['healthy'] is False:
        problems.append("Fon rejalashtiruvchi qotib qolgan bo'lishi mumkin")
    if memory and memory['used_pct'] is not None and memory['used_pct'] >= 90:
        problems.append("Xotira deyarli tugagan")
    if disk and disk['used_pct'] >= 90:
        problems.append("Diskda joy deyarli qolmagan")
    if env_info['debug']:
        problems.append("DEBUG=True — production muhitida bu XAVFLI (xatolarda to'liq kod/sozlamalar ko'rinadi)")
    if migrations_pending:
        problems.append(f"{len(migrations_pending)} ta migratsiya qo'llanilmagan — `python manage.py migrate` ishga tushiring")
    for c in django_checks:
        if c['is_error']:
            problems.append(f"Django: {c['msg']}")
    if not static_info['ok']:
        problems.append("Static fayllar manifesti buzilgan — `python manage.py collectstatic` ishga tushiring (aks holda sayt 500 beradi!)")
    if not cache_info['ok']:
        problems.append("Kesh (cache) ishlamayapti — sozlamalarni tekshiring")

    return render(request, 'taxi/system_status.html', {
        'problems': problems,
        'python_version': sys.version.split()[0],
        'django_version':  django.get_version(),
        'os_platform':     platform.platform(),
        'uptime_human':     uptime_human,
        'memory':           memory,
        'process_memory_mb': process_memory_mb,
        'disk':             disk,
        'load_avg':         load_avg,
        'cpu_count':        cpu_count,
        'db':               db,
        'sched':            sched,
        'counts':           counts,
        'backups':          backups,
        'git_info':         git_info,
        'migrations_pending': migrations_pending,
        'django_checks':    django_checks,
        'env_info':          env_info,
        'static_info':       static_info,
        'integrations':      integrations,
        'cache_info':        cache_info,
    })


@system_login_required
def system_audit_log(request):
    """Kim tizimga kirdi/kira olmadi, sozlamalarni kim o'zgartirdi, server
    xatolari (500'lar, to'liq traceback bilan) — hammasi shu yerda. Bundan
    tashqari "kimda qanday huquq bor" (is_staff/is_superuser) ro'yxati ham
    shu sahifada — xavfsizlik nuqtai nazaridan bittada ko'rinib turishi
    uchun."""
    from taxi.models import SystemAuditLog
    from django.core.paginator import Paginator
    from django.contrib.auth.models import User

    level = request.GET.get('level', '').strip()
    qs = SystemAuditLog.objects.select_related('user').all()
    if level in ('info', 'warning', 'error'):
        qs = qs.filter(level=level)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    staff_users = User.objects.filter(is_staff=True).order_by('-is_superuser', 'username')

    counts = {
        'error':   SystemAuditLog.objects.filter(level='error').count(),
        'warning': SystemAuditLog.objects.filter(level='warning').count(),
        'info':    SystemAuditLog.objects.filter(level='info').count(),
    }

    return render(request, 'taxi/system_audit_log.html', {
        'page_obj': page_obj,
        'level': level,
        'staff_users': staff_users,
        'counts': counts,
    })


# Diqqat (xavfsizlik): faqat shu ro'yxatdagi buyruqlar ishga tushirilishi
# mumkin — foydalanuvchidan erkin buyruq nomi HECH QACHON qabul qilinmaydi
# (aks holda `manage.py shell`/boshqa xavfli buyruqlarni ham chaqirish
# imkoni ochilib qolardi).
SYSTEM_ALLOWED_COMMANDS = [
    'send_morning_greeting',
    'send_night_greeting',
    'send_daily_summary',
    'send_daily_highlight',
    'send_evening_top_drivers',
    'send_weekly_summary',
    'send_weekly_top_drivers',
    'send_monthly_top_drivers',
    'send_monthly_financial_report',
    'send_inactive_drivers_report',
    'send_top_hours_drivers',
    'send_high_rejection_report',
]


@system_login_required
def system_commands(request):
    """Kunlik/haftalik/oylik Telegram hisobot buyruqlarini SSH'siz, qo'lda
    (masalan sozlama to'g'ri ishlayaptimi tekshirish uchun) ishga tushirish."""
    from django.core.management import load_command_class
    commands = []
    for name in SYSTEM_ALLOWED_COMMANDS:
        try:
            help_text = load_command_class('taxi', name).help
        except Exception:
            help_text = ''
        commands.append({'name': name, 'help': help_text})
    return render(request, 'taxi/system_commands.html', {'commands': commands})


@system_login_required
def system_run_command(request, name):
    if request.method != 'POST' or name not in SYSTEM_ALLOWED_COMMANDS:
        return redirect('system:system_commands')
    import io
    from django.core.management import call_command
    from .utils import log_system_event
    out = io.StringIO()
    try:
        call_command(name, stdout=out, stderr=out)
        log_system_event('command_run', f"'{name}' qo'lda ishga tushirildi", request=request, detail=out.getvalue())
        messages.success(request, f"'{name}' bajarildi: {out.getvalue().strip() or 'OK'}")
    except Exception as e:
        log_system_event('command_run', f"'{name}' xato berdi: {e}", level='error', request=request, detail=out.getvalue())
        messages.error(request, f"'{name}' xatosi: {e}")
    return redirect('system:system_commands')


# ── Xodimlar boshqaruvi (faqat /system/ panelidan, is_superuser talab qiladi) ──
@system_login_required
def system_staff_list(request):
    """Barcha foydalanuvchilarni (is_staff bo'lsin yoki yo'q) ko'rish va
    huquqlarini (staff/superuser/faol) shu yerdan, Django admin'siz
    boshqarish uchun."""
    from django.contrib.auth.models import User
    users = User.objects.all().order_by('-is_superuser', '-is_staff', 'username')
    return render(request, 'taxi/system_staff.html', {'staff_users': users})


@system_login_required
def system_staff_create(request):
    from django.contrib.auth.models import User
    from .utils import log_system_event
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        make_superuser = 'is_superuser' in request.POST
        if not username or not password:
            messages.error(request, "Login va parol kiritilishi shart.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"'{username}' logini band.")
        elif len(password) < 8:
            messages.error(request, "Parol kamida 8 belgidan iborat bo'lishi kerak.")
        else:
            user = User.objects.create_user(username=username, password=password, is_staff=True, is_superuser=make_superuser)
            log_system_event('staff_created', f"Yangi xodim yaratildi: '{username}'" + (" (superuser)" if make_superuser else ""), level='warning', request=request)
            messages.success(request, f"'{username}' yaratildi.")
    return redirect('system:system_staff_list')


@system_login_required
def system_staff_toggle_staff(request, pk):
    from django.contrib.auth.models import User
    from .utils import log_system_event
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target == request.user:
            messages.error(request, "O'zingizning staff huquqingizni shu yerdan olib tashlay olmaysiz.")
        else:
            target.is_staff = not target.is_staff
            target.save(update_fields=['is_staff'])
            log_system_event('staff_toggled', f"'{target.username}' uchun staff huquqi: {'yoqildi' if target.is_staff else 'o‘chirildi'}", level='warning', request=request)
            messages.success(request, f"'{target.username}' yangilandi.")
    return redirect('system:system_staff_list')


@system_login_required
def system_staff_toggle_superuser(request, pk):
    from django.contrib.auth.models import User
    from .utils import log_system_event
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target == request.user:
            messages.error(request, "O'zingizning superuser huquqingizni shu yerdan olib tashlay olmaysiz.")
        else:
            target.is_superuser = not target.is_superuser
            target.save(update_fields=['is_superuser'])
            log_system_event('staff_toggled', f"'{target.username}' uchun superuser huquqi: {'yoqildi' if target.is_superuser else 'o‘chirildi'}", level='warning', request=request)
            messages.success(request, f"'{target.username}' yangilandi.")
    return redirect('system:system_staff_list')


@system_login_required
def system_staff_toggle_active(request, pk):
    from django.contrib.auth.models import User
    from .utils import log_system_event
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target == request.user:
            messages.error(request, "O'zingizni shu yerdan bloklay olmaysiz.")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            log_system_event('staff_toggled', f"'{target.username}' hisobi: {'faollashtirildi' if target.is_active else 'bloklandi'}", level='warning', request=request)
            messages.success(request, f"'{target.username}' yangilandi.")
    return redirect('system:system_staff_list')


@system_login_required
def system_staff_reset_password(request, pk):
    from django.contrib.auth.models import User
    from .utils import log_system_event
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if len(password) < 8:
            messages.error(request, "Parol kamida 8 belgidan iborat bo'lishi kerak.")
        else:
            target.set_password(password)
            target.save(update_fields=['password'])
            log_system_event('staff_password_reset', f"'{target.username}' uchun parol qayta o'rnatildi", level='warning', request=request)
            messages.success(request, f"'{target.username}' uchun parol yangilandi.")
    return redirect('system:system_staff_list')


@system_login_required
def run_collectstatic(request):
    """`git pull`dan keyin `collectstatic` unutilib qolsa, static fayllar
    manifesti eskirib, butun sayt 500 bera boshlaydi (buni bir marta boshdan
    kechirdik) — shuning uchun SSH'siz, shu tugma orqali ham ishga tushirish
    mumkin bo'lsin."""
    if request.method != 'POST':
        return redirect('system:system_status')
    import io
    from django.core.management import call_command
    from .utils import log_system_event
    out = io.StringIO()
    try:
        call_command('collectstatic', interactive=False, verbosity=1, stdout=out, stderr=out)
        log_system_event('collectstatic_run', 'collectstatic ishga tushirildi', request=request)
        messages.success(request, "collectstatic muvaffaqiyatli bajarildi.")
    except Exception as e:
        log_system_event('collectstatic_run', f'collectstatic xato berdi: {e}', level='error', request=request, detail=out.getvalue())
        messages.error(request, f"collectstatic xatosi: {e}")
    return redirect('system:system_status')


@system_login_required
def run_migrate(request):
    if request.method != 'POST':
        return redirect('system:system_status')
    import io
    from django.core.management import call_command
    from .utils import log_system_event
    out = io.StringIO()
    try:
        call_command('migrate', interactive=False, verbosity=1, stdout=out, stderr=out)
        log_system_event('migrate_run', 'migrate ishga tushirildi', request=request, detail=out.getvalue())
        messages.success(request, "Migratsiyalar bajarildi.")
    except Exception as e:
        log_system_event('migrate_run', f'migrate xato berdi: {e}', level='error', request=request, detail=out.getvalue())
        messages.error(request, f"Migratsiya xatosi: {e}")
    return redirect('system:system_status')


@system_login_required
def backup_create(request):
    """`pg_dump` orqali joriy PostgreSQL bazasining to'liq nusxasini oladi va
    gzip qilib backups/ papkasiga saqlaydi. Kichik/o'rta hajmdagi baza uchun
    (bu loyiha kabi kichik-o'lchamli, bitta joyga o'rnatilgan tizim) so'rov
    davomida sinxron bajarish yetarli — juda katta bazalarda bu alohida
    fon vazifasiga (masalan cron) ko'chirilishi kerak bo'lardi."""
    if request.method != 'POST':
        return redirect('system:system_status')

    import os
    import gzip
    import shutil
    import subprocess
    from django.conf import settings as django_settings
    from django.utils import timezone

    db = django_settings.DATABASES['default']
    ts = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    backups_dir = _backups_dir()
    sql_path = os.path.join(backups_dir, f'vijdon_backup_{ts}.sql')
    gz_path = sql_path + '.gz'

    env = os.environ.copy()
    if db.get('PASSWORD'):
        env['PGPASSWORD'] = db['PASSWORD']

    try:
        with open(sql_path, 'wb') as f:
            result = subprocess.run(
                [
                    'pg_dump',
                    '-h', db.get('HOST') or 'localhost',
                    '-p', str(db.get('PORT') or '5432'),
                    '-U', db['USER'],
                    '--no-owner', '--no-privileges',
                    db['NAME'],
                ],
                env=env, stdout=f, stderr=subprocess.PIPE, timeout=300,
            )
        if result.returncode != 0:
            os.remove(sql_path)
            messages.error(request, f"Backup xatosi: {result.stderr.decode(errors='ignore')[:400]}")
        else:
            with open(sql_path, 'rb') as fin, gzip.open(gz_path, 'wb') as fout:
                shutil.copyfileobj(fin, fout)
            os.remove(sql_path)
            from .utils import log_system_event
            log_system_event('backup_created', f'vijdon_backup_{ts}.sql.gz', request=request)
            messages.success(request, f"Backup yaratildi: vijdon_backup_{ts}.sql.gz")
    except FileNotFoundError:
        messages.error(request, "pg_dump topilmadi — serverda PostgreSQL klient dasturlari o'rnatilmagan bo'lishi mumkin.")
        if os.path.exists(sql_path):
            os.remove(sql_path)
    except subprocess.TimeoutExpired:
        messages.error(request, "Backup yaratish vaqti tugadi (5 daqiqadan oshdi) — baza juda katta bo'lishi mumkin.")
        if os.path.exists(sql_path):
            os.remove(sql_path)
    except Exception as e:
        messages.error(request, f"Backup xatosi: {e}")
        if os.path.exists(sql_path):
            os.remove(sql_path)
    return redirect('system:system_status')


@system_login_required
def backup_download(request, filename):
    import os
    from django.http import FileResponse, Http404
    if not BACKUP_FILENAME_RE.match(filename):
        raise Http404
    path = os.path.join(_backups_dir(), filename)
    if not os.path.isfile(path):
        raise Http404
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=filename)


@system_login_required
def backup_delete(request, filename):
    import os
    if request.method == 'POST' and BACKUP_FILENAME_RE.match(filename):
        path = os.path.join(_backups_dir(), filename)
        if os.path.isfile(path):
            os.remove(path)
            from .utils import log_system_event
            log_system_event('backup_deleted', filename, level='warning', request=request)
            messages.success(request, f"{filename} o'chirildi.")
    return redirect('system:system_status')


@panel_login_required
def panel_ai_insights(request):
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta

    now   = timezone.now()
    today = now.date()
    completed_qs = Order.objects.filter(status='completed')
    total_orders = Order.objects.count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    cancel_rate = round(cancelled_orders / total_orders * 100, 1) if total_orders else 0

    weekly_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_counts.append(Order.objects.filter(created_at__date=day).count())

    # ── Shu hafta / o'tgan hafta taqqoslash — orqaga ketishni aniqlash uchun ──
    this_week_start = today - timedelta(days=6)
    prev_week_start  = today - timedelta(days=13)
    prev_week_end    = today - timedelta(days=7)
    this_week_qs = Order.objects.filter(created_at__date__gte=this_week_start, created_at__date__lte=today)
    prev_week_qs = Order.objects.filter(created_at__date__gte=prev_week_start, created_at__date__lte=prev_week_end)
    this_week_orders  = this_week_qs.count()
    prev_week_orders  = prev_week_qs.count()
    this_week_revenue = float(this_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    prev_week_revenue = float(prev_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    orders_change_pct  = round((this_week_orders - prev_week_orders) / prev_week_orders * 100, 1) if prev_week_orders else None
    revenue_change_pct = round((this_week_revenue - prev_week_revenue) / prev_week_revenue * 100, 1) if prev_week_revenue else None

    online_threshold = timezone.now() - timezone.timedelta(minutes=2)
    top_drivers = list(Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed'))
    ).filter(completed__gt=0).order_by('-completed')[:5])
    bottom_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED
    ).annotate(
        completed=Count('orders', filter=Q(orders__status='completed'))
    ).order_by('completed')[:5]

    total_clients = Client.objects.count()
    repeat_clients = Client.objects.annotate(total=Count('orders')).filter(total__gt=1).count()
    repeat_rate = round(repeat_clients / total_clients * 100, 1) if total_clients else 0

    # ── Eng ko'p ishlagan haydovchi va eng faol mijoz (shu oy, bo'lmasa umumiy) ──
    # Bu oy allaqachon "berdim" deb belgilangan haydovchi/mijoz qayta taklif qilinmaydi —
    # operator ularga sovg'a berganini tasdiqlagach, navbat keyingisiga o'tadi.
    month_start = today.replace(day=1)
    period = today.strftime('%Y-%m')
    rewarded_driver_ids = set(AiRewardLog.objects.filter(
        reward_type=AiRewardLog.TYPE_DRIVER, period=period
    ).values_list('driver_id', flat=True))
    rewarded_client_ids = set(AiRewardLog.objects.filter(
        reward_type=AiRewardLog.TYPE_CLIENT, period=period
    ).values_list('client_id', flat=True))

    top_driver_month = Driver.objects.exclude(id__in=rewarded_driver_ids).annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
    ).filter(completed__gt=0).order_by('-completed').first()
    top_driver_fallback = next((d for d in top_drivers if d.id not in rewarded_driver_ids), None)
    top_driver = top_driver_month or top_driver_fallback

    top_client_month = Client.objects.exclude(id__in=rewarded_client_ids).annotate(
        total=Count('orders', filter=Q(orders__created_at__date__gte=month_start)),
        spent=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
    ).filter(total__gt=0).order_by('-total').first()
    top_client_fallback = Client.objects.exclude(id__in=rewarded_client_ids).annotate(
        total=Count('orders'), spent=Sum('orders__price', filter=Q(orders__status='completed'))
    ).filter(total__gt=0).order_by('-total').first()
    top_client = top_client_month or top_client_fallback

    top_driver_data = None
    if top_driver:
        top_driver_data = {
            'id': top_driver.id,
            'ism': top_driver.full_name,
            'yakunlangan_safar': getattr(top_driver, 'completed', None),
            'daromad_keltirdi_som': float(getattr(top_driver, 'earned', None) or 0),
        }
    top_client_data = None
    if top_client:
        top_client_data = {
            'id': top_client.id,
            'ism': top_client.full_name or top_client.phone_number,
            'buyurtmalar_soni': getattr(top_client, 'total', None),
            'sarflagan_pul_som': float(getattr(top_client, 'spent', None) or 0),
        }

    stats = {
        'jami_buyurtmalar':              total_orders,
        'yakunlangan_buyurtmalar':       completed_qs.count(),
        'bekor_qilingan_buyurtmalar':    cancelled_orders,
        'bekor_qilish_foizi':            cancel_rate,
        'jami_daromad_som':              float(completed_qs.aggregate(s=Sum('price'))['s'] or 0),
        'ortacha_narx_som':              float(completed_qs.aggregate(a=Avg('price'))['a'] or 0),
        'songgi_7_kun_buyurtmalar_soni': weekly_counts,
        'shu_hafta_buyurtmalar':         this_week_orders,
        'otgan_hafta_buyurtmalar':       prev_week_orders,
        'buyurtmalar_ozgarish_foizi':    orders_change_pct,
        'shu_hafta_daromad_som':         this_week_revenue,
        'otgan_hafta_daromad_som':       prev_week_revenue,
        'daromad_ozgarish_foizi':        revenue_change_pct,
        'faol_haydovchilar_soni':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'online_haydovchilar_soni':      Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED, last_seen__gte=online_threshold).count(),
        'eng_faol_haydovchilar':         [{'ism': d.full_name, 'yakunlangan_safar': d.completed} for d in top_drivers],
        'kam_faol_haydovchilar':         [{'ism': d.full_name, 'yakunlangan_safar': d.completed} for d in bottom_drivers],
        'oyning_eng_faol_haydovchisi':   top_driver_data,
        'oyning_eng_faol_mijozi':        top_client_data,
        'jami_mijozlar':                 total_clients,
        'qaytib_kelgan_mijozlar_foizi':  repeat_rate,
        'bloklangan_mijozlar':           Client.objects.filter(is_blocked=True).count(),
    }

    ok, result = generate_growth_insights(stats)
    if ok:
        return JsonResponse({
            'ok': True,
            'items': result['tavsiyalar'],
            'warning': result.get('ogohlantirish') or '',
            'period': period,
            'top_driver': top_driver_data,
            'top_driver_reward': result.get('top_haydovchi_sovrini') or '',
            'top_client': top_client_data,
            'top_client_reward': result.get('top_mijoz_sovrini') or '',
        })
    return JsonResponse({'ok': False, 'error': result}, status=400)


@panel_login_required
@require_POST
def panel_ai_reward_given(request):
    """Operator AI tavsiya qilgan sovg'ani haydovchi/mijozga qo'lda berganini
    tasdiqlaydi. AI hech qachon sovg'ani o'zi avtomatik bermaydi — bu yerda faqat
    inson tasdiqlagan holat qayd etiladi, shundan keyin shu davrda ular AI
    tavsiyasida qayta taklif qilinmaydi."""
    reward_type = request.POST.get('type', '').strip()
    target_id   = request.POST.get('id', '').strip()
    period      = request.POST.get('period', '').strip()
    reward_text = request.POST.get('reward_text', '').strip()

    if reward_type not in (AiRewardLog.TYPE_DRIVER, AiRewardLog.TYPE_CLIENT) or not target_id or not period:
        return JsonResponse({'ok': False, 'error': "Noto'g'ri so'rov"}, status=400)

    kwargs = {'reward_type': reward_type, 'period': period}
    if reward_type == AiRewardLog.TYPE_DRIVER:
        driver = get_object_or_404(Driver, pk=target_id)
        kwargs['driver'] = driver
    else:
        client = get_object_or_404(Client, pk=target_id)
        kwargs['client'] = client

    obj, created = AiRewardLog.objects.get_or_create(
        **kwargs,
        defaults={'reward_text': reward_text, 'given_by': request.user},
    )
    if not created:
        return JsonResponse({'ok': False, 'error': 'Bu shaxsga shu oy uchun allaqachon belgilangan'}, status=400)
    return JsonResponse({'ok': True})


@system_login_required
def bot_admin_add(request):
    if request.method == 'POST':
        chat_id   = request.POST.get('chat_id', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        if chat_id.isdigit():
            BotAdmin.objects.get_or_create(chat_id=chat_id, defaults={'full_name': full_name})
    return redirect('system:bot_settings')


@system_login_required
def bot_admin_delete(request, pk):
    admin = get_object_or_404(BotAdmin, pk=pk)
    if request.method == 'POST':
        admin.delete()
    return redirect('system:bot_settings')


@system_login_required
def bot_admin_toggle(request, pk):
    admin = get_object_or_404(BotAdmin, pk=pk)
    if request.method == 'POST':
        admin.is_active = not admin.is_active
        admin.save(update_fields=['is_active'])
    return redirect('system:bot_settings')


@system_login_required
def sound_settings(request):
    from .constants import PANEL_SOUND_EVENTS, DRIVER_SOUND_EVENTS
    all_keys = [k for k, _ in PANEL_SOUND_EVENTS + DRIVER_SOUND_EVENTS]
    sounds = PanelSound.get_map()
    for key in all_keys:
        if key not in sounds:
            sounds[key] = PanelSound.objects.create(event_key=key)

    if request.method == 'POST':
        for key in all_keys:
            snd = sounds[key]
            if request.POST.get(f'reset_{key}'):
                if snd.file:
                    snd.file.delete(save=False)
                snd.file = None
            elif request.FILES.get(f'file_{key}'):
                snd.file = request.FILES[f'file_{key}']
            snd.enabled = f'enabled_{key}' in request.POST
            snd.save()
        messages.success(request, "Ovoz sozlamalari saqlandi.")
        return redirect('system:sound_settings')

    return render(request, 'taxi/sound_settings.html', {
        'panel_sounds':  [(key, label, sounds[key]) for key, label in PANEL_SOUND_EVENTS],
        'driver_sounds': [(key, label, sounds[key]) for key, label in DRIVER_SOUND_EVENTS],
    })


# ── Telegram Client Bot Webhook ───────────────────────────────────────────────

# Har bir mijoz sessiyasi: {chat_id: {'step': 'phone'|'from'|'to', 'phone': ..., 'from_address': ...}}
_client_sessions = {}


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def client_bot_webhook(request):
    """Mijoz Telegram boti webhook — buyurtma qabul qiladi."""
    import json as _json
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('ok')

    try:
        data = _json.loads(request.body)
    except Exception:
        from django.http import HttpResponse
        return HttpResponse('ok')

    msg = data.get('message') or data.get('edited_message')
    if not msg:
        from django.http import HttpResponse
        return HttpResponse('ok')

    chat_id = str(msg['chat']['id'])
    text    = (msg.get('text') or '').strip()
    loc     = msg.get('location')
    contact = msg.get('contact')

    bot = BotSettings.get()
    token = bot.client_bot_token.strip()
    if not token:
        from django.http import HttpResponse
        return HttpResponse('ok')

    def _send(chat, txt, keyboard=None):
        import urllib.request, urllib.parse
        payload = {'chat_id': chat, 'text': txt, 'parse_mode': 'HTML'}
        if keyboard:
            import json as j
            payload['reply_markup'] = j.dumps(keyboard)
        data = urllib.parse.urlencode(payload).encode()
        try:
            urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/sendMessage',
                data=data, timeout=5
            )
        except Exception:
            pass

    session = _client_sessions.get(chat_id, {})
    step    = session.get('step', 'start')

    if text in ('/start', 'Yangi buyurtma 🚖'):
        _client_sessions[chat_id] = {'step': 'phone'}
        _send(chat_id,
            '📞 <b>Telefon raqamingizni yuboring</b>\n'
            'Pastdagi tugmani bosing yoki qo\'lda yozing, masalan: <code>+998901234567</code>',
            {'keyboard': [
                [{'text': '📞 Raqamni yuborish', 'request_contact': True}],
                [{'text': 'Yangi buyurtma 🚖'}],
            ], 'resize_keyboard': True}
        )

    elif step == 'phone':
        phone = (contact.get('phone_number', '') if contact else text).replace(' ', '')
        if len(phone) < 9:
            _send(chat_id, '❌ Telefon raqam noto\'g\'ri. Qayta kiriting yoki tugmani bosing:')
        else:
            _client_sessions[chat_id] = {'step': 'from', 'phone': phone}
            _send(chat_id,
                '📍 <b>Qayerdan yo\'lga chiqasiz?</b>\nManzilni yozing yoki pastdagi tugma orqali joylashuvingizni yuboring:',
                {'keyboard': [[{'text': '📍 Joylashuvni yuborish', 'request_location': True}]], 'resize_keyboard': True}
            )

    elif step == 'from':
        if loc:
            lat, lng = loc.get('latitude'), loc.get('longitude')
            address  = reverse_geocode_address(lat, lng) or f'{lat:.5f}, {lng:.5f}'
            _client_sessions[chat_id] = dict(session, step='to', from_address=address, from_lat=lat, from_lng=lng)
        elif text:
            _client_sessions[chat_id] = dict(session, step='to', from_address=text)
        else:
            _send(chat_id, '📍 Manzilni yozing yoki joylashuvingizni yuboring:')
            from django.http import HttpResponse
            return HttpResponse('ok')
        _send(chat_id,
            '🏁 <b>Qayerga borasiz?</b>\nManzilni yozing, joylashuv yuboring yoki o\'tkazib yuboring:',
            {'keyboard': [
                [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
                [{'text': "O'tkazib yuborish ➡️"}],
            ], 'resize_keyboard': True}
        )

    elif step == 'to':
        if loc:
            to_lat, to_lng = loc.get('latitude'), loc.get('longitude')
            to_address = reverse_geocode_address(to_lat, to_lng) or f'{to_lat:.5f}, {to_lng:.5f}'
        elif text == "O'tkazib yuborish ➡️":
            to_address, to_lat, to_lng = '', None, None
        else:
            to_address, to_lat, to_lng = text, None, None

        phone        = session.get('phone', '')
        from_address = session.get('from_address', '')
        from_lat     = session.get('from_lat')
        from_lng     = session.get('from_lng')

        client, _ = Client.objects.get_or_create(phone_number=phone)
        if client.telegram_chat_id != chat_id:
            client.telegram_chat_id = chat_id
            client.save(update_fields=['telegram_chat_id'])
        tariff    = TariffSettings.get()
        order = Order.objects.create(
            client=client,
            from_address=from_address,
            from_lat=from_lat,
            from_lng=from_lng,
            to_address=to_address,
            to_lat=to_lat,
            to_lng=to_lng,
            commission=tariff.commission,
            status='pending',
        )
        tg_new_order(order)
        if tariff.auto_dispatch:
            dispatch_order(order)

        _client_sessions.pop(chat_id, None)
        _send(chat_id,
            f'✅ <b>Buyurtma #{order.id} qabul qilindi!</b>\n'
            f'📍 Qayerdan: {from_address}\n'
            + (f'🏁 Qayerga: {to_address}\n' if to_address else '') +
            '⏳ Haydovchi tez orada topiladi.',
            {'keyboard': [[{'text': 'Yangi buyurtma 🚖'}]], 'resize_keyboard': True}
        )
    else:
        _send(chat_id, 'Boshlash uchun /start yuboring.',
            {'keyboard': [[{'text': 'Yangi buyurtma 🚖'}]], 'resize_keyboard': True}
        )

    from django.http import HttpResponse
    return HttpResponse('ok')


@system_login_required
def maps_settings(request):
    maps = MapsSettings.get()
    if request.method == 'POST':
        maps.provider          = request.POST.get('provider', maps.provider)
        maps.api_key           = request.POST.get('api_key', '').strip()
        maps.yandex_mapkit_key = request.POST.get('yandex_mapkit_key', '').strip()
        maps.is_active         = request.POST.get('is_active') == 'on'
        maps.save()
        from .utils import log_system_event
        log_system_event('settings_changed', 'Maps sozlamalari o\'zgartirildi', request=request)
        return redirect('system:maps_settings')
    return render(request, 'taxi/maps_settings.html', {'maps': maps})


@system_login_required
def tariff_settings(request):
    tariff = TariffSettings.get()
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        try:
            tariff.base_price   = Decimal(request.POST.get('base_price', tariff.base_price))
            tariff.price_per_km = Decimal(request.POST.get('price_per_km', tariff.price_per_km))
            tariff.waiting_price_per_minute = Decimal(request.POST.get('waiting_price_per_minute', tariff.waiting_price_per_minute))
            tariff.commission   = Decimal(request.POST.get('commission', tariff.commission))
            tariff.auto_dispatch = request.POST.get('auto_dispatch') == 'on'
            tariff.max_dispatch_attempts = int(request.POST.get('max_dispatch_attempts', tariff.max_dispatch_attempts))
            tariff.fairness_weight_km    = float(request.POST.get('fairness_weight_km', tariff.fairness_weight_km))
            tariff.fairness_max_radius_km = float(request.POST.get('fairness_max_radius_km', tariff.fairness_max_radius_km))
            tariff.dispatch_timeout      = int(request.POST.get('dispatch_timeout', tariff.dispatch_timeout))
            tariff.operator_phone        = request.POST.get('operator_phone', tariff.operator_phone).strip() or tariff.operator_phone
            tariff.office_name = request.POST.get('office_name', tariff.office_name).strip() or tariff.office_name
            office_lat = request.POST.get('office_lat', '').strip()
            office_lng = request.POST.get('office_lng', '').strip()
            tariff.office_lat = float(office_lat) if office_lat else None
            tariff.office_lng = float(office_lng) if office_lng else None
            tariff.save()
            from .utils import log_system_event
            log_system_event('settings_changed', 'Tariff sozlamalari o\'zgartirildi', request=request)
        except (InvalidOperation, ValueError):
            pass
        return redirect('system:tariff_settings')
    return render(request, 'taxi/tariff_settings.html', {'tariff': tariff})


# ── SOS ──────────────────────────────────────────────────────────────────────────────

@panel_login_required
def sos_list(request):
    qs = SosAlert.objects.select_related('driver').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'taxi/sos_list.html', {
        'alerts':        qs,
        'status_filter': status_filter,
        'new_count':     SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count(),
    })


@panel_login_required
def sos_resolve(request, pk):
    alert = get_object_or_404(SosAlert, pk=pk)
    if request.method == 'POST':
        from django.utils import timezone
        alert.status      = request.POST.get('status', SosAlert.STATUS_RESOLVED)
        alert.resolved_by = request.POST.get('resolved_by', '').strip()
        if alert.status == SosAlert.STATUS_RESOLVED:
            alert.resolved_at = timezone.now()
        alert.save(update_fields=['status', 'resolved_by', 'resolved_at'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:sos_list'))


def sos_count(request):
    count = SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count()
    return JsonResponse({'count': count})


# ── Balans to'ldirish so'rovlari (admin panel) ──────────────────────────────

@panel_login_required
def topup_list(request):
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta

    tab = request.GET.get('tab', 'requests')
    status_filter = request.GET.get('status', BalanceTopupRequest.STATUS_PENDING)
    qs = BalanceTopupRequest.objects.select_related('driver').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)
    total_topped_up = BalanceLog.objects.filter(action=BalanceLog.ACTION_ADD).aggregate(s=Sum('amount'))['s'] or 0
    total_deducted  = BalanceLog.objects.filter(action=BalanceLog.ACTION_DEDUCT).aggregate(s=Sum('amount'))['s'] or 0
    month_topped_up = BalanceLog.objects.filter(action=BalanceLog.ACTION_ADD, created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'] or 0
    month_deducted  = BalanceLog.objects.filter(action=BalanceLog.ACTION_DEDUCT, created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'] or 0

    # Diqqat: "haqiqiy kirim" — komissiya qaytarilishi (refund) hisobga
    # kirmaydi, chunki u yangi pul emas, avval yechilgan komissiyaning
    # o'ziga qaytishi. Haydovchilarga qancha YANGI pul (to'lov cheki,
    # admin qo'shgan, bonus va h.k.) kirganini bilish uchun shu yozuvlar
    # chetlab o'tiladi.
    real_income_qs = BalanceLog.objects.filter(action=BalanceLog.ACTION_ADD).exclude(note__startswith='Komissiya qaytarildi')
    today_income     = real_income_qs.filter(created_at__date=today).aggregate(s=Sum('amount'))['s'] or 0
    today_income_count     = real_income_qs.filter(created_at__date=today).values('driver_id').distinct().count()
    yesterday_income = real_income_qs.filter(created_at__date=yesterday).aggregate(s=Sum('amount'))['s'] or 0
    yesterday_income_count = real_income_qs.filter(created_at__date=yesterday).values('driver_id').distinct().count()

    history_qs = BalanceLog.objects.select_related('driver').order_by('-created_at')
    history_action = request.GET.get('haction', '')
    history_q       = request.GET.get('q', '').strip()
    history_start   = request.GET.get('hstart', '')
    history_end     = request.GET.get('hend', '')
    if history_action in (BalanceLog.ACTION_ADD, BalanceLog.ACTION_DEDUCT):
        history_qs = history_qs.filter(action=history_action)
    if history_q:
        history_qs = history_qs.filter(Q(driver__full_name__icontains=history_q) | Q(driver__phone_number__icontains=history_q))
    if history_start:
        history_qs = history_qs.filter(created_at__date__gte=history_start)
    if history_end:
        history_qs = history_qs.filter(created_at__date__lte=history_end)

    from django.core.paginator import Paginator
    history_page = Paginator(history_qs, 30).get_page(request.GET.get('hpage'))

    # So'nggi 30 kunlik pul harakati (qo'shilgan/yechilgan), grafik uchun
    flow_labels, flow_added, flow_deducted = [], [], []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_logs = BalanceLog.objects.filter(created_at__date=day)
        flow_labels.append(day.strftime('%d/%m'))
        flow_added.append(float(day_logs.filter(action=BalanceLog.ACTION_ADD).aggregate(s=Sum('amount'))['s'] or 0))
        flow_deducted.append(float(day_logs.filter(action=BalanceLog.ACTION_DEDUCT).aggregate(s=Sum('amount'))['s'] or 0))

    return render(request, 'taxi/topup_list.html', {
        'tab':           tab,
        'requests':      qs,
        'status_filter': status_filter,
        'pending_count': BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count(),
        'drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).order_by('full_name'),
        'total_topped_up': total_topped_up,
        'total_deducted':  total_deducted,
        'month_topped_up': month_topped_up,
        'month_deducted':  month_deducted,
        'today_income':            today_income,
        'today_income_count':      today_income_count,
        'yesterday_income':        yesterday_income,
        'yesterday_income_count':  yesterday_income_count,
        'history':        history_page,
        'history_action': history_action,
        'history_q':      history_q,
        'history_start':  history_start,
        'history_end':    history_end,
        'flow_labels':   flow_labels,
        'flow_added':    flow_added,
        'flow_deducted': flow_deducted,
    })


@panel_login_required
def balance_log_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="balans_tarixi.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['#', 'Haydovchi', 'Telefon', 'Amal', 'Summa', "Balans (keyin)", 'Izoh', 'Vaqt'])

    qs = BalanceLog.objects.select_related('driver').order_by('-created_at')
    action = request.GET.get('haction', '')
    q       = request.GET.get('q', '').strip()
    start   = request.GET.get('hstart', '')
    end     = request.GET.get('hend', '')
    if action in (BalanceLog.ACTION_ADD, BalanceLog.ACTION_DEDUCT):
        qs = qs.filter(action=action)
    if q:
        qs = qs.filter(Q(driver__full_name__icontains=q) | Q(driver__phone_number__icontains=q))
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    for log in qs:
        writer.writerow([
            log.id, log.driver.full_name, log.driver.phone_number, log.get_action_display(),
            log.amount, log.balance_after, log.note, log.created_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response


@panel_login_required
def balance_log_receipt_pdf(request, pk):
    log = get_object_or_404(BalanceLog.objects.select_related('driver'), pk=pk)
    buf = build_balance_receipt_pdf(log)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="chek_{log.id}.pdf"'
    return response


@panel_login_required
def topup_resolve(request, pk):
    topup = get_object_or_404(BalanceTopupRequest, pk=pk)
    if request.method == 'POST' and topup.status == BalanceTopupRequest.STATUS_PENDING:
        from django.utils import timezone
        action = request.POST.get('action')
        driver = topup.driver
        if action == 'approve':
            driver.balance += topup.amount
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=BalanceLog.ACTION_ADD, amount=topup.amount,
                balance_after=driver.balance, note=f"To'lov cheki tasdiqlandi #{topup.id} (panel)",
            )
            DriverActivityLog.objects.create(
                driver=driver, action=DriverActivityLog.ACTION_BALANCE,
                detail=f"Admin (panel): to'lov cheki #{topup.id} tasdiqlandi, +{topup.amount} UZS",
                ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            topup.status = BalanceTopupRequest.STATUS_APPROVED
            tg_balance_changed(driver, topup.amount, BalanceLog.ACTION_ADD)
            messages.success(request, f"To'lov #{topup.id} tasdiqlandi — {driver.full_name} balansi: {driver.balance} UZS")
        elif action == 'reject':
            reason = request.POST.get('reason', '').strip()
            topup.status = BalanceTopupRequest.STATUS_REJECTED
            topup.reject_reason = reason
            messages.success(request, f"To'lov #{topup.id} rad etildi.")
            from .driver_views import send_push_to_driver
            send_push_to_driver(
                driver, "❌ To'lov so'rovi rad etildi",
                f"{topup.amount} UZS to'lov so'rovingiz rad etildi." + (f" Sabab: {reason}" if reason else ''),
            )
        topup.resolved_at = timezone.now()
        topup.save(update_fields=['status', 'resolved_at', 'reject_reason'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:topup_list'))


@panel_login_required
def panel_events_api(request):
    """Operator panel ovozli bildirishnomasi uchun polling endpoint.
    ?since=<id> dan keyingi hodisalarni, har biri uchun mos ovoz URL bilan qaytaradi."""
    since = int(request.GET.get('since') or 0)
    events = list(PanelEvent.objects.filter(id__gt=since).order_by('id')[:20])
    sounds = PanelSound.get_map()
    data = []
    for e in events:
        snd = sounds.get(e.event_type)
        data.append({
            'id': e.id,
            'type': e.event_type,
            'message': e.message,
            'enabled': snd.enabled if snd else True,
            'sound_url': snd.resolve_url() if snd else None,
        })
    last_id = events[-1].id if events else since
    return JsonResponse({'events': data, 'last_id': last_id})


# ── Operator Bot — Admin buyruqlari (shaxsiy chat) ────────────────────────────

# Admin bilan buyurtma yaratish suhbati holati: {chat_id: {'step': ..., ...}}
_admin_sessions = {}

_ADMIN_MENU_KB = {
    'keyboard': [
        [{'text': '🆕 Yangi buyurtma'}],
        [{'text': '📋 Buyurtmalar'}, {'text': '🚖 Haydovchilar'}],
        [{'text': '🆕 Yangi haydovchilar'}, {'text': '📊 Statistika'}],
        [{'text': "💳 To'lov so'rovlari"}, {'text': '💰 Moliya'}],
        [{'text': '🆘 SOS'}, {'text': '🛡 Xavfsizlik'}],
        [{'text': '🔍 Qidiruv'}, {'text': '❓ Yordam'}],
    ],
    'resize_keyboard': True,
}

_LOCATION_KB = {
    'keyboard': [
        [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
        [{'text': "❌ Bekor qilish"}],
    ],
    'resize_keyboard': True,
}

_LOCATION_OR_SKIP_KB = {
    'keyboard': [
        [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
        [{'text': "O'tkazib yuborish ➡️"}, {'text': "❌ Bekor qilish"}],
    ],
    'resize_keyboard': True,
}

_CANCEL_KB = {
    'keyboard': [[{'text': "❌ Bekor qilish"}]],
    'resize_keyboard': True,
}


def _admin_bot_send(token, chat_id, text, keyboard=None):
    import urllib.request, urllib.parse, json as _j
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if keyboard:
        payload['reply_markup'] = _j.dumps(keyboard)
    data = urllib.parse.urlencode(payload).encode()
    try:
        urllib.request.urlopen(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=data, timeout=5
        )
    except Exception:
        pass


def _admin_help_text():
    return (
        "🤖 <b>Admin buyruqlari</b>\n\n"
        "🆕 Yangi buyurtma — mijoz uchun buyurtma yaratish (manzilni yozish yoki 📍 joylashuv yuborish mumkin)\n"
        "📋 Buyurtmalar — oxirgi faol buyurtmalar\n"
        "🚖 Haydovchilar — tasdiqlangan haydovchilar ro'yxati\n"
        "🆕 Yangi haydovchilar — tasdiqlanishi kerak bo'lgan haydovchilar\n"
        "📊 Statistika — bugungi buyurtmalar va tushum hisoboti\n"
        "/buyurtma &lt;id&gt; — buyurtma haqida to'liq ma'lumot\n"
        "/bekor &lt;id&gt; — buyurtmani bekor qilish\n"
        "/qayta &lt;id&gt; — buyurtmani qayta ochish va eng yaqin haydovchiga qayta yuborish\n"
        "/tasdiq &lt;id&gt; — yangi haydovchini tasdiqlash\n"
        "/rad &lt;id&gt; — yangi haydovchini rad etish\n"
        "/blok &lt;id&gt; — haydovchini bloklash\n"
        "/blokoch &lt;id&gt; — haydovchini blokdan chiqarish\n"
        "/balans &lt;id&gt; &lt;miqdor&gt; — balans qo'shish (ayirish uchun manfiy son, masalan -20000)\n"
        "/tarix &lt;id&gt; — haydovchi balans tarixi\n"
        "💳 To'lov so'rovlari — haydovchi yuborgan to'lov cheklarini ko'rish\n"
        "/tolovtasdiq &lt;id&gt; — to'lov chekini tasdiqlash (balansga qo'shiladi)\n"
        "/tolovrad &lt;id&gt; — to'lov chekini rad etish\n"
        "💰 Moliya — bugungi/haftalik GMV, komissiya daromadi, haydovchi ulushi\n"
        "🆘 SOS — hal qilinmagan SOS signallar\n"
        "/sosresolve &lt;id&gt; — SOS signalni hal qilindi deb belgilash\n"
        "🛡 Xavfsizlik — ochiq xavfsizlik hodisalari (tuhmat/shantaj/yuridik nizo)\n"
        "/xavfsizlikhal &lt;id&gt; — hodisani hal qilindi deb belgilash\n"
        "🔍 Qidiruv — telefon raqami yoki ID bo'yicha haydovchi/buyurtma qidirish\n"
        "/qidir &lt;so'rov&gt; — xuddi shu qidiruvni to'g'ridan-to'g'ri buyruq bilan\n"
        "/cancel — joriy amalni bekor qilish (masalan buyurtma yaratishni to'xtatish)"
    )


def _admin_search(query):
    """Telefon raqami yoki ID bo'yicha haydovchi/mijoz/buyurtmalarni qidiradi va
    natijani tayyor HTML matn sifatida qaytaradi (bot xabari uchun)."""
    query = query.strip()
    digits = query.replace(' ', '').replace('+', '')
    blocks = []

    if digits.isdigit():
        driver = Driver.objects.filter(pk=int(digits)).first()
        if driver:
            status = "🟢 Navbatda" if driver.is_on_duty else "⚪ Navbatda emas"
            blocked = " 🔒 BLOKLANGAN" if not driver.is_active else ''
            blocks.append(
                f"🚖 <b>Haydovchi #{driver.id}</b>\n{driver.full_name} | <code>{driver.phone_number}</code>\n"
                f"🚗 {driver.car_model} | {driver.car_number}\n💰 {driver.balance} UZS — {status}{blocked}"
            )
        order = Order.objects.filter(pk=int(digits)).select_related('client', 'driver').first()
        if order:
            status_labels = dict(Order.STATUS_CHOICES)
            blocks.append(
                f"📄 <b>Buyurtma #{order.id}</b> — {status_labels.get(order.status, order.status)}\n"
                f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>\n"
                f"🚖 Haydovchi: {order.driver.full_name if order.driver else '—'}\n"
                f"📍 {order.from_address}" + (f" → 🏁 {order.to_address}" if order.to_address else '')
            )

    phone_drivers = Driver.objects.filter(phone_number__icontains=digits or query)[:10] if (digits or query) else []
    for d in phone_drivers:
        status = "🟢 Navbatda" if d.is_on_duty else "⚪ Navbatda emas"
        blocked = " 🔒 BLOKLANGAN" if not d.is_active else ''
        blocks.append(
            f"🚖 <b>Haydovchi #{d.id}</b>\n{d.full_name} | <code>{d.phone_number}</code>\n"
            f"🚗 {d.car_model} | {d.car_number}\n💰 {d.balance} UZS — {status}{blocked}"
        )

    clients = Client.objects.filter(phone_number__icontains=digits or query)[:5] if (digits or query) else []
    for c in clients:
        recent = Order.objects.filter(client=c).order_by('-created_at')[:3]
        order_lines = '\n'.join(f"  #{o.id} — {dict(Order.STATUS_CHOICES).get(o.status, o.status)}" for o in recent) or '  —'
        blocks.append(
            f"👤 <b>Mijoz</b> {c.full_name or '—'} | <code>{c.phone_number}</code>"
            + (" 🚫 BLOKLANGAN" if c.is_blocked else '') + f"\nOxirgi buyurtmalar:\n{order_lines}"
        )

    if not blocks:
        return f"❌ \"{query}\" bo'yicha hech narsa topilmadi."
    return f"🔍 <b>\"{query}\" bo'yicha natijalar:</b>\n\n" + '\n\n'.join(blocks)


def _handle_admin_message(token, chat_id, text, location=None):
    """Admin (whitelist'dagi) shaxsiy chatdan yuborgan xabarni qayta ishlaydi."""
    from decimal import Decimal, InvalidOperation

    session = _admin_sessions.get(chat_id, {})
    step = session.get('step')

    # ── Joriy amaldan chiqish — istalgan bosqichda ishlaydi ──
    if step and text in ('/cancel', '❌ Bekor qilish'):
        _admin_sessions.pop(chat_id, None)
        _admin_bot_send(token, chat_id, "❌ Bekor qilindi.", _ADMIN_MENU_KB)
        return

    # ── Yangi buyurtma yaratish oqimi ──
    if step == 'order_phone':
        phone = text.replace(' ', '')
        if len(phone) < 9:
            _admin_bot_send(token, chat_id, "❌ Telefon raqam noto'g'ri. Qayta kiriting:", _CANCEL_KB)
        else:
            _admin_sessions[chat_id] = {'step': 'order_from', 'phone': phone}
            _admin_bot_send(token, chat_id,
                "📍 <b>Qayerdan yo'lga chiqadi?</b>\nManzilni yozing yoki joylashuvni yuboring:",
                _LOCATION_KB)
        return

    if step == 'order_from':
        if location:
            lat, lng = location.get('latitude'), location.get('longitude')
            address = reverse_geocode_address(lat, lng) or f"{lat:.5f}, {lng:.5f}"
            _admin_sessions[chat_id] = dict(session, step='order_to', from_address=address, from_lat=lat, from_lng=lng)
        else:
            _admin_sessions[chat_id] = dict(session, step='order_to', from_address=text)
        _admin_bot_send(token, chat_id,
            "🏁 <b>Qayerga boradi?</b>\nManzilni yozing, joylashuvni yuboring yoki o'tkazib yuboring:",
            _LOCATION_OR_SKIP_KB)
        return

    if step == 'order_to':
        to_lat, to_lng = None, None
        if location:
            to_lat, to_lng = location.get('latitude'), location.get('longitude')
            to_address = reverse_geocode_address(to_lat, to_lng) or f"{to_lat:.5f}, {to_lng:.5f}"
        elif text == "O'tkazib yuborish ➡️":
            to_address = ''
        else:
            to_address = text

        phone        = session.get('phone', '')
        from_address = session.get('from_address', '')
        from_lat     = session.get('from_lat')
        from_lng     = session.get('from_lng')

        client, _created = Client.objects.get_or_create(phone_number=phone)
        tariff = TariffSettings.get()

        distance_km = None
        price = None
        if from_lat and from_lng and to_lat and to_lng:
            distance_km = haversine(from_lat, from_lng, to_lat, to_lng)
            if distance_km:
                price = tariff.calc_price(distance_km)

        order = Order.objects.create(
            client=client,
            from_address=from_address, from_lat=from_lat, from_lng=from_lng,
            to_address=to_address, to_lat=to_lat, to_lng=to_lng,
            distance_km=distance_km,
            price=price,
            commission=tariff.commission,
            status='pending',
        )
        tg_new_order(order)
        if tariff.auto_dispatch:
            dispatch_order(order)

        _admin_sessions.pop(chat_id, None)
        _admin_bot_send(token, chat_id,
            f"✅ <b>Buyurtma #{order.id} yaratildi!</b>\n"
            f"📍 Qayerdan: {from_address}\n"
            + (f"🏁 Qayerga: {to_address}\n" if to_address else '')
            + (f"💰 Narx: {price:.0f} UZS\n" if price else ''),
            _ADMIN_MENU_KB)
        return

    if step == 'search_query':
        _admin_sessions.pop(chat_id, None)
        _admin_bot_send(token, chat_id, _admin_search(text), _ADMIN_MENU_KB)
        return

    # ── Menyu / buyruqlar ──
    if text in ('/start', '/menu'):
        _admin_sessions.pop(chat_id, None)
        pending_orders  = Order.objects.filter(status='pending').count()
        active_orders   = Order.objects.filter(status__in=Order.ACTIVE_STATUSES).count()
        on_duty         = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED).count()
        pending_drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count()
        pending_topups  = BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count()
        new_sos         = SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count()

        lines = ["👋 <b>Admin panel botiga xush kelibsiz!</b>\n"]
        if new_sos:
            lines.append(f"🆘 <b>{new_sos} ta hal qilinmagan SOS signal!</b>")
        lines.append(f"🕐 Kutilayotgan buyurtmalar: <b>{pending_orders}</b>")
        lines.append(f"⏳ Jarayondagi buyurtmalar: <b>{active_orders}</b>")
        lines.append(f"🟢 Navbatdagi haydovchilar: <b>{on_duty}</b>")
        if pending_drivers:
            lines.append(f"🆕 Tasdiq kutayotgan haydovchilar: <b>{pending_drivers}</b>")
        if pending_topups:
            lines.append(f"💳 Kutilayotgan to'lov so'rovlari: <b>{pending_topups}</b>")
        lines.append("\nQuyidagi menyudan tanlang:")

        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('🆕 Yangi buyurtma', '/neworder'):
        _admin_sessions[chat_id] = {'step': 'order_phone'}
        _admin_bot_send(token, chat_id,
            "📞 <b>Mijoz telefon raqamini yuboring:</b>\nMasalan: <code>+998901234567</code>",
            _CANCEL_KB)
        return

    if text in ('📋 Buyurtmalar', '/orders'):
        qs = (Order.objects.exclude(status__in=['completed', 'cancelled'])
              .select_related('client', 'driver').order_by('-created_at')[:10])
        if not qs:
            _admin_bot_send(token, chat_id, "📋 Hozircha faol buyurtmalar yo'q.", _ADMIN_MENU_KB)
            return
        status_labels = dict(Order.STATUS_CHOICES)
        blocks = []
        for o in qs:
            driver_name = o.driver.full_name if o.driver else '—'
            blocks.append(
                f"<b>#{o.id}</b> — {status_labels.get(o.status, o.status)}\n"
                f"👤 {o.client.phone_number} | 🚖 {driver_name}\n"
                f"📍 {o.from_address}" + (f" → 🏁 {o.to_address}" if o.to_address else '')
            )
        _admin_bot_send(token, chat_id, '📋 <b>Faol buyurtmalar:</b>\n\n' + '\n\n'.join(blocks), _ADMIN_MENU_KB)
        return

    if text in ('🚖 Haydovchilar', '/drivers'):
        qs = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).order_by('-is_on_duty', 'full_name')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "🚖 Haydovchilar topilmadi.", _ADMIN_MENU_KB)
            return
        lines = []
        for d in qs:
            status  = "🟢 Navbatda" if d.is_on_duty else "⚪ Navbatda emas"
            blocked = " 🔒 BLOKLANGAN" if not d.is_active else ''
            lines.append(f"<b>#{d.id}</b> {d.full_name} ({d.car_number}) — {status}{blocked}\n💰 {d.balance} UZS")
        lines.append("\n<i>/blok id, /blokoch id, /balans id miqdor</i>")
        _admin_bot_send(token, chat_id, '🚖 <b>Haydovchilar:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('❓ Yordam', '/help'):
        _admin_bot_send(token, chat_id, _admin_help_text(), _ADMIN_MENU_KB)
        return

    if text in ('🆕 Yangi haydovchilar', '/pending'):
        qs = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).order_by('-registered_at')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Tasdiqlanishi kerak bo'lgan haydovchilar yo'q.", _ADMIN_MENU_KB)
            return
        lines = []
        for d in qs:
            lines.append(
                f"<b>#{d.id}</b> {d.full_name} | <code>{d.phone_number}</code>\n"
                f"🚗 {d.car_model} | {d.car_number}"
            )
        lines.append("\n<i>/tasdiq id — tasdiqlash, /rad id — rad etish</i>")
        _admin_bot_send(token, chat_id, '🆕 <b>Yangi haydovchilar:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    parts = text.split()

    if len(parts) == 2 and parts[0] in ('/blok', '/blokoch') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.")
            return
        unblock = parts[0] == '/blokoch'
        driver.is_active = unblock
        driver.save(update_fields=['is_active'])
        DriverActivityLog.objects.create(
            driver=driver,
            action=DriverActivityLog.ACTION_UNBLOCK if unblock else DriverActivityLog.ACTION_BLOCK,
            detail='Admin (bot) tomonidan ' + ('blok ochildi' if unblock else 'bloklandi'),
        )
        if unblock:
            tg_driver_unblocked(driver)
            _admin_bot_send(token, chat_id, f"🔓 {driver.full_name} blokdan chiqarildi.", _ADMIN_MENU_KB)
        else:
            tg_driver_blocked(driver)
            _admin_bot_send(token, chat_id, f"🔒 {driver.full_name} bloklandi.", _ADMIN_MENU_KB)
        return

    if text in ('📊 Statistika', '/stat', '/statistika', '/hisobot'):
        from django.utils import timezone
        from django.db.models import Sum, Count
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        todays = Order.objects.filter(created_at__gte=today_start)
        agg = todays.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            active=Count('id', filter=Q(status__in=Order.ACTIVE_STATUSES)),
            pending=Count('id', filter=Q(status='pending')),
            revenue=Sum('price', filter=Q(status='completed')),
        )
        on_duty = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED).count()
        approved_total = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count()
        _admin_bot_send(token, chat_id,
            f"📊 <b>Bugungi statistika</b> ({today_start.strftime('%d.%m.%Y')})\n\n"
            f"🆕 Jami buyurtmalar: {agg['total']}\n"
            f"✅ Yakunlangan: {agg['completed']}\n"
            f"❌ Bekor qilingan: {agg['cancelled']}\n"
            f"⏳ Jarayonda: {agg['active']}\n"
            f"🕐 Kutilmoqda: {agg['pending']}\n"
            f"💰 Tushum: {agg['revenue'] or 0} UZS\n\n"
            f"🚖 Navbatda: {on_duty} / {approved_total} haydovchi",
            _ADMIN_MENU_KB)
        return

    if text in ('💰 Moliya', '/moliya'):
        from django.utils import timezone
        from django.db.models import Sum
        import datetime
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - datetime.timedelta(days=today_start.weekday())

        def _fin(qs):
            gmv = float(qs.aggregate(s=Sum('price'))['s'] or 0)
            commission = float(qs.aggregate(s=Sum('commission'))['s'] or 0)
            return gmv, commission, gmv - commission

        today_qs = Order.objects.filter(status='completed', created_at__gte=today_start)
        week_qs  = Order.objects.filter(status='completed', created_at__gte=week_start)
        t_gmv, t_comm, t_share = _fin(today_qs)
        w_gmv, w_comm, w_share = _fin(week_qs)
        _admin_bot_send(token, chat_id,
            f"💰 <b>Moliya</b>\n\n"
            f"<b>Bugun</b> ({today_start.strftime('%d.%m.%Y')})\n"
            f"GMV: {t_gmv:,.0f} UZS\n"
            f"Komissiya daromadi: {t_comm:,.0f} UZS\n"
            f"Haydovchi ulushi: {t_share:,.0f} UZS\n\n"
            f"<b>Shu hafta</b> ({week_start.strftime('%d.%m')} dan)\n"
            f"GMV: {w_gmv:,.0f} UZS\n"
            f"Komissiya daromadi: {w_comm:,.0f} UZS\n"
            f"Haydovchi ulushi: {w_share:,.0f} UZS".replace(',', ' '),
            _ADMIN_MENU_KB)
        return

    if text in ('🆘 SOS', '/sos'):
        qs = SosAlert.objects.exclude(status=SosAlert.STATUS_RESOLVED).select_related('driver').order_by('-created_at')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Hal qilinmagan SOS signal yo'q.", _ADMIN_MENU_KB)
            return
        lines = []
        for a in qs:
            loc = f"{a.latitude:.5f}, {a.longitude:.5f}" if a.latitude and a.longitude else (a.address or '—')
            lines.append(
                f"<b>#{a.id}</b> — {a.driver.full_name} | <code>{a.driver.phone_number}</code>\n"
                f"📍 {loc}\n"
                + (f"📝 {a.note}\n" if a.note else '')
                + f"🕐 {a.created_at:%d.%m.%Y %H:%M}"
            )
        lines.append("\n<i>/sosresolve id — hal qilindi deb belgilash</i>")
        _admin_bot_send(token, chat_id, '🆘 <b>Hal qilinmagan SOS signallar:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('🛡 Xavfsizlik', '/xavfsizlik'):
        qs = SecurityIncident.objects.exclude(status=SecurityIncident.STATUS_RESOLVED).order_by('-created_at')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Ochiq xavfsizlik hodisasi yo'q.", _ADMIN_MENU_KB)
            return
        type_labels = dict(SecurityIncident.TYPE_CHOICES)
        status_labels = dict(SecurityIncident.STATUS_CHOICES)
        lines = []
        for inc in qs:
            lines.append(
                f"<b>#{inc.id}</b> — {inc.title}\n"
                f"Turi: {type_labels.get(inc.incident_type, inc.incident_type)} | {status_labels.get(inc.status, inc.status)}\n"
                + (f"🚖 {inc.related_driver.full_name}\n" if inc.related_driver else '')
                + f"🕐 {inc.created_at:%d.%m.%Y %H:%M}"
            )
        lines.append("\n<i>/xavfsizlikhal id — hal qilindi deb belgilash</i>")
        _admin_bot_send(token, chat_id, '🛡 <b>Ochiq xavfsizlik hodisalari:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('🔍 Qidiruv', '/qidiruv'):
        _admin_sessions[chat_id] = {'step': 'search_query'}
        _admin_bot_send(token, chat_id,
            "🔍 <b>Qidiruv</b>\nHaydovchi/mijoz telefon raqami yoki buyurtma/haydovchi ID raqamini yuboring:",
            _CANCEL_KB)
        return

    if len(parts) == 2 and parts[0] in ('/buyurtma', '/qidir') and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('client', 'driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        status_labels = dict(Order.STATUS_CHOICES)
        lines = [
            f"📄 <b>Buyurtma #{order.id}</b> — {status_labels.get(order.status, order.status)}",
            f"👤 Mijoz: {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>",
            f"🚖 Haydovchi: {order.driver.full_name if order.driver else '—'}",
            f"📍 {order.from_address}" + (f" → 🏁 {order.to_address}" if order.to_address else ''),
        ]
        if order.distance_km:
            lines.append(f"📏 Masofa: {order.distance_km:.1f} km")
        if order.price:
            lines.append(f"💰 Narx: {order.price} UZS")
        lines.append(f"💳 To'lov: {'Naqd' if order.payment_type == 'cash' else 'Karta'}")
        lines.append(f"🕐 {order.created_at.strftime('%d.%m.%Y %H:%M')}")
        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if parts and parts[0] == '/qidir' and len(parts) >= 2:
        _admin_bot_send(token, chat_id, _admin_search(' '.join(parts[1:])), _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] == '/sosresolve' and parts[1].isdigit():
        alert = SosAlert.objects.filter(pk=int(parts[1])).exclude(status=SosAlert.STATUS_RESOLVED).select_related('driver').first()
        if not alert:
            _admin_bot_send(token, chat_id, "❌ Hal qilinmagan SOS signal topilmadi.", _ADMIN_MENU_KB)
            return
        from django.utils import timezone
        admin = BotAdmin.objects.filter(chat_id=str(chat_id)).first()
        alert.status = SosAlert.STATUS_RESOLVED
        alert.resolved_at = timezone.now()
        alert.resolved_by = admin.full_name if admin and admin.full_name else f'Bot ({chat_id})'
        alert.save(update_fields=['status', 'resolved_at', 'resolved_by'])
        from .utils import log_system_event
        log_system_event('sos_resolved', f"SOS #{alert.id} — {alert.driver.full_name} — bot orqali hal qilindi")
        _admin_bot_send(token, chat_id, f"✅ SOS #{alert.id} hal qilindi deb belgilandi.", _ADMIN_MENU_KB)
        return

    if len(parts) >= 2 and parts[0] == '/xavfsizlikhal' and parts[1].isdigit():
        incident = SecurityIncident.objects.filter(pk=int(parts[1])).exclude(status=SecurityIncident.STATUS_RESOLVED).first()
        if not incident:
            _admin_bot_send(token, chat_id, "❌ Ochiq xavfsizlik hodisasi topilmadi.", _ADMIN_MENU_KB)
            return
        from django.utils import timezone
        incident.status = SecurityIncident.STATUS_RESOLVED
        incident.resolved_at = timezone.now()
        note = ' '.join(parts[2:]).strip()
        if note:
            incident.resolution_note = note
        incident.save(update_fields=['status', 'resolved_at', 'resolution_note'])
        from .utils import log_system_event
        log_system_event('security_incident_resolved', f"Xavfsizlik hodisasi #{incident.id} — {incident.title} — bot orqali hal qilindi")
        _admin_bot_send(token, chat_id, f"✅ Xavfsizlik hodisasi #{incident.id} hal qilindi deb belgilandi.", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] == '/bekor' and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        if order.status in ('completed', 'cancelled'):
            _admin_bot_send(token, chat_id,
                f"⚠️ Buyurtma #{order.id} allaqachon {dict(Order.STATUS_CHOICES).get(order.status)}.",
                _ADMIN_MENU_KB)
            return
        refunded = False
        if order.driver_id and order.status in Order.ACTIVE_STATUSES:
            _refund_order_commission(order, order.driver, "admin (bot) tomonidan bekor qilindi")
            refunded = True
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])
        sms_order_status(order, 'cancelled')
        if order.driver:
            if not refunded:
                from .utils import send_fcm
                send_fcm(
                    order.driver.fcm_token,
                    title='Buyurtma bekor qilindi',
                    body=f"Buyurtma #{order.id} bekor qilindi.",
                    data={'type': 'order_cancelled', 'order_id': str(order.id)},
                )
            tg_order_cancelled(order, order.driver)
        else:
            log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — admin (bot) tomonidan bekor qilindi")
        _admin_bot_send(token, chat_id, f"❌ Buyurtma #{order.id} bekor qilindi.", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] == '/qayta' and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        reassignable = order.status == 'pending' or (order.driver_id and order.status in Order.ACTIVE_STATUSES)
        if not reassignable:
            _admin_bot_send(token, chat_id,
                f"⚠️ Buyurtma #{order.id} qayta yuborib bo'lmaydi ({dict(Order.STATUS_CHOICES).get(order.status)}).",
                _ADMIN_MENU_KB)
            return
        from .utils import send_fcm
        if order.driver_id and order.status in Order.ACTIVE_STATUSES:
            old_driver = order.driver
            commission = order.commission or TariffSettings.get().commission
            old_driver.balance += Decimal(str(commission))
            old_driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=old_driver, action=BalanceLog.ACTION_ADD, amount=commission,
                balance_after=old_driver.balance,
                note=f"Komissiya qaytarildi — buyurtma #{order.id} admin (bot) tomonidan qayta ochildi",
            )
            order.rejected_by.add(old_driver)
            order.driver = None
            send_fcm(
                old_driver.fcm_token,
                title='Buyurtma bekor qilindi',
                body=f"Buyurtma #{order.id} qayta ochildi. {commission} so'm balansingizga qaytarildi.",
                data={'type': 'order_cancelled', 'order_id': str(order.id)},
            )
        order.dispatched_to = None
        order.dispatched_at = None
        order.status = 'pending'
        order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'updated_at'])
        log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — admin (bot) tomonidan qayta ochildi")
        if TariffSettings.get().auto_dispatch:
            dispatch_order(order)
        _admin_bot_send(token, chat_id, f"🔄 Buyurtma #{order.id} qayta ochildi va eng yaqin haydovchiga yuborilmoqda.", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tasdiq', '/rad') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1]), approval_status=Driver.APPROVAL_PENDING).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Kutilayotgan haydovchi topilmadi.", _ADMIN_MENU_KB)
            return
        if parts[0] == '/tasdiq':
            driver.approval_status = Driver.APPROVAL_APPROVED
            driver.is_active = True
            if driver.user:
                driver.user.is_active = True
                driver.user.save(update_fields=['is_active'])
            driver.save(update_fields=['approval_status', 'is_active'])
            tg_driver_approved(driver)
            _admin_bot_send(token, chat_id, f"✅ {driver.full_name} tasdiqlandi.", _ADMIN_MENU_KB)
        else:
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
            driver.save(update_fields=['approval_status', 'is_active'])
            tg_driver_rejected(driver)
            _admin_bot_send(token, chat_id, f"🚫 {driver.full_name} rad etildi.", _ADMIN_MENU_KB)
        return

    if len(parts) == 3 and parts[0] == '/balans' and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.")
            return
        try:
            amount = Decimal(parts[2])
        except InvalidOperation:
            _admin_bot_send(token, chat_id, "❌ Miqdor noto'g'ri. Masalan: /balans 5 50000")
            return
        action = BalanceLog.ACTION_DEDUCT if amount < 0 else BalanceLog.ACTION_ADD
        driver.balance += amount
        driver.save(update_fields=['balance'])
        BalanceLog.objects.create(
            driver=driver, action=action, amount=abs(amount),
            balance_after=driver.balance, note='Admin (bot)',
        )
        DriverActivityLog.objects.create(
            driver=driver, action=DriverActivityLog.ACTION_BALANCE,
            detail=f"Admin (bot): {'+' if amount >= 0 else ''}{amount} UZS",
        )
        tg_balance_changed(driver, abs(amount), action)
        _admin_bot_send(token, chat_id, f"💰 {driver.full_name} balansi yangilandi: {driver.balance} UZS", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tarix', '/balanstarix') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.", _ADMIN_MENU_KB)
            return
        logs = driver.balance_logs.all()[:10]
        if not logs:
            _admin_bot_send(token, chat_id, f"📄 {driver.full_name} — balans tarixi bo'sh.", _ADMIN_MENU_KB)
            return
        lines = [f"📄 <b>{driver.full_name} — balans tarixi</b>\n"]
        for log in logs:
            sign = '+' if log.action == BalanceLog.ACTION_ADD else '-'
            lines.append(f"{sign}{log.amount} UZS → {log.balance_after} UZS | {log.created_at.strftime('%d.%m %H:%M')}" + (f" | {log.note}" if log.note else ''))
        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('💳 To\'lov so\'rovlari', '/tolovlar'):
        qs = BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).select_related('driver')[:10]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Kutilayotgan to'lov so'rovlari yo'q.", _ADMIN_MENU_KB)
            return
        lines = []
        for t in qs:
            lines.append(
                f"<b>#{t.id}</b> {t.driver.full_name} | <code>{t.driver.phone_number}</code>\n"
                f"💰 {t.amount} UZS | {t.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        lines.append("\n<i>/tolovtasdiq id — tasdiqlash, /tolovrad id — rad etish</i>")
        _admin_bot_send(token, chat_id, "💳 <b>To'lov so'rovlari:</b>\n\n" + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tolovtasdiq', '/tolovrad') and parts[1].isdigit():
        topup = BalanceTopupRequest.objects.filter(pk=int(parts[1]), status=BalanceTopupRequest.STATUS_PENDING).select_related('driver').first()
        if not topup:
            _admin_bot_send(token, chat_id, "❌ Kutilayotgan to'lov so'rovi topilmadi.", _ADMIN_MENU_KB)
            return
        from django.utils import timezone
        driver = topup.driver
        if parts[0] == '/tolovtasdiq':
            driver.balance += topup.amount
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=BalanceLog.ACTION_ADD, amount=topup.amount,
                balance_after=driver.balance, note=f"To'lov cheki tasdiqlandi #{topup.id}",
            )
            DriverActivityLog.objects.create(
                driver=driver, action=DriverActivityLog.ACTION_BALANCE,
                detail=f"Admin (bot): to'lov cheki #{topup.id} tasdiqlandi, +{topup.amount} UZS",
            )
            topup.status = BalanceTopupRequest.STATUS_APPROVED
            topup.resolved_at = timezone.now()
            topup.save(update_fields=['status', 'resolved_at'])
            tg_balance_changed(driver, topup.amount, BalanceLog.ACTION_ADD)
            _admin_bot_send(token, chat_id, f"✅ To'lov #{topup.id} tasdiqlandi. {driver.full_name} balansi: {driver.balance} UZS", _ADMIN_MENU_KB)
        else:
            topup.status = BalanceTopupRequest.STATUS_REJECTED
            topup.resolved_at = timezone.now()
            topup.save(update_fields=['status', 'resolved_at'])
            from .driver_views import send_push_to_driver
            send_push_to_driver(driver, "❌ To'lov so'rovi rad etildi", f"{topup.amount} UZS to'lov so'rovingiz rad etildi.")
            _admin_bot_send(token, chat_id, f"🚫 To'lov #{topup.id} rad etildi.", _ADMIN_MENU_KB)
        return

    _admin_bot_send(token, chat_id, "Tushunmadim 🤔\n/help — buyruqlar ro'yxati", _ADMIN_MENU_KB)


@csrf_exempt
def operator_bot_webhook(request):
    """Operator bot webhook — guruhdan callback_query va admin shaxsiy buyruqlarini qayta ishlash."""
    import json as _json
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('ok')
    try:
        data = _json.loads(request.body)
    except Exception:
        from django.http import HttpResponse
        return HttpResponse('ok')

    # Shaxsiy chatdan kelgan matnli xabar — whitelist'dagi adminlar uchun buyruqlar
    msg = data.get('message')
    if msg and msg.get('chat', {}).get('type') == 'private':
        from .models import BotSettings
        bot   = BotSettings.get()
        token = bot.bot_token.strip()
        chat_id  = str(msg.get('chat', {}).get('id', ''))
        text     = (msg.get('text') or '').strip()
        location = msg.get('location')
        if token and (text or location) and BotAdmin.objects.filter(chat_id=chat_id, is_active=True).exists():
            _handle_admin_message(token, chat_id, text, location=location)
        from django.http import HttpResponse
        return HttpResponse('ok')

    # Faqat callback_query ni qayta ishlaymiz
    cb = data.get('callback_query')
    if not cb:
        from django.http import HttpResponse
        return HttpResponse('ok')

    cb_id   = cb['id']
    cb_data = cb.get('data', '')

    from .models import BotSettings
    bot = BotSettings.get()
    token = bot.bot_token.strip()
    if not token:
        from django.http import HttpResponse
        return HttpResponse('ok')

    def _answer(text):
        import urllib.request, urllib.parse
        payload = urllib.parse.urlencode({'callback_query_id': cb_id, 'text': text}).encode()
        try:
            urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/answerCallbackQuery',
                data=payload, timeout=5
            )
        except Exception:
            pass

    # callback_data formatlar: order_<id>, driver_<id>
    if cb_data.startswith('order_'):
        _answer(f"Buyurtma #{cb_data.split('_')[1]} — admin panelda ko'ring")
    elif cb_data.startswith('driver_'):
        _answer(f"Haydovchi #{cb_data.split('_')[1]} — admin panelda ko'ring")
    else:
        _answer('OK')

    from django.http import HttpResponse
    return HttpResponse('ok')


@system_login_required
def operator_bot_set_webhook(request):
    """Operator bot webhook URL ni Telegram ga o'rnatish.
    Diqqat (xavfsizlik): avval bu view hech qanday autentifikatsiya
    tekshiruvisiz edi — endi bot_settings sahifasining bir qismi sifatida
    faqat tizim (superuser) roliga ochiq."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'POST talab qilinadi'})
    from .models import BotSettings
    from django.conf import settings as django_settings
    bot = BotSettings.get()
    token = bot.bot_token.strip()
    if not token:
        return JsonResponse({'ok': False, 'message': 'Bot token kiritilmagan'})
    webhook_url = f"{request.scheme}://{request.get_host()}/panel/bot/operator-webhook/"
    import urllib.request, urllib.parse
    try:
        data = urllib.parse.urlencode({'url': webhook_url}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/setWebhook',
            data=data,
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json as _json
            result = _json.loads(resp.read().decode())
        if result.get('ok'):
            return JsonResponse({'ok': True, 'message': f'Webhook o\'rnatildi: {webhook_url}'})
        return JsonResponse({'ok': False, 'message': result.get('description', 'Xatolik')})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)})


@system_login_required
def bot_webhook_status(request):
    """Telegram'ning o'zidan hozir qaysi webhook URL o'rnatilganini, kutilayotgan
    (pending) yangilanishlar sonini va oxirgi xatoni so'rab oladi — "Webhookni
    o'rnatish" tugmasi bilan bog'liq holatni diagnostika qilish uchun."""
    from .models import BotSettings
    bot = BotSettings.get()
    token = bot.bot_token.strip()
    if not token:
        return JsonResponse({'ok': False, 'message': 'Bot token kiritilmagan'})
    import urllib.request
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/getWebhookInfo')
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json as _json
            result = _json.loads(resp.read().decode())
        if not result.get('ok'):
            return JsonResponse({'ok': False, 'message': result.get('description', 'Xatolik')})
        info = result.get('result', {})
        return JsonResponse({
            'ok': True,
            'url': info.get('url') or None,
            'pending_update_count': info.get('pending_update_count', 0),
            'last_error_message': info.get('last_error_message'),
            'last_error_date': info.get('last_error_date'),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)})


@system_login_required
def client_bot_set_webhook(request):
    """Mijoz boti webhook URL ni Telegram ga o'rnatish — operator bot uchun
    bo'lgan operator_bot_set_webhook bilan bir xil, faqat client_bot_token
    va client-webhook manzilidan foydalanadi."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'POST talab qilinadi'})
    from .models import BotSettings
    bot = BotSettings.get()
    token = bot.client_bot_token.strip()
    if not token:
        return JsonResponse({'ok': False, 'message': 'Mijoz bot token kiritilmagan'})
    webhook_url = f"{request.scheme}://{request.get_host()}/panel/bot/client-webhook/"
    import urllib.request, urllib.parse
    try:
        data = urllib.parse.urlencode({'url': webhook_url}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/setWebhook',
            data=data,
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json as _json
            result = _json.loads(resp.read().decode())
        if result.get('ok'):
            return JsonResponse({'ok': True, 'message': f'Webhook o\'rnatildi: {webhook_url}'})
        return JsonResponse({'ok': False, 'message': result.get('description', 'Xatolik')})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)})


@system_login_required
def client_bot_webhook_status(request):
    """Mijoz boti uchun getWebhookInfo — bot_webhook_status'ning client_bot_token
    versiyasi."""
    from .models import BotSettings
    bot = BotSettings.get()
    token = bot.client_bot_token.strip()
    if not token:
        return JsonResponse({'ok': False, 'message': 'Mijoz bot token kiritilmagan'})
    import urllib.request
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/getWebhookInfo')
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json as _json
            result = _json.loads(resp.read().decode())
        if not result.get('ok'):
            return JsonResponse({'ok': False, 'message': result.get('description', 'Xatolik')})
        info = result.get('result', {})
        return JsonResponse({
            'ok': True,
            'url': info.get('url') or None,
            'pending_update_count': info.get('pending_update_count', 0),
            'last_error_message': info.get('last_error_message'),
            'last_error_date': info.get('last_error_date'),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)})


@panel_login_required
def driver_map(request):
    from taxi.models import MapsSettings
    drivers = Driver.objects.filter(
        is_active=True,
        approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False,
        longitude__isnull=False,
    )
    maps = MapsSettings.get()
    return render(request, 'taxi/driver_map.html', {
        'drivers': drivers,
        'yandex_api_key': maps.yandex_mapkit_key,
    })


@panel_login_required
def active_drivers_locations(request):
    from django.utils import timezone
    from django.db.models import Count, Q
    today = timezone.now().date()
    drivers = Driver.objects.filter(
        is_active=True,
        approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False,
        longitude__isnull=False
    ).annotate(
        today_orders_count=Count(
            'orders', filter=Q(orders__created_at__date=today) & ~Q(orders__status='cancelled')
        )
    )
    now = timezone.now()
    data = []
    for d in drivers:
        is_online = bool(d.last_seen) and (now - d.last_seen).total_seconds() < ONLINE_THRESHOLD_SECONDS
        data.append({
            'id': d.id,
            'full_name': d.full_name,
            'phone_number': d.phone_number,
            'car_model': d.car_model,
            'car_number': d.car_number,
            'latitude': d.latitude,
            'longitude': d.longitude,
            'balance': str(d.balance),
            'today_orders_count': d.today_orders_count,
            'last_address': d.last_address or '',
            'photo_url': d.photo.url if d.photo else '',
            'is_online': is_online,
            'is_on_duty': d.is_on_duty,
        })
    return JsonResponse({'drivers': data})


# ── Operator Chat ──────────────────────────────────────────────────────────────────

@panel_login_required
def operator_chat(request):
    drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).order_by('full_name')
    driver_data = []
    for d in drivers:
        last_msg = ChatMessage.objects.filter(driver=d).order_by('-created_at').first()
        unread   = ChatMessage.objects.filter(driver=d, sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
        driver_data.append({'driver': d, 'last_msg': last_msg, 'unread': unread})

    selected_id     = request.GET.get('driver_id')
    selected_driver = None
    messages        = []
    if selected_id:
        selected_driver = Driver.objects.filter(pk=selected_id).first()
        if selected_driver:
            ChatMessage.objects.filter(
                driver=selected_driver, sender=ChatMessage.SENDER_DRIVER, is_read=False
            ).update(is_read=True)
            messages = ChatMessage.objects.filter(driver=selected_driver).order_by('created_at')

    if request.method == 'POST' and request.POST.get('group_text'):
        text = request.POST.get('group_text', '').strip()
        if text:
            GroupMessage.objects.create(driver=None, sender_name='Operator', text=text)
        return redirect(request.path + ('?driver_id=' + selected_id if selected_id else '') + '#group')

    if request.method == 'POST' and selected_driver:
        text  = request.POST.get('text', '').strip()
        audio = request.FILES.get('audio')
        if text or audio:
            ChatMessage.objects.create(
                driver=selected_driver,
                sender=ChatMessage.SENDER_OPERATOR,
                text=text,
                audio=audio or None,
            )
            if text:
                _send_fcm_to_driver(selected_driver, '💬 Operator', text)
            elif audio:
                _send_fcm_to_driver(selected_driver, '🎤 Operator', 'Ovozli xabar')
        return redirect(f"{request.path}?driver_id={selected_id}")

    return render(request, 'taxi/operator_chat.html', {
        'driver_data':     driver_data,
        'selected_driver': selected_driver,
        'messages':        messages,
        'selected_id':     selected_id,
        'group_messages':  GroupMessage.objects.select_related('driver').order_by('created_at')[:200],
    })


def operator_chat_unread(request):
    """AJAX: jami o'qilmagan xabarlar soni."""
    count = ChatMessage.objects.filter(sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
    return JsonResponse({'unread': count})


@panel_login_required
@require_POST
def operator_chat_typing(request):
    """AJAX: operator xabar yozayotganini haydovchi ilovasiga bildirish uchun belgi qo'yadi."""
    from django.utils import timezone
    driver_id = request.POST.get('driver_id')
    driver = Driver.objects.filter(pk=driver_id).first()
    if driver:
        driver.operator_typing_at = timezone.now()
        driver.save(update_fields=['operator_typing_at'])
    return JsonResponse({'ok': True})


def _send_fcm_to_driver(driver, title, body):
    import urllib.request, json
    from django.conf import settings
    fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
    if not fcm_key or not driver.fcm_token:
        return
    try:
        data = json.dumps({
            'to': driver.fcm_token,
            'notification': {'title': title, 'body': body, 'sound': 'default'},
            'data': {'type': 'chat'},
        }).encode()
        req = urllib.request.Request(
            'https://fcm.googleapis.com/fcm/send',
            data=data,
            headers={'Authorization': f'key={fcm_key}', 'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ── Login / Logout ─────────────────────────────────────────────────────────────

def panel_login(request):
    # Diqqat: faqat is_authenticated emas, is_staff ham tekshiriladi — aks
    # holda (masalan) haydovchi hisobi bilan kirgan foydalanuvchi bu yerga
    # kelganda "allaqachon kirgan" deb dashboard'ga yo'naltirilardi, dashboard
    # esa (endi is_staff talab qilgani uchun) uni yana shu yerga qaytarib,
    # cheksiz redirect siklini hosil qilardi.
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('taxi:panel_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            from .utils import log_system_event
            log_system_event('panel_login_success', f"'{username}' panelga kirdi", request=request, user=user)
            return redirect(request.GET.get('next', 'taxi:panel_dashboard'))
        from .utils import log_system_event
        log_system_event('panel_login_failed', f"'{username}' — noto'g'ri login/parol", level='warning', request=request)
        messages.error(request, "Login yoki parol noto'g'ri!")
    return render(request, 'taxi/login.html')


def panel_logout(request):
    logout(request)
    return redirect('taxi:panel_login')


# ── Tizim (dasturchi) paneli — alohida kirish ──────────────────────────────
def system_login(request):
    # Diqqat: is_superuser ham tekshiriladi (is_staff yetarli emas) — aks
    # holda oddiy admin hisobi bilan kirgan foydalanuvchi shu sahifada
    # "allaqachon kirgan" deb tizim dashboard'iga yo'naltirilardi, u esa
    # (is_superuser talab qilgani uchun) yana shu yerga qaytarib, cheksiz
    # redirect siklini hosil qilardi (panel_login'dagi bilan bir xil sabab).
    if request.user.is_authenticated and request.user.is_staff and request.user.is_superuser:
        return redirect('system:system_status')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff and user.is_superuser:
            login(request, user)
            from .utils import log_system_event
            log_system_event('system_login_success', f"'{username}' tizim paneliga kirdi", request=request, user=user)
            return redirect(request.GET.get('next', 'system:system_status'))
        from .utils import log_system_event
        # Diqqat: bu ayniqsa muhim signal — is_staff bo'lib, lekin is_superuser
        # bo'lmagan (oddiy admin) hisob shu yerga kirishga urinishi ham
        # "warning" sifatida qayd etiladi, chunki bu ruxsat chegarasini
        # tekshirib ko'rish (yoki huquqni suiiste'mol qilishga urinish)
        # bo'lishi mumkin.
        log_system_event('system_login_failed', f"'{username}' — noto'g'ri login/parol yoki tizim huquqi yo'q", level='warning', request=request)
        messages.error(request, "Login yoki parol noto'g'ri, yoki sizda tizim paneliga kirish huquqi yo'q!")
    return render(request, 'taxi/system_login.html')


def system_logout(request):
    logout(request)
    return redirect('system:system_login')


# ── Driver Edit ────────────────────────────────────────────────────────────────

@panel_login_required
def driver_edit(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', driver.full_name).strip()
        phone_number = request.POST.get('phone_number', driver.phone_number).strip()
        car_model    = request.POST.get('car_model', driver.car_model).strip()
        car_number   = request.POST.get('car_number', driver.car_number).strip()
        car_type     = request.POST.get('car_type', driver.car_type)
        new_password = request.POST.get('new_password', '').strip()
        if Driver.objects.filter(phone_number=phone_number).exclude(pk=driver.pk).exists():
            messages.error(request, f"Telefon raqami {phone_number} boshqa haydovchiga tegishli.")
        elif new_password and len(new_password) < 6:
            messages.error(request, "Parol kamida 6 ta belgi bo'lishi kerak.")
        else:
            driver.full_name    = full_name
            driver.phone_number = phone_number
            driver.car_model    = car_model
            driver.car_number   = car_number
            driver.car_type     = car_type
            driver.save(update_fields=['full_name', 'phone_number', 'car_model', 'car_number', 'car_type'])
            if new_password:
                if driver.user:
                    driver.user.set_password(new_password)
                    driver.user.save()
                else:
                    messages.error(request, "Haydovchiga bog'langan foydalanuvchi topilmadi, parol o'zgartirilmadi.")
            messages.success(request, "Haydovchi ma'lumotlari yangilandi.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:driver_detail', args=[pk]))


# ── Order price edit ───────────────────────────────────────────────────────────

@panel_login_required
def order_edit_price(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        try:
            order.price = Decimal(request.POST.get('price', ''))
            order.save(update_fields=['price'])
        except (InvalidOperation, TypeError):
            pass
    return redirect('taxi:order_detail', pk=pk)


# ── Orders CSV export ──────────────────────────────────────────────────────────

@panel_login_required
def orders_export_csv(request):
    qs = Order.objects.select_related('client', 'driver').order_by('-created_at')
    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')
    status    = request.GET.get('status')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if status:
        qs = qs.filter(status=status)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['#', 'Mijoz', 'Telefon', 'Qayerdan', 'Qayerga', 'Haydovchi', 'Narx', "To'lov", 'Holat', 'Vaqt'])
    for o in qs:
        writer.writerow([
            o.id, o.client.full_name or '', o.client.phone_number,
            o.from_address, o.to_address,
            o.driver.full_name if o.driver else '',
            o.price or '', o.get_payment_type_display(),
            o.get_status_display(), o.created_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response


# ── Statistics ─────────────────────────────────────────────────────────────────

def _statistics_range(request):
    """GET parametrlaridan tahlil qilinadigan sana oralig'ini aniqlaydi:
    ?start=YYYY-MM-DD&end=YYYY-MM-DD berilsa shu oraliq, aks holda ?period=week/month/year."""
    from django.utils import timezone
    from datetime import timedelta, date as date_cls

    today  = timezone.now().date()
    period = request.GET.get('period', 'week')
    start_str = request.GET.get('start')
    end_str   = request.GET.get('end')

    if start_str and end_str:
        try:
            start_date = date_cls.fromisoformat(start_str)
            end_date   = date_cls.fromisoformat(end_str)
            if start_date > end_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            start_date, end_date = today - timedelta(days=6), today
    else:
        days = 30 if period == 'month' else (365 if period == 'year' else 7)
        start_date, end_date = today - timedelta(days=days - 1), today

    return period, start_date, end_date


@panel_login_required
def statistics(request):
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import ExtractHour
    from datetime import timedelta
    from decimal import Decimal

    period, start_date, end_date = _statistics_range(request)
    range_days = (end_date - start_date).days + 1

    labels, revenues, counts = [], [], []
    for i in range(range_days):
        day = start_date + timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        labels.append(day.strftime('%d/%m'))
        revenues.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        counts.append(day_qs.count())

    range_qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    range_completed_qs = range_qs.filter(status='completed')
    range_orders_count    = range_qs.count()
    range_cancelled_count = range_qs.filter(status='cancelled').count()
    cancellation_rate = round(range_cancelled_count / range_orders_count * 100, 1) if range_orders_count else 0
    range_revenue = float(range_completed_qs.aggregate(s=Sum('price'))['s'] or 0)

    # Oldingi (bir xil uzunlikdagi) davrga nisbatan o'sish foizi
    prev_end_date   = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=range_days - 1)
    prev_qs = Order.objects.filter(created_at__date__gte=prev_start_date, created_at__date__lte=prev_end_date)
    prev_revenue = float(prev_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    prev_orders_count = prev_qs.count()
    revenue_growth_pct = round((range_revenue - prev_revenue) / prev_revenue * 100, 1) if prev_revenue else None
    orders_growth_pct  = round((range_orders_count - prev_orders_count) / prev_orders_count * 100, 1) if prev_orders_count else None

    # Soatlik yuklama (tanlangan davr bo'yicha, 0-23 soat)
    hourly_counts = [0] * 24
    for row in range_qs.annotate(hour=ExtractHour('created_at')).values('hour').annotate(c=Count('id')):
        hourly_counts[row['hour']] = row['c']

    # Hudud bo'yicha top manzillar (qayerdan)
    top_addresses = list(
        range_qs.exclude(from_address='').values('from_address')
        .annotate(c=Count('id')).order_by('-c')[:10]
    )

    top_drivers = Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(completed__gt=0).order_by('-completed')[:10]

    top_clients = Client.objects.annotate(
        total=Count('orders', filter=Q(orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        spent=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(total__gt=0).order_by('-total')[:10]

    total_revenue = Order.objects.filter(status='completed').aggregate(s=Sum('price'))['s'] or Decimal('0')
    avg_price     = Order.objects.filter(status='completed').aggregate(a=Avg('price'))['a'] or Decimal('0')

    return render(request, 'taxi/statistics.html', {
        'period': period, 'labels': labels, 'revenues': revenues, 'counts': counts,
        'start_date': start_date, 'end_date': end_date,
        'custom_range': bool(request.GET.get('start') and request.GET.get('end')),
        'top_drivers': top_drivers, 'top_clients': top_clients,
        'total_revenue': total_revenue, 'avg_price': avg_price,
        'total_orders': Order.objects.count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'cancelled_orders': Order.objects.filter(status='cancelled').count(),
        'total_drivers': Driver.objects.filter(approval_status='approved').count(),
        'total_clients': Client.objects.count(),
        'blocked_clients': Client.objects.filter(is_blocked=True).count(),
        'range_revenue': range_revenue,
        'range_orders_count': range_orders_count,
        'cancellation_rate': cancellation_rate,
        'revenue_growth_pct': revenue_growth_pct,
        'orders_growth_pct': orders_growth_pct,
        'hourly_labels': [f"{h:02d}" for h in range(24)],
        'hourly_counts': hourly_counts,
        'top_addresses': top_addresses,
    })


@panel_login_required
def statistics_export_csv(request):
    from django.db.models import Sum
    from datetime import timedelta

    period, start_date, end_date = _statistics_range(request)
    range_days = (end_date - start_date).days + 1

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="statistika_{start_date}_{end_date}.csv"'
    response.write('﻿')
    writer = csv.writer(response)

    writer.writerow(['Sana', 'Daromad (UZS)', 'Buyurtmalar soni'])
    for i in range(range_days):
        day = start_date + timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        revenue = day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0
        writer.writerow([day.strftime('%d.%m.%Y'), revenue, day_qs.count()])

    writer.writerow([])
    writer.writerow(['Top haydovchilar', 'Safarlar', 'Daromad (UZS)'])
    top_drivers = Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(completed__gt=0).order_by('-completed')[:20]
    for d in top_drivers:
        writer.writerow([d.full_name, d.completed, d.earned or 0])

    writer.writerow([])
    writer.writerow(['Top hududlar (qayerdan)', 'Buyurtmalar soni'])
    range_qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    for row in range_qs.exclude(from_address='').values('from_address').annotate(c=Count('id')).order_by('-c')[:20]:
        writer.writerow([row['from_address'], row['c']])

    return response


# ── Moliya ───────────────────────────────────────────────────────────────────

def _finance_breakdown(completed_qs, field, choices):
    from django.db.models import Sum, Count
    labels = dict(choices)
    rows = list(
        completed_qs.values(field).annotate(total=Sum('price'), commission=Sum('commission'), c=Count('id')).order_by('-total')
    )
    for row in rows:
        row['label'] = labels.get(row[field], row[field])
    return rows


@panel_login_required
def finance_dashboard(request):
    from django.db.models import Sum, Count
    from datetime import timedelta

    period, start_date, end_date = _statistics_range(request)
    range_days = (end_date - start_date).days + 1

    completed_qs = Order.objects.filter(status='completed', created_at__date__gte=start_date, created_at__date__lte=end_date)
    gmv = float(completed_qs.aggregate(s=Sum('price'))['s'] or 0)
    commission_revenue = float(completed_qs.aggregate(s=Sum('commission'))['s'] or 0)
    driver_share = gmv - commission_revenue
    take_rate = round(commission_revenue / gmv * 100, 1) if gmv else 0

    prev_end_date   = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=range_days - 1)
    prev_commission = float(Order.objects.filter(
        status='completed', created_at__date__gte=prev_start_date, created_at__date__lte=prev_end_date
    ).aggregate(s=Sum('commission'))['s'] or 0)
    commission_growth_pct = round((commission_revenue - prev_commission) / prev_commission * 100, 1) if prev_commission else None

    labels, daily_gmv, daily_commission = [], [], []
    for i in range(range_days):
        day = start_date + timedelta(days=i)
        day_qs = Order.objects.filter(status='completed', created_at__date=day)
        labels.append(day.strftime('%d/%m'))
        daily_gmv.append(float(day_qs.aggregate(s=Sum('price'))['s'] or 0))
        daily_commission.append(float(day_qs.aggregate(s=Sum('commission'))['s'] or 0))

    payment_breakdown  = _finance_breakdown(completed_qs, 'payment_type', Order.PAYMENT_CHOICES)
    car_type_breakdown = _finance_breakdown(completed_qs, 'car_type', Driver.CAR_TYPE_CHOICES)

    top_by_commission = Driver.objects.annotate(
        commission_sum=Sum('orders__commission', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
    ).filter(completed__gt=0).order_by('-commission_sum')[:10]

    topped_up = float(BalanceLog.objects.filter(
        action=BalanceLog.ACTION_ADD, created_at__date__gte=start_date, created_at__date__lte=end_date
    ).aggregate(s=Sum('amount'))['s'] or 0)
    manual_deducted = float(BalanceLog.objects.filter(
        action=BalanceLog.ACTION_DEDUCT, created_at__date__gte=start_date, created_at__date__lte=end_date
    ).aggregate(s=Sum('amount'))['s'] or 0)
    voucher_cost = float(FlyerVoucher.objects.filter(
        is_used=True, used_at__date__gte=start_date, used_at__date__lte=end_date
    ).aggregate(s=Sum('amount'))['s'] or 0)

    return render(request, 'taxi/finance.html', {
        'period': period, 'start_date': start_date, 'end_date': end_date,
        'custom_range': bool(request.GET.get('start') and request.GET.get('end')),
        'gmv': gmv,
        'commission_revenue': commission_revenue,
        'driver_share': driver_share,
        'take_rate': take_rate,
        'commission_growth_pct': commission_growth_pct,
        'labels': labels, 'daily_gmv': daily_gmv, 'daily_commission': daily_commission,
        'payment_breakdown': payment_breakdown,
        'car_type_breakdown': car_type_breakdown,
        'top_by_commission': top_by_commission,
        'topped_up': topped_up,
        'manual_deducted': manual_deducted,
        'voucher_cost': voucher_cost,
    })


@panel_login_required
def finance_export_csv(request):
    from django.db.models import Sum, Count

    period, start_date, end_date = _statistics_range(request)
    completed_qs = Order.objects.filter(status='completed', created_at__date__gte=start_date, created_at__date__lte=end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="moliya_{start_date}_{end_date}.csv"'
    response.write('﻿')
    writer = csv.writer(response)

    gmv = completed_qs.aggregate(s=Sum('price'))['s'] or 0
    commission = completed_qs.aggregate(s=Sum('commission'))['s'] or 0
    writer.writerow(['Davr', f'{start_date} — {end_date}'])
    writer.writerow(['Umumiy aylanma (GMV)', gmv])
    writer.writerow(['Kompaniya komissiya daromadi', commission])
    writer.writerow(['Haydovchilar ulushi', gmv - commission])
    writer.writerow([])

    writer.writerow(['Top haydovchilar (komissiya bo\'yicha)', 'Safarlar', 'Komissiya (UZS)'])
    top_by_commission = Driver.objects.annotate(
        commission_sum=Sum('orders__commission', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
    ).filter(completed__gt=0).order_by('-commission_sum')[:50]
    for d in top_by_commission:
        writer.writerow([d.full_name, d.completed, d.commission_sum or 0])

    return response


# ── Xavfsizlik (yuridik hujjatlar va jiddiy voqealar) ───────────────────────

DOCUMENT_EXPIRY_WARNING_DAYS = 30  # hujjat muddati shuncha kun qolganda ogohlantiriladi


@panel_login_required
def security_dashboard(request):
    from datetime import timedelta
    from django.utils import timezone

    tab = request.GET.get('tab', 'incidents')
    today = timezone.now().date()
    expiry_warning_date = today + timedelta(days=DOCUMENT_EXPIRY_WARNING_DAYS)

    incidents = SecurityIncident.objects.select_related('related_driver', 'related_client', 'created_by').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        incidents = incidents.filter(status=status_filter)

    documents = LegalDocument.objects.order_by('expires_at')

    return render(request, 'taxi/security.html', {
        'tab': tab,
        'incidents': incidents,
        'status_filter': status_filter,
        'open_incident_count': SecurityIncident.objects.exclude(status=SecurityIncident.STATUS_RESOLVED).count(),
        'documents': documents,
        'today': today,
        'expiry_warning_date': expiry_warning_date,
        'expiring_document_count': LegalDocument.objects.filter(
            expires_at__isnull=False, expires_at__lte=expiry_warning_date
        ).count(),
        'drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).order_by('full_name'),
        'clients': Client.objects.order_by('full_name'),
        'incident_types': SecurityIncident.TYPE_CHOICES,
        'document_types': LegalDocument.TYPE_CHOICES,
    })


@panel_login_required
def security_incident_create(request):
    if request.method == 'POST':
        SecurityIncident.objects.create(
            title=request.POST.get('title', '').strip(),
            incident_type=request.POST.get('incident_type', SecurityIncident.TYPE_OTHER),
            description=request.POST.get('description', '').strip(),
            related_driver_id=request.POST.get('related_driver') or None,
            related_client_id=request.POST.get('related_client') or None,
            evidence=request.FILES.get('evidence'),
            created_by=request.user,
        )
        messages.success(request, "Voqea ro'yxatga olindi.")
    return redirect('taxi:security_dashboard')


@panel_login_required
def security_incident_update(request, pk):
    incident = get_object_or_404(SecurityIncident, pk=pk)
    if request.method == 'POST':
        from django.utils import timezone
        incident.status = request.POST.get('status', incident.status)
        incident.resolution_note = request.POST.get('resolution_note', '').strip()
        if incident.status == SecurityIncident.STATUS_RESOLVED and not incident.resolved_at:
            incident.resolved_at = timezone.now()
        elif incident.status != SecurityIncident.STATUS_RESOLVED:
            incident.resolved_at = None
        incident.save(update_fields=['status', 'resolution_note', 'resolved_at'])
        messages.success(request, f"Voqea #{incident.id} yangilandi.")
    return redirect(request.META.get('HTTP_REFERER', 'taxi:security_dashboard'))


@panel_login_required
def security_document_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        LegalDocument.objects.create(
            title=request.POST.get('title', '').strip(),
            doc_type=request.POST.get('doc_type', LegalDocument.TYPE_LICENSE),
            number=request.POST.get('number', '').strip(),
            file=request.FILES.get('file'),
            issued_at=request.POST.get('issued_at') or None,
            expires_at=request.POST.get('expires_at') or None,
            notes=request.POST.get('notes', '').strip(),
            uploaded_by=request.user,
        )
        messages.success(request, "Hujjat yuklandi.")
    return redirect('taxi:security_dashboard')


@panel_login_required
def security_document_delete(request, pk):
    document = get_object_or_404(LegalDocument, pk=pk)
    if request.method == 'POST':
        document.delete()
        messages.success(request, "Hujjat o'chirildi.")
    return redirect('taxi:security_dashboard')


# ── Hodimlar (kompaniya xodimlari: profil, vazifalar, smena, davomat) ──────────

@panel_login_required
def employee_list(request):
    from django.utils import timezone
    today = timezone.now().date()

    employees = Employee.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        employees = employees.filter(Q(full_name__icontains=q) | Q(position__icontains=q) | Q(phone__icontains=q))
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)

    today_attendance = {a.employee_id: a for a in EmployeeAttendance.objects.filter(date=today)}
    open_task_counts = {
        row['employee']: row['c'] for row in
        EmployeeTask.objects.exclude(status=EmployeeTask.STATUS_DONE).values('employee').annotate(c=Count('id'))
    }

    employees = list(employees)
    for e in employees:
        e.today_attendance = today_attendance.get(e.pk)
        e.open_task_count = open_task_counts.get(e.pk, 0)

    return render(request, 'taxi/employees.html', {
        'employees': employees,
        'q': q,
        'status_filter': status_filter,
        'total_count': Employee.objects.count(),
        'active_count': Employee.objects.filter(is_active=True).count(),
        'today': today,
    })


@panel_login_required
def employee_create(request):
    from django.utils import timezone
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        position  = request.POST.get('position', '').strip()
        if full_name and position:
            Employee.objects.create(
                full_name=full_name,
                position=position,
                phone=request.POST.get('phone', '').strip(),
                hire_date=request.POST.get('hire_date') or timezone.localdate(),
                photo=request.FILES.get('photo'),
                notes=request.POST.get('notes', '').strip(),
            )
            messages.success(request, "Hodim qo'shildi.")
        else:
            messages.error(request, "F.I.Sh. va lavozimni kiriting.")
    return redirect(request.META.get('HTTP_REFERER') or 'taxi:employee_list')


@panel_login_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.full_name = request.POST.get('full_name', employee.full_name).strip()
        employee.position  = request.POST.get('position', employee.position).strip()
        employee.phone     = request.POST.get('phone', employee.phone).strip()
        hire_date = request.POST.get('hire_date')
        if hire_date:
            employee.hire_date = hire_date
        employee.notes = request.POST.get('notes', employee.notes).strip()
        if request.FILES.get('photo'):
            employee.photo = request.FILES.get('photo')
        employee.save()
        messages.success(request, "Hodim ma'lumotlari yangilandi.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:employee_detail', args=[pk]))


@panel_login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, "Hodim o'chirildi.")
    return redirect('taxi:employee_list')


@panel_login_required
def employee_toggle_active(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.is_active = not employee.is_active
        employee.save(update_fields=['is_active'])
    return redirect(request.META.get('HTTP_REFERER') or 'taxi:employee_list')


@panel_login_required
def employee_detail(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    employee = get_object_or_404(Employee, pk=pk)
    today = timezone.now().date()

    tasks = employee.tasks.all()
    shifts = {s.weekday: s for s in employee.shifts.all()}
    shift_rows = [
        {'weekday': wd, 'label': label, 'shift': shifts.get(wd)}
        for wd, label in EmployeeShift.WEEKDAY_CHOICES
    ]

    return render(request, 'taxi/employee_detail.html', {
        'employee': employee,
        'todo_tasks': tasks.filter(status=EmployeeTask.STATUS_TODO),
        'progress_tasks': tasks.filter(status=EmployeeTask.STATUS_PROGRESS),
        'done_tasks': tasks.filter(status=EmployeeTask.STATUS_DONE),
        'shift_rows': shift_rows,
        'attendance_records': employee.attendance_records.filter(date__gte=today - timedelta(days=30)),
        'today_attendance': employee.attendance_records.filter(date=today).first(),
        'today': today,
    })


@panel_login_required
def employee_task_create(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            EmployeeTask.objects.create(
                employee=employee,
                title=title,
                description=request.POST.get('description', '').strip(),
                due_date=request.POST.get('due_date') or None,
                assigned_by=request.user,
            )
            messages.success(request, "Vazifa qo'shildi.")
    return redirect('taxi:employee_detail', pk=pk)


@panel_login_required
def employee_task_set_status(request, task_id):
    from django.utils import timezone
    task = get_object_or_404(EmployeeTask, pk=task_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(EmployeeTask.STATUS_CHOICES):
            task.status = status
            task.completed_at = timezone.now() if status == EmployeeTask.STATUS_DONE else None
            task.save(update_fields=['status', 'completed_at'])
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:employee_detail', args=[task.employee_id]))


@panel_login_required
def employee_task_delete(request, task_id):
    task = get_object_or_404(EmployeeTask, pk=task_id)
    employee_pk = task.employee_id
    if request.method == 'POST':
        task.delete()
        messages.success(request, "Vazifa o'chirildi.")
    return redirect('taxi:employee_detail', pk=employee_pk)


@panel_login_required
def employee_shift_save(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        for weekday, _label in EmployeeShift.WEEKDAY_CHOICES:
            start = request.POST.get(f'start_{weekday}', '').strip()
            end   = request.POST.get(f'end_{weekday}', '').strip()
            if start and end:
                EmployeeShift.objects.update_or_create(
                    employee=employee, weekday=weekday,
                    defaults={'start_time': start, 'end_time': end},
                )
            else:
                EmployeeShift.objects.filter(employee=employee, weekday=weekday).delete()
        messages.success(request, "Smena jadvali saqlandi.")
    return redirect('taxi:employee_detail', pk=pk)


@panel_login_required
def employee_attendance_checkin(request, pk):
    from django.utils import timezone
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        record, _ = EmployeeAttendance.objects.get_or_create(employee=employee, date=timezone.now().date())
        record.check_in = timezone.now()
        record.status = EmployeeAttendance.STATUS_PRESENT
        record.save(update_fields=['check_in', 'status'])
        messages.success(request, f"{employee.full_name} — kelishi belgilandi.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:employee_detail', args=[pk]))


@panel_login_required
def employee_attendance_checkout(request, pk):
    from django.utils import timezone
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        record, _ = EmployeeAttendance.objects.get_or_create(employee=employee, date=timezone.now().date())
        record.check_out = timezone.now()
        record.save(update_fields=['check_out'])
        messages.success(request, f"{employee.full_name} — ketishi belgilandi.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:employee_detail', args=[pk]))


@panel_login_required
def employee_attendance_manual(request, pk):
    from datetime import datetime as _dt
    from django.utils import timezone
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        date = request.POST.get('date')
        if date:
            def _combine(time_str):
                if not time_str:
                    return None
                naive = _dt.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                return timezone.make_aware(naive) if timezone.is_naive(naive) else naive

            record, _ = EmployeeAttendance.objects.get_or_create(employee=employee, date=date)
            record.check_in  = _combine(request.POST.get('check_in', ''))
            record.check_out = _combine(request.POST.get('check_out', ''))
            record.status    = request.POST.get('status', record.status)
            record.note      = request.POST.get('note', '').strip()
            record.save()
            messages.success(request, "Davomat yozuvi saqlandi.")
    return redirect('taxi:employee_detail', pk=pk)


# ── Tezkor manzillar (xaritadan tanlab saqlanadigan, nomli manzillar) ───────────

@panel_login_required
def saved_addresses_list(request):
    from django.utils import timezone
    # Faqat online (last_seen yangi) haydovchilar navbatda "ko'rsatiladi" —
    # eski (masalan bir soat oldin GPS yuborgan) haydovchi navbatda hali ham
    # turgandek chiqmasin. Dispatch tomonida (_next_address_queue_driver,
    # utils.py) alohida, tigroq staleness mantig'i bor — u yerga tegilmadi.
    online_cutoff = timezone.now() - timezone.timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    addresses = SavedAddress.objects.annotate(
        queue_count=Count(
            'queue_entries',
            filter=Q(
                queue_entries__left_at__isnull=True,
                queue_entries__driver__is_active=True,
                queue_entries__driver__is_on_duty=True,
                queue_entries__driver__approval_status='approved',
                queue_entries__driver__last_seen__gte=online_cutoff,
            ),
        )
    )
    return render(request, 'taxi/saved_addresses.html', {
        'addresses': addresses,
    })


@panel_login_required
def saved_address_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        if name and lat and lng:
            SavedAddress.objects.create(
                name=name, address=address, lat=float(lat), lng=float(lng),
                created_by=request.user,
            )
            messages.success(request, f"«{name}» manzil sifatida saqlandi.")
        else:
            messages.error(request, "Nomi va xaritadan nuqta tanlanishi shart.")
    return redirect('taxi:saved_addresses_list')


@panel_login_required
def saved_address_update(request, pk):
    address = get_object_or_404(SavedAddress, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        addr_text = request.POST.get('address', '').strip()
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        if name and lat and lng:
            address.name = name
            address.address = addr_text
            address.lat = float(lat)
            address.lng = float(lng)
            address.save(update_fields=['name', 'address', 'lat', 'lng'])
            messages.success(request, f"«{name}» manzili yangilandi.")
        else:
            messages.error(request, "Nomi va xaritadan nuqta tanlanishi shart.")
    return redirect('taxi:saved_addresses_list')


@panel_login_required
def saved_address_delete(request, pk):
    address = get_object_or_404(SavedAddress, pk=pk)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Manzil o'chirildi.")
    return redirect('taxi:saved_addresses_list')


@panel_login_required
def saved_address_queue_drivers(request, pk):
    """Manzillar ro'yxatida qator ochilganda (strelka) shu manzil navbatidagi
    haydovchilarni tartib bilan qaytaradi — saved_addresses_list'dagi
    queue_count bilan bir xil filtrlash mantig'i (offline/off-duty va
    online bo'lmagan — last_seen eski — haydovchilar chiqarib tashlanadi)."""
    from django.utils import timezone
    from .models import AddressQueueEntry

    address = get_object_or_404(SavedAddress, pk=pk)
    online_cutoff = timezone.now() - timezone.timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    entries = (
        AddressQueueEntry.objects.filter(
            address=address, left_at__isnull=True,
            driver__is_active=True, driver__is_on_duty=True,
            driver__approval_status='approved',
            driver__last_seen__gte=online_cutoff,
        )
        .select_related('driver')
        .order_by('joined_at')
    )
    drivers = [
        {
            'position': i + 1,
            'full_name': e.driver.full_name,
            'phone_number': e.driver.phone_number,
            'car_model': e.driver.car_model,
            'car_number': e.driver.car_number,
            'joined_at': timezone.localtime(e.joined_at).strftime('%H:%M'),
        }
        for i, e in enumerate(entries)
    ]
    return JsonResponse({'ok': True, 'drivers': drivers})


@panel_login_required
@require_POST
def saved_address_use(request, pk):
    """Yangi buyurtma oynasida tezkor manzil bosilganda chaqiriladi —
    eng ko'p ishlatilganlar ro'yxat boshida chiqishi uchun hisoblagich."""
    SavedAddress.objects.filter(pk=pk).update(usage_count=F('usage_count') + 1)
    return JsonResponse({'ok': True})


# ── Guruh jonli ovozli aloqa ("efir") — operator paneli tomoni, ratsiya uslubi ─
# Haydovchilar bir-biri bilan gaplashadigan "efir"ning aynan o'zi — operator
# ham xuddi shu xonaga (VoiceParticipant/VoiceSignal) ulanadi, shu bilan
# haydovchilarning xabarini eshitishi va o'zi ham hammaga bosib-gapirib
# yuborishi mumkin bo'ladi. Umumiy mantiq taxi/utils.py dagi voice_*
# funksiyalarda — batafsili uchun taxi/driver_views.py dagi driver_voice_*
# (haydovchi tomoni) ga qarang.

@panel_login_required
@require_POST
def panel_voice_join(request):
    voice_prune_stale()
    VoiceParticipant.objects.update_or_create(operator=request.user)
    return JsonResponse({'ok': True, 'participants': voice_participants_list(f'o{request.user.id}')})


@panel_login_required
@require_POST
def panel_voice_leave(request):
    VoiceParticipant.objects.filter(operator=request.user).delete()
    return JsonResponse({'ok': True})


@panel_login_required
def panel_voice_heartbeat(request):
    try:
        VoiceParticipant.objects.get(operator=request.user).save(update_fields=['last_seen'])
    except VoiceParticipant.DoesNotExist:
        return JsonResponse({'ok': True, 'joined': False})
    voice_prune_stale()

    signals = list(VoiceSignal.objects.filter(to_operator=request.user).select_related('from_driver', 'from_operator').order_by('created_at')[:10])
    signal_ids = [s.id for s in signals]
    if signal_ids:
        VoiceSignal.objects.filter(id__in=signal_ids).delete()

    return JsonResponse({
        'ok': True,
        'joined': True,
        'participants': voice_participants_list(f'o{request.user.id}'),
        'clips': [
            dict(zip(('from', 'from_name'), voice_signal_sender_info(s)),
                 audio_url=request.build_absolute_uri(s.audio.url))
            for s in signals
        ],
    })


@panel_login_required
@require_POST
def panel_voice_send_audio(request):
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'ok': False, 'error': "Audio fayl kerak"}, status=400)
    voice_prune_stale()
    delivered = voice_broadcast_audio({'from_operator': request.user}, f'o{request.user.id}', audio)
    return JsonResponse({'ok': True, 'delivered': delivered})


# ── Haydovchi shartnomasi ──────────────────────────────────────────────────────

@system_login_required
def contract_settings(request):
    contract = ContractSettings.get()
    saved = False
    if request.method == 'POST':
        contract.title   = request.POST.get('title', contract.title).strip()
        contract.content = request.POST.get('content', contract.content).strip()
        contract.save()
        saved = True

    total_approved = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count()
    signed_current = DriverContractSignature.objects.filter(version=contract.version).values('driver').distinct().count()

    return render(request, 'taxi/contract_settings.html', {
        'contract': contract,
        'saved': saved,
        'total_approved': total_approved,
        'signed_current': signed_current,
    })


@system_login_required
def contract_download_blank(request):
    from django.utils.text import slugify
    contract = ContractSettings.get()
    buf = build_contract_pdf(contract)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="shartnoma_namunasi_v{contract.version}.pdf"'
    return response


@panel_login_required
def driver_contract_download(request, pk):
    from django.utils.text import slugify
    driver = get_object_or_404(Driver, pk=pk)
    contract = ContractSettings.get()
    signature = driver.contract_signatures.filter(version=contract.version).first()
    if not signature:
        messages.error(request, "Bu haydovchi hali joriy shartnomani imzolamagan.")
        return redirect('taxi:driver_detail', pk=pk)

    buf = build_contract_pdf(contract, driver=driver, signature=signature)
    filename = f"shartnoma_{slugify(driver.full_name) or driver.pk}.pdf"
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── Reklama flayeri ────────────────────────────────────────────────────────────

@system_login_required
def flyer_page(request):
    from django.utils import timezone
    from datetime import timedelta

    checked_voucher = None
    check_error = None

    if request.method == 'POST' and 'check_code' in request.POST:
        code = request.POST.get('code', '').strip().upper()
        checked_voucher = FlyerVoucher.objects.filter(code=code).select_related('used_by_driver', 'owner_driver').first()
        if not checked_voucher:
            check_error = "Bunday kod topilmadi — bu flayer soxta bo'lishi mumkin."

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    driver_stats = list(
        Driver.objects.filter(owned_vouchers__isnull=False)
        .annotate(
            issued_count=Count('owned_vouchers', distinct=True),
            used_count=Count('owned_vouchers', filter=Q(owned_vouchers__is_used=True), distinct=True),
            week_count=Count('owned_vouchers', filter=Q(owned_vouchers__is_used=True, owned_vouchers__used_at__date__gte=week_start), distinct=True),
        )
        .filter(issued_count__gt=0)
        .order_by('-week_count', '-used_count', 'full_name')
    )

    week_leader = driver_stats[0] if driver_stats and driver_stats[0].week_count > 0 else None
    week_leader_rewarded = False
    if week_leader:
        week_leader_rewarded = VizitkaRewardLog.objects.filter(driver=week_leader, week_start=week_start).exists()

    return render(request, 'taxi/flyer.html', {
        'total_vouchers': FlyerVoucher.objects.count(),
        'used_vouchers':  FlyerVoucher.objects.filter(is_used=True).count(),
        'checked_voucher': checked_voucher,
        'check_error': check_error,
        'drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).order_by('full_name'),
        'driver_stats': driver_stats,
        'week_start': week_start,
        'week_leader': week_leader,
        'week_leader_rewarded': week_leader_rewarded,
    })


def landing_page(request):
    """Bosh sahifa (vijdontaxi.uz) — OMMAVIY (login talab qilmaydigan) landing
    sahifa. Mijoz yoki haydovchi sifatida tizimga kirish/ro'yxatdan o'tish
    havolalarini beradi. Boshqaruv paneli endi shu yerdan avtomatik ochilmaydi —
    operatorlar to'g'ridan-to'g'ri /panel/ manzilidan kirishadi."""
    tariff = TariffSettings.get()

    def _uzs(value):
        return f'{int(value):,}'.replace(',', ' ')

    return render(request, 'taxi/landing.html', {
        'base_price': _uzs(tariff.base_price),
        'price_per_km': _uzs(tariff.price_per_km),
        'operator_phone': tariff.operator_phone,
    })


def flyer_verify(request, code):
    """Flayerdagi QR kod skanerlanganda ochiladigan OMMAVIY (login talab
    qilmaydigan) sahifa — mijoz telefon kamerasi bilan darhol flayer asl
    (original) yoki soxta ekanini, hamda kimning vizitkasi ekanini ko'radi."""
    voucher = FlyerVoucher.objects.select_related('used_by_driver', 'owner_driver').filter(code=code.strip().upper()).first()
    return render(request, 'taxi/flyer_verify.html', {'voucher': voucher, 'code': code.strip().upper()})


@system_login_required
@require_POST
def flyer_download(request):
    fmt = request.POST.get('format', 'flyer')
    per_sheet = 10 if fmt == 'card' else 3

    try:
        quantity = int(request.POST.get('quantity', 30))
    except (TypeError, ValueError):
        quantity = 30
    quantity = max(per_sheet, min(quantity, 300))
    quantity = ((quantity + per_sheet - 1) // per_sheet) * per_sheet  # to'liq varaqqa to'lishi kerak

    owner_id = request.POST.get('owner_driver_id', '').strip()
    owner_driver = get_object_or_404(Driver, pk=owner_id) if owner_id else None

    existing_codes = set(FlyerVoucher.objects.values_list('code', flat=True))
    codes = generate_voucher_codes(quantity, existing=existing_codes)
    FlyerVoucher.objects.bulk_create([FlyerVoucher(code=code, owner_driver=owner_driver) for code in codes])

    if fmt == 'card':
        buf = build_flyer_business_card_pdf(codes, owner_driver=owner_driver)
        filename = 'vijdon_taxi_vizitka.pdf'
    else:
        buf = build_flyer_pdf(codes, owner_driver=owner_driver)
        filename = 'vijdon_taxi_flayer.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@system_login_required
@require_POST
def flyer_redeem(request):
    from django.utils import timezone
    code = request.POST.get('code', '').strip().upper()
    driver_id = request.POST.get('driver_id', '').strip()
    voucher = get_object_or_404(FlyerVoucher, code=code)

    if voucher.is_used:
        messages.error(request, "Bu kod allaqachon ishlatilgan.")
        return redirect('system:flyer_page')

    # Vizitka chiqarilganda egasi biriktirilgan bo'lsa, haydovchini qo'lda
    # tanlash shart emas — vizitka egasi avtomatik hisoblanadi.
    if voucher.owner_driver_id:
        driver = voucher.owner_driver
    else:
        if not driver_id:
            messages.error(request, "Haydovchini tanlang.")
            return redirect('system:flyer_page')
        driver = get_object_or_404(Driver, pk=driver_id)
    amount = voucher.amount

    voucher.is_used = True
    voucher.used_at = timezone.now()
    voucher.used_by_driver = driver
    voucher.verified_by = request.user
    voucher.save(update_fields=['is_used', 'used_at', 'used_by_driver', 'verified_by'])

    driver.balance += amount
    driver.save(update_fields=['balance'])
    BalanceLog.objects.create(
        driver=driver, action='add', amount=amount,
        balance_after=driver.balance, note=f"Flayer kuponi: {voucher.code}"
    )
    DriverActivityLog.objects.create(
        driver=driver, action=DriverActivityLog.ACTION_BALANCE,
        detail=f"+{amount} UZS (flayer kuponi {voucher.code})",
        ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    tg_balance_changed(driver, amount, 'add')
    tg_flyer_voucher_redeemed(voucher, driver)
    messages.success(request, f"Kod tasdiqlandi — {driver.full_name} balansiga {amount} so'm qo'shildi.")
    return redirect('system:flyer_page')


@system_login_required
@require_POST
def flyer_reward_bonus(request):
    """Haftalik 'Mijoz olib kel' vizitka reytingida eng ko'p vizitka
    tarqatgan (va ishlatilgan) haydovchiga bonus balans qo'shadi. Bitta
    haydovchiga bitta hafta uchun faqat bir marta beriladi
    (VizitkaRewardLog.UniqueConstraint shuni kafolatlaydi)."""
    from datetime import date as date_cls

    driver_id  = request.POST.get('driver_id', '').strip()
    week_start_str = request.POST.get('week_start', '').strip()
    try:
        amount = int(request.POST.get('amount', 100000))
    except (TypeError, ValueError):
        amount = 100000

    driver = get_object_or_404(Driver, pk=driver_id)
    try:
        week_start = date_cls.fromisoformat(week_start_str)
    except ValueError:
        messages.error(request, "Noto'g'ri hafta sanasi.")
        return redirect('system:flyer_page')

    voucher_count = FlyerVoucher.objects.filter(
        owner_driver=driver, is_used=True, used_at__date__gte=week_start,
    ).count()

    reward, created = VizitkaRewardLog.objects.get_or_create(
        driver=driver, week_start=week_start,
        defaults={'voucher_count': voucher_count, 'amount': amount, 'given_by': request.user},
    )
    if not created:
        messages.error(request, f"{driver.full_name}ga shu hafta uchun bonus allaqachon berilgan.")
        return redirect('system:flyer_page')

    driver.balance += reward.amount
    driver.save(update_fields=['balance'])
    BalanceLog.objects.create(
        driver=driver, action='add', amount=reward.amount,
        balance_after=driver.balance, note=f"Vizitka reytingi bonusi ({week_start:%d.%m.%Y} haftasi)"
    )
    DriverActivityLog.objects.create(
        driver=driver, action=DriverActivityLog.ACTION_BALANCE,
        detail=f"+{reward.amount} UZS (vizitka reytingi bonusi)",
        ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    tg_balance_changed(driver, reward.amount, 'add')
    messages.success(request, f"{driver.full_name}ga {reward.amount} so'm vizitka bonusi berildi.")
    return redirect('system:flyer_page')


# ── Vazifalar (Task board) ────────────────────────────────────────────────────

@system_login_required
def task_list(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            Task.objects.create(title=title, created_by=request.user)
        return redirect('system:task_list')

    tasks = Task.objects.select_related('created_by').all()
    return render(request, 'taxi/tasks.html', {
        'todo_tasks':  tasks.filter(status=Task.STATUS_TODO),
        'doing_tasks': tasks.filter(status=Task.STATUS_DOING),
        'done_tasks':  tasks.filter(status=Task.STATUS_DONE),
    })


@system_login_required
@require_POST
def task_set_status(request, pk):
    from django.utils import timezone
    task = get_object_or_404(Task, pk=pk)
    status = request.POST.get('status', '')
    if status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'ok': False, 'error': "Noto'g'ri holat"}, status=400)
    task.status = status
    task.completed_at = timezone.now() if status == Task.STATUS_DONE else None
    task.save(update_fields=['status', 'completed_at', 'updated_at'])
    return JsonResponse({'ok': True})


@system_login_required
@require_POST
def task_delete(request, pk):
    Task.objects.filter(pk=pk).delete()
    return JsonResponse({'ok': True})
