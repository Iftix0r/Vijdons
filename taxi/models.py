from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from .constants import PANEL_SOUND_EVENTS, DRIVER_SOUND_EVENTS, DEFAULT_SOUND_URLS


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
    balance               = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Balans")
    rating                = models.DecimalField(max_digits=3, decimal_places=2, default=5.00, verbose_name="Reyting (1–5)")
    trips_count           = models.PositiveIntegerField(default=0, verbose_name="Jami safarlar soni")
    rating_count          = models.PositiveIntegerField(default=0, verbose_name="Reytinglar soni")
    push_subscription     = models.TextField(blank=True, null=True, verbose_name="Web Push Subscription")
    registered_at         = models.DateTimeField(auto_now_add=True, verbose_name="Ro'yxatdan o'tgan vaqt")
    destination_mode      = models.BooleanField(default=False, verbose_name="Destination mode (uyga yo'nalish)")
    destination_lat       = models.FloatField(null=True, blank=True, verbose_name="Yo'nalish kenglik")
    destination_lng       = models.FloatField(null=True, blank=True, verbose_name="Yo'nalish uzunlik")
    destination_address   = models.CharField(max_length=255, blank=True, default='', verbose_name="Yo'nalish manzil")
    photo                 = models.ImageField(upload_to='driver_photos/', blank=True, null=True, verbose_name="Profil rasmi")
    last_seen             = models.DateTimeField(null=True, blank=True, verbose_name="So'nggi faollik")
    last_address          = models.CharField(max_length=500, blank=True, default='', verbose_name="So'nggi manzil")

    def __str__(self):
        return f"{self.full_name} ({self.car_number})"

    class Meta:
        verbose_name = "Haydovchi"
        verbose_name_plural = "Haydovchilar"


class Client(models.Model):
    full_name    = models.CharField(max_length=255, verbose_name="Mijoz ismi", null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    is_blocked   = models.BooleanField(default=False, verbose_name="Bloklangan")
    rating       = models.DecimalField(max_digits=3, decimal_places=2, default=5.00,
                                       verbose_name="Reyting (1–5)")
    trips_count  = models.PositiveIntegerField(default=0, verbose_name="Jami safarlar soni")

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
    distance_km    = models.FloatField(null=True, blank=True, verbose_name="Masofa (km)")
    tmx_dist_km    = models.FloatField(default=0, verbose_name="Taximetr masofa (km)")
    tmx_paused     = models.BooleanField(default=False, verbose_name="Taximetr pauza")
    tmx_paused_ms  = models.BigIntegerField(default=0, verbose_name="Taximetr pauza (ms)")
    tmx_start_time = models.DateTimeField(null=True, blank=True, verbose_name="Taximetr boshlangan vaqt")
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Narxi")
    commission   = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Komissiya")
    payment_type  = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH, verbose_name="To'lov turi")
    note          = models.TextField(blank=True, default='', verbose_name="Izoh")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    dispatched_to = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatched_orders', verbose_name="Yuborilgan haydovchi")
    dispatched_at = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqti")
    rejected_by   = models.ManyToManyField(Driver, blank=True, related_name='rejected_orders', verbose_name="Rad etgan haydovchilar")
    client_rating = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Mijoz reytingi (1-5)")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at    = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.client}"

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        indexes = [
            # Haydovchi ilovasi buyurtmalar ro'yxatini har 3-5 soniyada shu
            # kombinatsiyalar bo'yicha so'raydi (poll) — indekssiz jadval kattalashgani
            # sari sekinlashib boradi.
            models.Index(fields=['status', 'driver']),
            models.Index(fields=['status', 'dispatched_to']),
        ]


