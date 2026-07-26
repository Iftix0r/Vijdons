# Vijdon Taxi

Taksi xizmatini boshqarish uchun Django asosidagi backend: operator boshqaruv paneli, haydovchi va mijoz veb-ilovalari, Telegram bot integratsiyasi hamda ikkita Flutter (WebView) mobil ilova.

## Tarkib

- **`taxi/`** — asosiy Django ilovasi (modellar, operator paneli, haydovchi/mijoz veb-ilovalari, REST API, Telegram bot, PDF/hisobot generatsiyasi)
- **`config/`** — Django loyihasi sozlamalari (`settings.py`, `urls.py`)
- **`vijdon_driver_app/`** — haydovchilar uchun Flutter ilovasi (`/driver/` veb-ilovasini o'rab turuvchi WebView + fon rejimida GPS/bildirishnoma)
- **`vijdon_client_app/`** — mijozlar uchun Flutter ilovasi (xuddi shunday, `/client/` uchun)

Loyiha arxitekturasi, har bir bo'limning ishlash tartibi va muhim texnik nuanslar haqida batafsil — **[CLAUDE.md](CLAUDE.md)** faylida.

## O'rnatish va ishga tushirish

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# config/settings.py da DATABASES (PostgreSQL) ma'lumotlarini moslang
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

Operator paneli: `http://localhost:8000/panel/`
Haydovchi ilovasi: `http://localhost:8000/driver/`
Mijoz ilovasi: `http://localhost:8000/client/`

## Texnologiyalar

Django · Django REST Framework · PostgreSQL · Chart.js · Tailwind CSS · Telegram Bot API · Web Push (VAPID) · ReportLab (PDF) · Flutter (WebView)
