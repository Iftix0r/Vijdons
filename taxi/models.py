from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Driver(models.Model):
    APPROVAL_PENDING  = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_CHOICES = (
        (APPROVAL_PENDING,  'Kutilmoqda'),
        (APPROVAL_APPROVED, 'Tasdiqlangan'),
        (APPROVAL_REJECTED, 'Rad etilgan'),
    )

    user            = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='driver_profile')
    full_name       = models.CharField(max_length=255, verbose_name="Haydovchi ismi")
    phone_number    = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    car_model       = models.CharField(max_length=100, verbose_name="Mashina modeli")
    car_number      = models.CharField(max_length=20, verbose_name="Mashina raqami")
    is_active       = models.BooleanField(default=True, verbose_name="Faol")
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_PENDING, verbose_name="Tasdiqlash holati")
    fcm_token       = models.TextField(blank=True, null=True, verbose_name="FCM Token")
    is_on_duty      = models.BooleanField(default=False, verbose_name="Ish navbatida")
    latitude        = models.FloatField(null=True, blank=True, verbose_name="Kenglik (Latitude)")
    longitude       = models.FloatField(null=True, blank=True, verbose_name="Uzunlik (Longitude)")
    balance         = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Balans")
    registered_at   = models.DateTimeField(auto_now_add=True, verbose_name="Ro'yxatdan o'tgan vaqt")

    def __str__(self):
        return f"{self.full_name} ({self.car_number})"

    class Meta:
        verbose_name = "Haydovchi"
        verbose_name_plural = "Haydovchilar"


class Client(models.Model):
    full_name    = models.CharField(max_length=255, verbose_name="Mijoz ismi", null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")

    def __str__(self):
        return self.full_name or self.phone_number

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending',   'Kutilmoqda'),
        ('accepted',  'Qabul qilindi'),
        ('on_way',    "Yo'lda"),
        ('arrived',   'Yetib keldim'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    )

    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_CHOICES = (
        (PAYMENT_CASH, 'Naqd'),
        (PAYMENT_CARD, 'Karta'),
    )

    client       = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders', verbose_name="Mijoz")
    driver       = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Haydovchi")
    from_address = models.CharField(max_length=255, verbose_name="Mijoz manzili")
    from_lat     = models.FloatField(null=True, blank=True, verbose_name="Manzil Kenglik (Lat)")
    from_lng     = models.FloatField(null=True, blank=True, verbose_name="Manzil Uzunlik (Lng)")
    to_address   = models.CharField(max_length=255, blank=True, default='', verbose_name="Qayerga (ixtiyoriy)")
    to_lat       = models.FloatField(null=True, blank=True, verbose_name="Qayerga Kenglik (Lat)")
    to_lng       = models.FloatField(null=True, blank=True, verbose_name="Qayerga Uzunlik (Lng)")
    distance_km  = models.FloatField(null=True, blank=True, verbose_name="Masofa (km)")
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Narxi")
    commission   = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Komissiya")
    payment_type  = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH, verbose_name="To'lov turi")
    note          = models.TextField(blank=True, default='', verbose_name="Izoh")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    dispatched_to = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatched_orders', verbose_name="Yuborilgan haydovchi")
    dispatched_at = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqti")
    rejected_by   = models.ManyToManyField(Driver, blank=True, related_name='rejected_orders', verbose_name="Rad etgan haydovchilar")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at    = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.client}"

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"