class ChatMessage(models.Model):
    SENDER_DRIVER   = 'driver'
    SENDER_OPERATOR = 'operator'
    SENDER_CHOICES  = (
        (SENDER_DRIVER,   'Haydovchi'),
        (SENDER_OPERATOR, 'Operator'),
    )

    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='messages', verbose_name='Haydovchi')
    sender     = models.CharField(max_length=10, choices=SENDER_CHOICES, verbose_name='Kimdan')
    text       = models.TextField(blank=True, default='', verbose_name='Xabar')
    audio      = models.FileField(upload_to='chat_audio/', blank=True, null=True, verbose_name='Audio xabar')
    is_read    = models.BooleanField(default=False, verbose_name="O'qildi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')

    def __str__(self):
        return f"{self.sender} → {self.driver.full_name}: {self.text[:40]}"

    class Meta:
        verbose_name = 'Chat xabari'
        verbose_name_plural = 'Chat xabarlari'
        ordering = ['created_at']


class BotSettings(models.Model):
    """Singleton: Telegram bot sozlamalari."""
    bot_token  = models.CharField(max_length=200, blank=True, default='', verbose_name='Bot Token',
                                  help_text='@BotFather dan olingan token')
    group_id   = models.CharField(max_length=50, blank=True, default='', verbose_name='Asosiy Guruh Chat ID',
                                  help_text='Birinchi operatorlar guruhi chat_id')
    extra_group_ids = models.TextField(blank=True, default='', verbose_name='Qo\'shimcha guruh IDlar',
                                       help_text='Har bir ID yangi qatorda. Bot qo\'shilgan barcha guruhlarga yuboradi.')
    client_bot_token = models.CharField(max_length=200, blank=True, default='', verbose_name='Mijoz Bot Token',
                                        help_text='Mijozlar buyurtma beruvchi bot tokeni')

    def get_all_group_ids(self):
        """Barcha guruh IDlarini list sifatida qaytaradi."""
        ids = []
        if self.group_id.strip():
            ids.append(self.group_id.strip())
        for line in self.extra_group_ids.splitlines():
            gid = line.strip()
            if gid and gid not in ids:
                ids.append(gid)
        return ids

    # Bildirishnoma toggle lar
    notify_new_order      = models.BooleanField(default=True,  verbose_name='Yangi buyurtma')
    notify_dispatched     = models.BooleanField(default=True,  verbose_name='Buyurtma yuborildi')
    notify_accepted       = models.BooleanField(default=True,  verbose_name='Buyurtma qabul qilindi')
    notify_on_way         = models.BooleanField(default=True,  verbose_name="Haydovchi yo'lda")
    notify_arrived        = models.BooleanField(default=True,  verbose_name='Haydovchi yetib keldi')
    notify_completed      = models.BooleanField(default=True,  verbose_name='Buyurtma yakunlandi')
    notify_cancelled      = models.BooleanField(default=True,  verbose_name='Buyurtma bekor qilindi')
    notify_rejected       = models.BooleanField(default=False, verbose_name='Buyurtma rad etildi')
    notify_driver_register= models.BooleanField(default=True,  verbose_name="Yangi haydovchi ro'yxatdan o'tdi")
    notify_driver_approved= models.BooleanField(default=True,  verbose_name='Haydovchi tasdiqlandi')
    notify_driver_rejected= models.BooleanField(default=True,  verbose_name='Haydovchi rad etildi')
    notify_driver_blocked = models.BooleanField(default=True,  verbose_name='Haydovchi bloklandi/ochildi')
    notify_driver_login   = models.BooleanField(default=False, verbose_name='Haydovchi kirdi (login)')
    notify_duty_changed   = models.BooleanField(default=False, verbose_name='Navbat holati o\'zgardi')
    notify_balance_changed= models.BooleanField(default=True,  verbose_name='Balans o\'zgardi')

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Telegram Bot Sozlamalari'

    class Meta:
        verbose_name = 'Bot sozlamalari'
        verbose_name_plural = 'Bot sozlamalari'


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


class SosAlert(models.Model):
    STATUS_NEW      = 'new'
    STATUS_VIEWED   = 'viewed'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES  = (
        (STATUS_NEW,      'Yangi'),
        (STATUS_VIEWED,   "Ko'rildi"),
        (STATUS_RESOLVED, 'Hal qilindi'),
    )

    driver     = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='sos_alerts', verbose_name='Haydovchi')
    latitude   = models.FloatField(null=True, blank=True, verbose_name='Kenglik')
    longitude  = models.FloatField(null=True, blank=True, verbose_name='Uzunlik')
    address    = models.CharField(max_length=500, blank=True, default='', verbose_name='Manzil')
    note       = models.TextField(blank=True, default='', verbose_name='Izoh')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name='Holati')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')
    resolved_at= models.DateTimeField(null=True, blank=True, verbose_name='Hal qilingan vaqt')
    resolved_by= models.CharField(max_length=255, blank=True, default='', verbose_name='Kim hal qildi')

    def __str__(self):
        return f"SOS #{self.id} — {self.driver.full_name} ({self.created_at:%d.%m.%Y %H:%M})"

    class Meta:
        verbose_name = 'SOS signal'
        verbose_name_plural = 'SOS signallar'
        ordering = ['-created_at']


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



class GroupMessage(models.Model):
    """Barcha haydovchilar uchun umumiy guruh chati."""
    driver      = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True, related_name='group_messages', verbose_name='Haydovchi')
    sender_name = models.CharField(max_length=100, blank=True, default='', verbose_name='Yuboruvchi ismi')
    text        = models.TextField(blank=True, default='', verbose_name='Xabar')
    audio       = models.FileField(upload_to='group_audio/', blank=True, null=True, verbose_name='Audio xabar')
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')

    @property
    def display_name(self):
        if self.driver:
            return self.driver.full_name
        return self.sender_name or 'Operator'

    @property
    def display_sub(self):
        if self.driver:
            return self.driver.car_number
        return ''

    def __str__(self):
        return f"{self.display_name}: {self.text[:40]}"

    class Meta:
        verbose_name = 'Guruh xabari'
        verbose_name_plural = 'Guruh xabarlari'
        ordering = ['created_at']