class ChatMessage(models.Model):
    SENDER_DRIVER   = 'driver'
    SENDER_OPERATOR = 'operator'
    SENDER_CHOICES  = (
        (SENDER_DRIVER,   'Haydovchi'),
        (SENDER_OPERATOR, 'Operator'),
    )

    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='messages', verbose_name='Haydovchi')
    sender     = models.CharField(max_length=10, choices=SENDER_CHOICES, verbose_name='Kimdan')
    text       = models.TextField(verbose_name='Xabar')
    is_read    = models.BooleanField(default=False, verbose_name="O'qildi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')

    def __str__(self):
        return f"{self.sender} → {self.driver.full_name}: {self.text[:40]}"

    class Meta:
        verbose_name = 'Chat xabari'
        verbose_name_plural = 'Chat xabarlari'
        ordering = ['created_at']


class MapsSettings(models.Model):
    """Singleton: admin paneldan geocoding API sozlamalari."""
    PROVIDER_NOMINATIM = 'nominatim'
    PROVIDER_YANDEX    = 'yandex'
    PROVIDER_GEOAPIFY  = 'geoapify'
    PROVIDER_GOOGLE    = 'google'
    PROVIDER_CHOICES = (
        (PROVIDER_NOMINATIM, 'OpenStreetMap (Nominatim) — Bepul'),
        (PROVIDER_YANDEX,    'Yandex Geocoder'),
        (PROVIDER_GEOAPIFY,  'Geoapify'),
        (PROVIDER_GOOGLE,    'Google Maps'),
    )

    provider          = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_NOMINATIM, verbose_name='Geocoding API')
    api_key           = models.CharField(max_length=255, blank=True, default='', verbose_name='Geocoding API kalit', help_text='Nominatim uchun shart emas')
    yandex_mapkit_key = models.CharField(max_length=255, blank=True, default='', verbose_name='Yandex MapKit API kalit', help_text='Mobil ilova xaritasi uchun (haydovchi va mijoz ilovasi)')
    is_active  = models.BooleanField(default=True, verbose_name='Faol')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Maps: {self.get_provider_display()}'

    class Meta:
        verbose_name = 'Maps sozlamalari'
        verbose_name_plural = 'Maps sozlamalari'


class DriverActivityLog(models.Model):
    ACTION_LOGIN    = 'login'
    ACTION_LOGOUT   = 'logout'
    ACTION_BLOCK    = 'block'
    ACTION_UNBLOCK  = 'unblock'
    ACTION_BALANCE  = 'balance'
    ACTION_DUTY_ON  = 'duty_on'
    ACTION_DUTY_OFF = 'duty_off'
    ACTION_ORDER    = 'order'
    ACTION_CHOICES  = (
        (ACTION_LOGIN,    'Kirish'),
        (ACTION_LOGOUT,   'Chiqish'),
        (ACTION_BLOCK,    'Bloklandi'),
        (ACTION_UNBLOCK,  'Blok ochildi'),
        (ACTION_BALANCE,  'Balans o\'zgardi'),
        (ACTION_DUTY_ON,  'Navbatga kirdi'),
        (ACTION_DUTY_OFF, 'Navbatdan chiqdi'),
        (ACTION_ORDER,    'Buyurtma'),
    )

    driver     = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='activity_logs', verbose_name='Haydovchi')
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Amal')
    detail     = models.CharField(max_length=500, blank=True, default='', verbose_name='Tafsilot')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP manzil')
    user_agent = models.TextField(blank=True, default='', verbose_name='Qurilma / Brauzer')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')

    def __str__(self):
        return f"{self.driver.full_name} — {self.get_action_display()} ({self.created_at:%d.%m.%Y %H:%M})"

    class Meta:
        verbose_name = 'Faollik logi'
        verbose_name_plural = 'Faollik loglari'
        ordering = ['-created_at']



class TariffSettings(models.Model):
    """Singleton: admin paneldan narx sozlamalari."""
    base_price    = models.DecimalField(max_digits=10, decimal_places=2, default=5000, verbose_name="Boshlang'ich narx (UZS)", help_text="Har bir buyurtma uchun minimal narx")
    price_per_km  = models.DecimalField(max_digits=10, decimal_places=2, default=2000, verbose_name="1 km narxi (UZS)")
    commission    = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Haydovchi komissiyasi (UZS)", help_text="Har bir qabul qilingan buyurtma uchun haydovchi balansidan yechiladi")
    auto_dispatch = models.BooleanField(default=True, verbose_name="Avtomatik taqsimlash", help_text="Yoqilgan bo'lsa eng yaqin haydovchiga avtomatik beriladi")
    max_dispatch_attempts = models.IntegerField(default=4, verbose_name="Maksimal urinishlar soni", help_text="Buyurtma eng ko'pi bilan nechta haydovchiga navbatma-navbat ko'rsatiladi")
    dispatch_timeout      = models.IntegerField(default=10, verbose_name="Kutish vaqti (sekund)", help_text="Har bir haydovchi qabul qilishi uchun beriladigan vaqt")
    updated_at    = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def calc_price(self, distance_km):
        if distance_km is None:
            return None
        return self.base_price + Decimal(str(distance_km)) * self.price_per_km

    def __str__(self):
        return f"Tariff: {self.base_price} + {self.price_per_km}/km, komissiya={self.commission}"

    class Meta:
        verbose_name = "Tariff sozlamalari"
        verbose_name_plural = "Tariff sozlamalari"