class BalanceLog(models.Model):
    ACTION_ADD    = 'add'
    ACTION_DEDUCT = 'deduct'
    ACTION_CHOICES = (
        (ACTION_ADD,    'Qo\'shildi'),
        (ACTION_DEDUCT, 'Ayirildi'),
    )
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='balance_logs', verbose_name='Haydovchi')
    action     = models.CharField(max_length=10, choices=ACTION_CHOICES)
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    note       = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Balans tarixi'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.driver.full_name} {self.action} {self.amount}"


class TariffSettings(models.Model):
    """Singleton: admin paneldan narx sozlamalari."""
    base_price    = models.DecimalField(max_digits=10, decimal_places=2, default=5000, verbose_name="Boshlang'ich narx (UZS)", help_text="Har bir buyurtma uchun minimal narx")
    price_per_km  = models.DecimalField(max_digits=10, decimal_places=2, default=2000, verbose_name="1 km narxi (UZS)")
    waiting_price_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Kutish narxi (1 daqiqa, UZS)", help_text="Haydovchi \"Kutish\" tugmasini bosgan vaqtda, har daqiqa uchun qo'shiladigan narx")
    commission    = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Haydovchi komissiyasi (UZS)", help_text="Har bir qabul qilingan buyurtma uchun haydovchi balansidan yechiladi")
    auto_dispatch = models.BooleanField(default=True, verbose_name="Avtomatik taqsimlash", help_text="Yoqilgan bo'lsa eng yaqin haydovchiga avtomatik beriladi")
    max_dispatch_attempts = models.IntegerField(default=4, verbose_name="Maksimal urinishlar soni", help_text="Buyurtma eng ko'pi bilan nechta haydovchiga navbatma-navbat ko'rsatiladi")
    dispatch_timeout      = models.IntegerField(default=10, verbose_name="Kutish vaqti (sekund)", help_text="Har bir haydovchi qabul qilishi uchun beriladigan vaqt")
    operator_phone = models.CharField(max_length=20, default='1351', verbose_name="Operator telefon raqami", help_text="Haydovchi qabul qilingan buyurtmani bekor qilmoqchi bo'lsa, shu raqamga qo'ng'iroq qiladi")
    updated_at    = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def calc_price(self, distance_km, waiting_minutes=0):
        if distance_km is None:
            return None
        price = self.base_price + Decimal(str(distance_km)) * self.price_per_km
        if waiting_minutes:
            price += Decimal(str(waiting_minutes)) * self.waiting_price_per_minute
        return price

    def __str__(self):
        return f"Tariff: {self.base_price} + {self.price_per_km}/km, komissiya={self.commission}"

    class Meta:
        verbose_name = "Tariff sozlamalari"
        verbose_name_plural = "Tariff sozlamalari"


class PanelEvent(models.Model):
    """Operator panelida ovozli bildirishnoma uchun hodisalar jurnali (polling orqali o'qiladi)."""
    EVENT_CHOICES = PANEL_SOUND_EVENTS

    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, verbose_name='Hodisa turi')
    message    = models.CharField(max_length=500, blank=True, default='', verbose_name='Xabar')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Vaqt')

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.created_at:%d.%m.%Y %H:%M}"

    class Meta:
        verbose_name = 'Panel hodisasi'
        verbose_name_plural = 'Panel hodisalari'
        ordering = ['-created_at']


class PanelSound(models.Model):
    """Operator panel va haydovchi ilovasi uchun har bir hodisaga tayinlangan audio fayl."""
    EVENT_CHOICES = PANEL_SOUND_EVENTS + DRIVER_SOUND_EVENTS

    event_key = models.CharField(max_length=30, unique=True, choices=EVENT_CHOICES, verbose_name='Hodisa')
    file      = models.FileField(upload_to='sounds/', blank=True, null=True, verbose_name='Audio fayl')
    enabled   = models.BooleanField(default=True, verbose_name='Yoqilgan')

    @classmethod
    def get_map(cls):
        """{event_key: PanelSound} — barcha qatorlarni bitta so'rovda olib keladi."""
        return {s.event_key: s for s in cls.objects.all()}

    def resolve_url(self):
        """Yoqilgan bo'lsa: yuklangan fayl -> standart statik fayl -> None (frontend sintez ohang chaladi)."""
        if not self.enabled:
            return None
        if self.file:
            return self.file.url
        return DEFAULT_SOUND_URLS.get(self.event_key)

    def __str__(self):
        return self.get_event_key_display()

    class Meta:
        verbose_name = 'Ovoz sozlamasi'
        verbose_name_plural = 'Ovoz sozlamalari'
