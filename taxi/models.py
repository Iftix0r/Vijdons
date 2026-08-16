from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
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

    CAR_TYPE_LIGHT   = 'light'
    CAR_TYPE_CARGO   = 'cargo'
    CAR_TYPE_MINIVAN = 'minivan'
    CAR_TYPE_CHOICES = (
        (CAR_TYPE_LIGHT,   '🚗 Yengil'),
        (CAR_TYPE_CARGO,   '🚚 Yuk mashinasi'),
        (CAR_TYPE_MINIVAN, '🚐 Minivan'),
    )

    user            = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='driver_profile')
    full_name       = models.CharField(max_length=255, verbose_name="Haydovchi ismi")
    phone_number    = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    car_model       = models.CharField(max_length=100, verbose_name="Mashina modeli")
    car_number      = models.CharField(max_length=20, verbose_name="Mashina raqami")
    car_type        = models.CharField(max_length=10, choices=CAR_TYPE_CHOICES, default=CAR_TYPE_LIGHT, verbose_name="Mashina turi")
    is_active       = models.BooleanField(default=True, verbose_name="Faol")
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_PENDING, verbose_name="Tasdiqlash holati")
    is_frozen       = models.BooleanField(default=False, verbose_name="Muzlatilgan", help_text="3+ kun onlayn bo'lmagani uchun avtomatik muzlatilgan — qayta ishga tushirish uchun admin blokni ochishi kerak")
    # Diqqat: balans manfiy bo'lishining o'zi "qarzdor" degani emas — bu
    # ATAYLAB qo'lda belgilanadigan bayroq (To'lov ekranidagi "Qarzdor" tugmasi
    # orqali), operator haydovchini haqiqatan ham qarzdorlar sifatida kuzatib
    # borishga qaror qilganda ishlatiladi. Shu orqali "Qarzdorlar" bo'limi
    # (`qarzdorlar_list`) faqat operator ATAYLAB belgilagan haydovchilarnigina
    # ko'rsatadi — vaqtinchalik manfiy balansli barcha haydovchilarni emas.
    is_qarzdor      = models.BooleanField(default=False, verbose_name="Qarzdor")
    sms_opt_out     = models.BooleanField(default=False, verbose_name="Ommaviy SMS'lardan chiqqan",
                                           help_text="\"BEKOR\" deb SMS javob yozsa avtomatik yoqiladi — "
                                                      "buyurtma/balans SMS'lariga ta'sir qilmaydi, faqat ommaviy xabarlar to'xtaydi")
    qarz_note       = models.CharField(max_length=255, blank=True, default='', verbose_name="Qarz izohi")
    qarz_marked_at  = models.DateTimeField(null=True, blank=True, verbose_name="Qarzdor deb belgilangan vaqt")
    fcm_token       = models.TextField(blank=True, null=True, verbose_name="FCM Token")
    is_on_duty      = models.BooleanField(default=False, verbose_name="Ish navbatida")
    latitude        = models.FloatField(null=True, blank=True, verbose_name="Kenglik (Latitude)")
    longitude       = models.FloatField(null=True, blank=True, verbose_name="Uzunlik (Longitude)")
    balance               = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Balans")
    low_balance_sms_at    = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi 'balans kam' SMS vaqti",
                                                  help_text="Har buyurtma qabul qilganda emas, bir necha soatda bir "
                                                             "marta SMS yuborilishi uchun (utils.tg_low_balance_alert)")
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
    freeze_warning_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Muzlash haqida oxirgi ogohlantirilgan vaqt")
    last_address          = models.CharField(max_length=500, blank=True, default='', verbose_name="So'nggi manzil")
    operator_typing_at    = models.DateTimeField(null=True, blank=True, verbose_name="Operator yozayotgan vaqt")
    ai_typing_at          = models.DateTimeField(null=True, blank=True, verbose_name="AI yordamchi javob tayyorlayotgan vaqt")
    last_group_read_at    = models.DateTimeField(default=timezone.now, blank=True, verbose_name="Guruh chatini oxirgi o'qigan vaqt")
    last_ping_ms          = models.IntegerField(null=True, blank=True, verbose_name="Oxirgi ping (ms)")
    last_ping_at          = models.DateTimeField(null=True, blank=True, verbose_name="Ping o'lchangan vaqt")
    device_model          = models.CharField(max_length=120, blank=True, default='', verbose_name="Qurilma modeli", help_text="Native ilovaga kirganda avtomatik yoziladi (masalan 'Samsung SM-A125F')")
    battery_level         = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Batareya foizi", help_text="Native ilova joylashuv yuborganda birga keladi")
    # Yaqin atrofida hech qanday SavedAddress topilmagan holatda, haydovchi
    # shu nuqtada qancha vaqtdan beri turganini kuzatish uchun (yangi manzil
    # AVTOMATIK yaratilishidan oldin) — util.py, update_address_queue_membership().
    pending_stand_lat     = models.FloatField(null=True, blank=True, verbose_name="Kutilayotgan yangi manzil (kenglik)")
    pending_stand_lng     = models.FloatField(null=True, blank=True, verbose_name="Kutilayotgan yangi manzil (uzunlik)")
    pending_stand_since   = models.DateTimeField(null=True, blank=True, verbose_name="Shu nuqtada turgan vaqtdan beri")

    LEVEL_THRESHOLDS = (
        (500, "Usta haydovchi"),
        (200, "Professional"),
        (50,  "Tajribali"),
        (0,   "Yangi haydovchi"),
    )

    @property
    def level(self):
        """Jami safarlar soniga qarab hisoblanadigan daraja (xaritadagi
        haydovchi kartochkasida ko'rsatish uchun)."""
        for threshold, label in self.LEVEL_THRESHOLDS:
            if self.trips_count >= threshold:
                return label
        return self.LEVEL_THRESHOLDS[-1][1]

    def __str__(self):
        return f"{self.full_name} ({self.car_number})"

    class Meta:
        verbose_name = "Haydovchi"
        verbose_name_plural = "Haydovchilar"


class Client(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='client_profile')
    full_name    = models.CharField(max_length=255, verbose_name="Mijoz ismi", null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    telegram_chat_id = models.CharField(max_length=50, blank=True, default='', verbose_name="Telegram chat ID",
                                        help_text="Mijoz botidan foydalansa avtomatik saqlanadi")
    is_blocked   = models.BooleanField(default=False, verbose_name="Bloklangan")
    sms_opt_out  = models.BooleanField(default=False, verbose_name="Ommaviy SMS'lardan chiqqan",
                                        help_text="\"BEKOR\" deb SMS javob yozsa avtomatik yoqiladi — "
                                                   "buyurtma holati SMS'lariga ta'sir qilmaydi, faqat ommaviy xabarlar to'xtaydi")
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

    # Haydovchi hali yakunlamagan (band) buyurtma holatlari
    ACTIVE_STATUSES = ('accepted', 'on_way', 'arrived')
    # Bir haydovchi bir vaqtning o'zida shuncha buyurtmani band qila oladi
    MAX_ACTIVE_PER_DRIVER = 2

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
    # Haydovchi "Yo'lga chiqdim"/"Yetib keldim" tugmasini bosgan paytdagi
    # haqiqiy GPS joylashuvi — mijoz kiritgan from_address'dan farqli, bu
    # haydovchining o'sha ondagi haqiqiy holatini qayd etadi (operator
    # panelida va taximetr vidjetida ko'rsatish uchun).
    on_way_lat      = models.FloatField(null=True, blank=True, verbose_name="Yo'lga chiqqan joy (Lat)")
    on_way_lng      = models.FloatField(null=True, blank=True, verbose_name="Yo'lga chiqqan joy (Lng)")
    on_way_address  = models.CharField(max_length=255, blank=True, default='', verbose_name="Yo'lga chiqqan manzil")
    arrived_lat     = models.FloatField(null=True, blank=True, verbose_name="Yetib kelgan joy (Lat)")
    arrived_lng     = models.FloatField(null=True, blank=True, verbose_name="Yetib kelgan joy (Lng)")
    arrived_address = models.CharField(max_length=255, blank=True, default='', verbose_name="Yetib kelgan manzil")
    distance_km    = models.FloatField(null=True, blank=True, verbose_name="Masofa (km)")
    tmx_dist_km    = models.FloatField(default=0, verbose_name="Taximetr masofa (km)")
    tmx_paused     = models.BooleanField(default=False, verbose_name="Taximetr pauza")
    tmx_paused_ms  = models.BigIntegerField(default=0, verbose_name="Taximetr pauza (ms)")
    tmx_start_time = models.DateTimeField(null=True, blank=True, verbose_name="Taximetr boshlangan vaqt")
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Narxi")
    commission   = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Komissiya")
    payment_type  = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH, verbose_name="To'lov turi")
    car_type      = models.CharField(max_length=10, choices=Driver.CAR_TYPE_CHOICES, default=Driver.CAR_TYPE_LIGHT, verbose_name="Mashina turi")
    is_delivery   = models.BooleanField(default=False, verbose_name="Yetkazib berish")
    note          = models.TextField(blank=True, default='', verbose_name="Izoh")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    cancel_reason = models.CharField(max_length=255, blank=True, default='', verbose_name="Bekor qilish sababi")
    dispatched_to = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatched_orders', verbose_name="Yuborilgan haydovchi")
    dispatched_at = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqti")
    rejected_by   = models.ManyToManyField(Driver, blank=True, related_name='rejected_orders', verbose_name="Rad etgan haydovchilar")
    created_by_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='self_registered_orders', verbose_name="Ilova orqali ro'yxatga olgan haydovchi")
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


class DispatchAttempt(models.Model):
    """Buyurtma taqsimlanayotganda qaysi haydovchiga, necha km masofada,
    qanday navbat bilan taklif qilingani va natijasi — buyurtma
    tafsilotlarida "Taqsimlash tarixi" sifatida ko'rsatish uchun."""
    RESULT_PENDING   = 'pending'
    RESULT_ACCEPTED  = 'accepted'
    RESULT_REJECTED  = 'rejected'
    RESULT_TIMEOUT   = 'timeout'
    RESULT_CANCELLED = 'cancelled'
    RESULT_CHOICES = (
        (RESULT_PENDING,   'Kutilmoqda'),
        (RESULT_ACCEPTED,  'Qabul qildi'),
        (RESULT_REJECTED,  'Rad etdi'),
        (RESULT_TIMEOUT,   "Javob bermadi"),
        (RESULT_CANCELLED, 'Bekor qilindi'),
    )

    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='dispatch_attempts', verbose_name="Buyurtma")
    driver         = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='dispatch_attempts', verbose_name="Haydovchi")
    distance_km    = models.FloatField(null=True, blank=True, verbose_name="Masofa (km)")
    attempt_number = models.PositiveIntegerField(verbose_name="Urinish raqami")
    result         = models.CharField(max_length=20, choices=RESULT_CHOICES, default=RESULT_PENDING, verbose_name="Natija")
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name="Taklif qilingan vaqt")
    resolved_at    = models.DateTimeField(null=True, blank=True, verbose_name="Hal bo'lgan vaqt")

    def __str__(self):
        return f"#{self.order_id} → {self.driver} ({self.attempt_number}-urinish, {self.get_result_display()})"

    class Meta:
        ordering = ['attempt_number']
        verbose_name = "Taqsimlash urinishi"
        verbose_name_plural = "Taqsimlash urinishlari"


class ChatMessage(models.Model):
    SENDER_DRIVER   = 'driver'
    SENDER_OPERATOR = 'operator'
    SENDER_AI       = 'ai'
    SENDER_CHOICES  = (
        (SENDER_DRIVER,   'Haydovchi'),
        (SENDER_OPERATOR, 'Operator'),
        (SENDER_AI,       'AI yordamchi'),
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
    driver_group_id = models.CharField(max_length=50, blank=True, default='', verbose_name='Haydovchilar Guruhi Chat ID',
                                       help_text="Yangi buyurtmalar shu guruhga ham yuboriladi — mijoz telefon raqamisiz")
    driver_extra_group_ids = models.TextField(blank=True, default='', verbose_name="Qo'shimcha haydovchilar guruhlari",
                                              help_text='Har bir ID yangi qatorda')
    notify_driver_group   = models.BooleanField(default=True, verbose_name='Haydovchilar guruhiga yuborish')

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

    def get_all_driver_group_ids(self):
        """Haydovchilar guruhi(lari) IDlarini list sifatida qaytaradi."""
        ids = []
        if self.driver_group_id.strip():
            ids.append(self.driver_group_id.strip())
        for line in self.driver_extra_group_ids.splitlines():
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
    notify_deleted        = models.BooleanField(default=True,  verbose_name="Buyurtma o'chirildi")
    notify_driver_register= models.BooleanField(default=True,  verbose_name="Yangi haydovchi ro'yxatdan o'tdi")
    notify_driver_approved= models.BooleanField(default=True,  verbose_name='Haydovchi tasdiqlandi')
    notify_driver_rejected= models.BooleanField(default=True,  verbose_name='Haydovchi rad etildi')
    notify_driver_blocked = models.BooleanField(default=True,  verbose_name='Haydovchi bloklandi/ochildi')
    notify_driver_login   = models.BooleanField(default=False, verbose_name='Haydovchi kirdi (login)')
    notify_duty_changed   = models.BooleanField(default=False, verbose_name='Navbat holati o\'zgardi')
    notify_balance_changed= models.BooleanField(default=True,  verbose_name='Balans o\'zgardi')
    notify_low_balance    = models.BooleanField(default=True,  verbose_name='Balans kam ogohlantirish')

    # Kunlik/haftalik/oylik jadval bo'yicha xabarlar (ilova ichidagi scheduler orqali chaqiriladi)
    notify_morning_greeting    = models.BooleanField(default=True, verbose_name='Ertalabki salomlashuv')
    notify_evening_top_drivers = models.BooleanField(default=True, verbose_name="Kechqurungi TOP-10 haydovchilar")
    notify_night_greeting      = models.BooleanField(default=True, verbose_name='Tungi navbatchilarga salom')
    notify_weekly_top_drivers  = models.BooleanField(default=True, verbose_name="Haftalik TOP-10 haydovchilar")
    notify_monthly_top_drivers = models.BooleanField(default=True, verbose_name="Oylik TOP-10 haydovchilar")
    notify_inactive_drivers    = models.BooleanField(default=True, verbose_name="Uzoq faol bo'lmagan haydovchilar hisoboti")
    notify_top_hours_drivers   = models.BooleanField(default=True, verbose_name="Eng ko'p soat ishlagan haydovchilar")
    notify_high_rejection      = models.BooleanField(default=True, verbose_name="Ko'p rad etish haqida ogohlantirish")
    notify_daily_summary       = models.BooleanField(default=True, verbose_name='Kunlik umumiy hisobot')
    notify_weekly_summary      = models.BooleanField(default=True, verbose_name='Haftalik umumiy hisobot')
    notify_daily_highlight     = models.BooleanField(default=True, verbose_name='Kunning yorqin lahzalari')
    notify_monthly_financial_report = models.BooleanField(default=True, verbose_name="Oylik moliyaviy hisobot")
    notify_driver_engagement  = models.BooleanField(default=True, verbose_name="Motivatsion/maslahat/hazil xabarlar")
    notify_driver_fun_stats   = models.BooleanField(default=True, verbose_name="Kunlik qiziqarli statistika")

    # Voqea asosida (event-based) yangi bildirishnomalar
    notify_low_rating         = models.BooleanField(default=True, verbose_name='Reyting pasayganda ogohlantirish')
    notify_surge_alert        = models.BooleanField(default=True, verbose_name='Talab yuqori bo\'lganda ogohlantirish')
    notify_driver_milestone   = models.BooleanField(default=True, verbose_name='Haydovchi yubileyi (safarlar soni)')
    notify_sos_to_driver_group= models.BooleanField(default=True, verbose_name='SOS signalini haydovchilar guruhiga ham yuborish')
    notify_flyer_redeemed     = models.BooleanField(default=True, verbose_name='Flayer kuponi ishlatilganda xabar')
    notify_balance_changed_to_driver_group = models.BooleanField(default=True, verbose_name="Balans to'ldirilganda haydovchilar guruhiga ham yuborish")
    notify_low_balance_to_driver_group     = models.BooleanField(default=True, verbose_name='Balans kam qolganda haydovchilar guruhiga ham yuborish')
    notify_freeze_warning = models.BooleanField(default=True, verbose_name="Muzlashga 1 kun qolganda ogohlantirish")
    notify_goal_events    = models.BooleanField(default=True, verbose_name="Maqsadga erishilganda/muddat yaqinlashganda xabar")

    # Har bir kunlik/haftalik/oylik xabar oxirgi marta yuborilgan sana — bir marta
    # yuborilib ketmasligi uchun (masalan bir nechta worker jarayoni bo'lsa)
    last_morning_greeting_date       = models.DateField(null=True, blank=True)
    last_evening_top_drivers_date    = models.DateField(null=True, blank=True)
    last_night_greeting_date         = models.DateField(null=True, blank=True)
    last_weekly_top_drivers_date     = models.DateField(null=True, blank=True)
    last_monthly_top_drivers_date    = models.DateField(null=True, blank=True)
    last_inactive_drivers_report_date= models.DateField(null=True, blank=True)
    last_surge_alert_at              = models.DateTimeField(null=True, blank=True)
    last_order_creating_at           = models.DateTimeField(null=True, blank=True, verbose_name="Operator buyurtma yaratayotgani so'nggi bildirilgan vaqt")
    last_top_hours_drivers_date      = models.DateField(null=True, blank=True)
    last_high_rejection_report_date  = models.DateField(null=True, blank=True)
    last_daily_summary_date          = models.DateField(null=True, blank=True)
    last_weekly_summary_date         = models.DateField(null=True, blank=True)
    last_daily_highlight_date        = models.DateField(null=True, blank=True)
    last_monthly_financial_report_date = models.DateField(null=True, blank=True)
    last_driver_engagement_noon_date    = models.DateField(null=True, blank=True)
    last_driver_engagement_evening_date = models.DateField(null=True, blank=True)
    last_driver_fun_stats_date          = models.DateField(null=True, blank=True)
    last_freeze_inactive_drivers_date   = models.DateField(null=True, blank=True)
    last_freeze_warning_date            = models.DateField(null=True, blank=True)

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


class BotAdmin(models.Model):
    """Operator bot bilan shaxsiy chatda admin buyruqlaridan (buyurtma yaratish,
    haydovchilarni boshqarish va h.k.) foydalanishga ruxsati bor Telegram foydalanuvchi."""
    chat_id    = models.CharField(max_length=50, unique=True, verbose_name='Telegram Chat ID')
    full_name  = models.CharField(max_length=255, blank=True, default='', verbose_name='Ism (ixtiyoriy)')
    is_active  = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqti")

    def __str__(self):
        return f"{self.full_name or 'Admin'} ({self.chat_id})"

    class Meta:
        verbose_name = 'Bot admin'
        verbose_name_plural = 'Bot adminlari'
        ordering = ['-created_at']


class SmsSettings(models.Model):
    """Singleton: SMS sozlamalari."""
    PROVIDER_ESKIZ = 'eskiz'
    PROVIDER_LOCAL_GATEWAY = 'local_gateway'
    PROVIDER_CHOICES = (
        (PROVIDER_ESKIZ, 'Eskiz.uz'),
        (PROVIDER_LOCAL_GATEWAY, "Telefon orqali (mahalliy SIM, vijdon_sms_gateway ilovasi)"),
    )
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_ESKIZ, verbose_name='SMS xizmati',
        help_text="\"Telefon orqali\" tanlansa, Eskiz.uz'ga pul to'lash shart emas — SMS'lar "
                   "vijdon_sms_gateway ilovasi o'rnatilgan telefon(lar)ning oddiy SIM kartasi orqali "
                   "yuboriladi. Diqqat: bu usul mobil operator tomonidan cheklanishi/bloklanishi "
                   "mumkin — katta hajmda (kuniga yuzlab SMS) ehtiyot bo'ling.",
    )
    email      = models.CharField(max_length=255, blank=True, default='', verbose_name='Eskiz Email',
                                   help_text='Eskiz.uz kabinetiga kirish emaili')
    password   = models.CharField(max_length=255, blank=True, default='', verbose_name='Eskiz Parol')
    nickname   = models.CharField(max_length=50, blank=True, default='4546', verbose_name='Sender nomi (nickname)',
                                   help_text="Eskiz'da tasdiqlangan alfa-nom. Test rejimida 4546")
    token      = models.TextField(blank=True, default='', verbose_name='Auth token (avtomatik)')
    token_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='Token yangilangan vaqt')

    # Bildirishnoma toggle lar (mijozga SMS)
    sms_accepted  = models.BooleanField(default=True, verbose_name='Buyurtma qabul qilindi')
    sms_arrived   = models.BooleanField(default=True, verbose_name='Haydovchi yetib keldi')
    sms_completed = models.BooleanField(default=True, verbose_name='Buyurtma yakunlandi')
    sms_cancelled = models.BooleanField(default=True, verbose_name='Buyurtma bekor qilindi')

    # Bildirishnoma toggle lar (haydovchiga SMS) — push/Telegram'ga QO'SHIMCHA,
    # internet yo'q/sekin bo'lganda ham yetib borishi uchun.
    sms_driver_cancelled      = models.BooleanField(default=True, verbose_name="Haydovchiga: buyurtma bekor qilindi/qayta ochildi")
    sms_driver_new_order      = models.BooleanField(
        default=False, verbose_name='Haydovchiga: yangi buyurtma (zaxira)',
        help_text="Diqqat: bu har bir tayinlangan buyurtmada yuboriladi — push allaqachon bor, "
                   "shu sabab sukut bo'yicha O'CHIQ (katta hajm SIM-blok xavfini oshiradi).",
    )
    sms_driver_low_balance    = models.BooleanField(default=True, verbose_name='Haydovchiga: balans kam qoldi')
    sms_driver_topup_approved = models.BooleanField(default=True, verbose_name="Haydovchiga: to'lov tasdiqlandi")

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'SMS Sozlamalari'

    class Meta:
        verbose_name = 'SMS sozlamalari'
        verbose_name_plural = 'SMS sozlamalari'


class AiSettings(models.Model):
    """Singleton: dashboard uchun OpenAI o'sish tavsiyalari sozlamalari."""
    MODEL_CHOICES = [
        ('gpt-4o-mini', 'GPT-4o mini (tez va arzon)'),
        ('gpt-4o',       'GPT-4o'),
    ]
    api_key = models.CharField(max_length=255, blank=True, default='', verbose_name='OpenAI API kalit',
                                help_text='platform.openai.com dan olingan sk-... kalit')
    model   = models.CharField(max_length=50, choices=MODEL_CHOICES, default='gpt-4o-mini', verbose_name='Model')
    chat_ai_enabled = models.BooleanField(default=True, verbose_name='Chatda AI javob bersin',
                                           help_text='Yoqilsa, haydovchi ilovasidagi Chat bo\'limida AI avtomatik javob beradi')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'AI Sozlamalari'

    class Meta:
        verbose_name = 'AI sozlamalari'
        verbose_name_plural = 'AI sozlamalari'


class AiRewardLog(models.Model):
    """Operator AI tavsiya qilgan sovg'ani haydovchi/mijozga 'berdim' deb belgilagan
    holatlar tarixi. Shu davr (oy) uchun belgilangan kishi keyingi AI tavsiyasida
    qayta taklif qilinmaydi — sovg'a AI tomonidan avtomatik berilmaydi, faqat
    operator tasdiqlagach shu yerga yoziladi."""
    TYPE_DRIVER = 'driver'
    TYPE_CLIENT = 'client'
    TYPE_CHOICES = [(TYPE_DRIVER, 'Haydovchi'), (TYPE_CLIENT, 'Mijoz')]

    reward_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    driver      = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.CASCADE, related_name='ai_rewards')
    client      = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE, related_name='ai_rewards')
    period      = models.CharField(max_length=7, verbose_name="Davr (YYYY-MM)")
    reward_text = models.TextField(blank=True, default='', verbose_name="Sovg'a tavsifi")
    given_by    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    given_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.driver.full_name if self.driver else (self.client.full_name or self.client.phone_number if self.client else '—')
        return f"{who} — {self.period}"

    class Meta:
        verbose_name = "AI sovg'a tarixi"
        verbose_name_plural = "AI sovg'a tarixi"
        constraints = [
            models.UniqueConstraint(fields=['reward_type', 'driver', 'period'], name='unique_driver_reward_per_period'),
            models.UniqueConstraint(fields=['reward_type', 'client', 'period'], name='unique_client_reward_per_period'),
        ]


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
    ACTION_FREEZE   = 'freeze'
    ACTION_UNFREEZE = 'unfreeze'
    ACTION_QARZ_ON   = 'qarz_on'
    ACTION_QARZ_OFF  = 'qarz_off'
    ACTION_QARZ_NOTE = 'qarz_note'
    ACTION_CHOICES  = (
        (ACTION_LOGIN,    'Kirish'),
        (ACTION_LOGOUT,   'Chiqish'),
        (ACTION_BLOCK,    'Bloklandi'),
        (ACTION_UNBLOCK,  'Blok ochildi'),
        (ACTION_BALANCE,  'Balans o\'zgardi'),
        (ACTION_DUTY_ON,  'Navbatga kirdi'),
        (ACTION_DUTY_OFF, 'Navbatdan chiqdi'),
        (ACTION_ORDER,    'Buyurtma'),
        (ACTION_FREEZE,   'Muzlatildi'),
        (ACTION_UNFREEZE, 'Muzlash bekor qilindi'),
        (ACTION_QARZ_ON,   'Qarzdorlar ro\'yxatiga qo\'shildi'),
        (ACTION_QARZ_OFF,  'Qarzdorlar ro\'yxatidan chiqarildi'),
        (ACTION_QARZ_NOTE, 'Qarz izohi tahrirlandi'),
    )

    driver     = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='activity_logs', verbose_name='Haydovchi')
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Amal')
    detail     = models.CharField(max_length=500, blank=True, default='', verbose_name='Tafsilot')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP manzil')
    user_agent = models.TextField(blank=True, default='', verbose_name='Qurilma / Brauzer')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')

    def __str__(self):
        return f"{self.driver.full_name} — {self.get_action_display()} ({self.created_at:%d.%m.%Y %H:%M})"

    ACTION_ICONS = {
        ACTION_LOGIN: '🔑', ACTION_LOGOUT: '🚪', ACTION_BLOCK: '🚫',
        ACTION_UNBLOCK: '🔓', ACTION_BALANCE: '💰', ACTION_DUTY_ON: '🟢',
        ACTION_DUTY_OFF: '🔴', ACTION_ORDER: '🚕',
        ACTION_FREEZE: '🥶', ACTION_UNFREEZE: '🔥',
        ACTION_QARZ_ON: '📌', ACTION_QARZ_OFF: '✅', ACTION_QARZ_NOTE: '✏️',
    }

    @staticmethod
    def _device_label(user_agent):
        """user_agent satridan qurilma/brauzer turini o'qiladigan qisqa yorliqqa
        aylantiradi — taxi/templates/taxi/driver_detail.html'dagi bilan bir xil mantiq."""
        if not user_agent:
            return None
        ua = user_agent
        if 'Android' in ua:
            os_label = 'Android'
        elif 'iPhone' in ua or 'iOS' in ua:
            os_label = 'iOS'
        elif 'Windows' in ua:
            os_label = 'Windows'
        elif 'Linux' in ua:
            os_label = 'Linux'
        elif 'Mac' in ua:
            os_label = 'Mac'
        else:
            os_label = None
        if 'Chrome' in ua:
            browser = 'Chrome'
        elif 'Firefox' in ua:
            browser = 'Firefox'
        elif 'Safari' in ua:
            browser = 'Safari'
        else:
            browser = None
        parts = [p for p in (os_label, browser) if p]
        return ' / '.join(parts) if parts else None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new:
            return
        try:
            from taxi.utils import notify_developer
            icon = self.ACTION_ICONS.get(self.action, '🚕')
            lines = [
                f"{icon} <b>Haydovchi faolligi</b>",
                f"Haydovchi: {self.driver.full_name} ({self.driver.phone_number})",
                f"Amal: {self.get_action_display()}",
            ]
            if self.detail:
                lines.append(f"Tafsilot: {self.detail}")
            if self.ip_address:
                lines.append(f"IP: {self.ip_address}")
            device = self._device_label(self.user_agent)
            if device:
                lines.append(f"Qurilma: {device}")
            lines.append(f"Vaqt: {self.created_at:%d.%m.%Y %H:%M:%S}")
            notify_developer('\n'.join(lines))
        except Exception:
            pass

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


class BalanceTopupRequest(models.Model):
    """Haydovchi saytdan to'lov chekini yuklab balans to'ldirishni so'raydi —
    admin operator botdan chekni ko'rib tasdiqlaydi yoki rad etadi."""
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = (
        (STATUS_PENDING,  'Kutilmoqda'),
        (STATUS_APPROVED, 'Tasdiqlandi'),
        (STATUS_REJECTED, 'Rad etildi'),
    )

    driver      = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='topup_requests', verbose_name='Haydovchi')
    amount      = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="So'ralgan summa")
    receipt     = models.ImageField(upload_to='topup_receipts/', verbose_name='Chek rasmi')
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Holati')
    reject_reason = models.CharField(max_length=255, blank=True, default='', verbose_name='Rad etish sababi')
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Hal qilingan vaqti')

    def __str__(self):
        return f"{self.driver.full_name} — {self.amount} UZS ({self.get_status_display()})"

    class Meta:
        verbose_name = "Balans to'ldirish so'rovi"
        verbose_name_plural = "Balans to'ldirish so'rovlari"
        ordering = ['-created_at']


class TariffSettings(models.Model):
    """Singleton: admin paneldan narx sozlamalari."""
    base_price    = models.DecimalField(max_digits=10, decimal_places=2, default=5000, verbose_name="Boshlang'ich narx (UZS)", help_text="Har bir buyurtma uchun minimal narx")
    price_per_km  = models.DecimalField(max_digits=10, decimal_places=2, default=2000, verbose_name="1 km narxi (UZS)")
    waiting_price_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Kutish narxi (1 daqiqa, UZS)", help_text="Haydovchi \"Kutish\" tugmasini bosgan vaqtda, har daqiqa uchun qo'shiladigan narx")
    commission    = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Haydovchi komissiyasi (UZS)", help_text="Har bir qabul qilingan buyurtma uchun haydovchi balansidan yechiladi")
    auto_dispatch = models.BooleanField(default=True, verbose_name="Avtomatik taqsimlash", help_text="Yoqilgan bo'lsa eng yaqin haydovchiga avtomatik beriladi")
    max_dispatch_attempts = models.IntegerField(default=4, verbose_name="Maksimal urinishlar soni", help_text="Buyurtma eng ko'pi bilan nechta haydovchiga navbatma-navbat ko'rsatiladi")
    fairness_weight_km = models.FloatField(default=1.2, verbose_name="Adolat vazni (km)", help_text="Taqsimlashda haydovchining bugun yakunlagan har bir buyurtmasi 'masofasiga' shuncha km qo'shib hisoblanadi, uzoq kutgan haydovchining esa masofasi kamayadi (har 10 daqiqa kutish ≈ 1 km) — shu orqali band haydovchi hammasini olib ketmaydi. 0 = faqat masofa bo'yicha (adolat hisobga olinmaydi)")
    fairness_max_radius_km = models.FloatField(default=3.0, verbose_name="Adolat radiusi (km)", help_text="Shu radiusdan uzoqdagi haydovchilar adolat hisobida (bugungi yuk/kutish bonusi) qatnashmaydi — mijozni ortiqcha kutdirmaslik uchun. Lekin radius ichida hech kim topilmasa, buyurtma baribir eng yaqin haydovchiga individual yuboriladi (umumiy tabloga tushmaydi). 0 = cheklovsiz")
    dispatch_timeout      = models.IntegerField(default=10, verbose_name="Kutish vaqti (sekund)", help_text="Har bir haydovchi qabul qilishi uchun beriladigan vaqt")
    operator_phone = models.CharField(max_length=20, default='1351', verbose_name="Operator telefon raqami", help_text="Haydovchi qabul qilingan buyurtmani bekor qilmoqchi bo'lsa, shu raqamga qo'ng'iroq qiladi")
    office_name = models.CharField(max_length=100, blank=True, default='1351 Taxi ofisi', verbose_name="Ofis nomi", help_text="Haydovchilar xaritasidagi belgi tagida ko'rinadi")
    office_lat  = models.FloatField(null=True, blank=True, verbose_name="Ofis Kenglik (Lat)")
    office_lng  = models.FloatField(null=True, blank=True, verbose_name="Ofis Uzunlik (Lng)")
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


class SystemAuditLog(models.Model):
    """Tizim (dasturchi) paneli uchun xavfsizlik/audit jurnali — PanelEvent'dan
    ATAYLAB alohida: PanelEvent operator panelidagi OVOZLI bildirishnoma
    feedini boshqaradi (kundalik ish hodisalari), bu esa faqat /system/
    panelida ko'rinadigan, operatorlarga aloqasi yo'q texnik/xavfsizlik
    yozuvlari uchun (muvaffaqiyatsiz kirish urinishlari, sozlama
    o'zgarishlari, backup amallari, server xatolari/traceback)."""
    LEVEL_INFO    = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR   = 'error'
    LEVEL_CHOICES = [
        (LEVEL_INFO,    'Info'),
        (LEVEL_WARNING, 'Ogohlantirish'),
        (LEVEL_ERROR,   'Xato'),
    ]

    level      = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO, verbose_name='Daraja')
    event_type = models.CharField(max_length=50, verbose_name='Hodisa turi')
    message    = models.CharField(max_length=500, blank=True, default='', verbose_name='Xabar')
    detail     = models.TextField(blank=True, default='', verbose_name="Tafsilot (masalan traceback)")
    user       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Foydalanuvchi')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP manzil')
    path       = models.CharField(max_length=300, blank=True, default='', verbose_name='Manzil (path)')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Vaqt')

    def __str__(self):
        return f"[{self.level}] {self.event_type} — {self.created_at:%d.%m.%Y %H:%M}"

    class Meta:
        verbose_name = 'Tizim jurnali yozuvi'
        verbose_name_plural = 'Tizim jurnali'
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


DEFAULT_CONTRACT_TEXT = """VIJDON TAXI SERVISI BILAN HAYDOVCHI O'RTASIDA TUZILADIGAN HAMKORLIK SHARTNOMASI

0. SHARTNOMA PREDMETI
0.1. Ushbu shartnoma "Vijdon Taxi" xizmati (bundan buyon — Kompaniya) bilan Kompaniyaning "Vijdon Driver" mobil ilovasi/platformasiga (bundan buyon — Platforma) ro'yxatdan o'tgan haydovchi (bundan buyon — Haydovchi) o'rtasida yo'lovchi tashish buyurtmalarini taqsimlash bo'yicha hamkorlik shartlarini belgilaydi.
0.2. Kompaniya yaqinda faoliyat yuritishni boshlagan taksi xizmati bo'lib, Platforma va ish jarayonlari doimiy takomillashtirilib boriladi. Shu sababli ushbu shartnoma vaqti-vaqti bilan yangilanishi mumkin (8-bandga qarang).

1. ATAMALAR
1.1. Kompaniya — "Vijdon Taxi" xizmatini yurituvchi tomon, buyurtmalarni Platforma orqali haydovchilarga taqsimlaydi.
1.2. Haydovchi — Platformaga ro'yxatdan o'tgan, mustaqil ravishda o'z transport vositasida buyurtmalarni bajaruvchi shaxs.
1.3. Platforma — buyurtmalarni qabul qilish, taqsimlash va hisob-kitob yuritish uchun mo'ljallangan "Vijdon Driver" ilovasi va unga bog'liq tizimlar.
1.4. Elektron imzo — Haydovchi tomonidan Platforma orqali barmoq yoki sichqoncha yordamida chizilgan raqamli imzo, sanasi va IP-manzili bilan birga qayd etiladi.

2. UMUMIY QOIDALAR
2.1. Haydovchi ushbu shartnoma shartlarini to'liq o'qib chiqqach, Platforma orqali elektron imzo qo'yish yo'li bilan shartnoma shartlariga rozilik bildiradi. Elektron imzo qog'ozdagi imzo bilan teng huquqiy kuchga ega.
2.2. Haydovchi Kompaniyaning shtatdagi xodimi emas, balki mustaqil hamkor sifatida buyurtmalarni bajaradi va o'z soliq/huquqiy majburiyatlari uchun mustaqil javobgar hisoblanadi.
2.3. Ushbu shartnoma Haydovchini faqat Kompaniya bilan ishlashga majburlamaydi — Haydovchi istalgan boshqa xizmat yoki ish bilan parallel shug'ullanishi mumkin.

3. HAYDOVCHIGA QO'YILADIGAN TALABLAR
3.1. Haydovchida amaldagi haydovchilik guvohnomasi, transport vositasi esa texnik ko'rikdan o'tgan va sug'urtalangan bo'lishi shart.
3.2. Haydovchi mashinani toza va ishlaydigan holatda saqlashi, buyurtmani belgilangan vaqtda qabul qilishi shart.
3.3. Yo'lovchilar bilan xushmuomala, hurmatli munosabatda bo'lish, haydash chog'ida telefon bilan chalg'imaslik, tezlik chegaralariga va yo'l harakati qoidalariga qat'iy rioya qilish majburiy.
3.4. Ish vaqtida spirtli ichimlik yoki boshqa mast qiluvchi vositalar iste'mol qilish qat'iyan taqiqlanadi — bunday holat aniqlansa, Haydovchi Platformadan darhol va butunlay chetlashtiriladi.
3.5. Haydovchi Kompaniyaning nomi, logotipi va boshqa belgilarini Kompaniyaning yozma roziligisiz tijorat maqsadida ishlatmasligi shart.

4. BUYURTMALAR VA TO'LOVLAR
4.1. Buyurtmalar tizim orqali avtomatik taqsimlanadi, Haydovchi sababsiz buyurtmani tez-tez rad etmasligi lozim.
4.2. Har bir yakunlangan buyurtmadan tizim komissiyasi joriy tarif sozlamalariga muvofiq ushlab qolinadi. Komissiya miqdori Platforma ichida ochiq ko'rsatiladi va o'zgargan taqdirda Haydovchiga ilova orqali oldindan xabar beriladi.
4.3. Haydovchi balansi manfiy bo'lib qolgan taqdirda yangi buyurtmalar qabul qila olmaydi, balansni ilova orqali o'z vaqtida to'ldirishi lozim.

5. JARIMALAR VA CHEKLOVLAR
5.1. Sababsiz buyurtmani bekor qilish, mijozdan qo'shimcha pul talab qilish, buyurtmani chetlab o'tish kabi holatlar aniqlansa, Kompaniya Haydovchiga ogohlantirish berish, vaqtinchalik yoki butunlay Platformadan chetlashtirish huquqiga ega.
5.2. Mijozlar tomonidan takroran asosli shikoyatlar tushgan taqdirda Kompaniya Haydovchi profilini ko'rib chiqadi va tegishli chora ko'radi. Har qanday cheklov haqida Haydovchiga sababini ko'rsatgan holda xabar beriladi.

6. TEXNIK NOSOZLIKLAR VA FORS-MAJOR
6.1. Platforma yangi ishga tushirilgani sababli vaqti-vaqti bilan texnik uzilishlar yoki nosozliklar yuzaga kelishi mumkin. Kompaniya bunday vaqtinchalik texnik nosozliklar tufayli Haydovchi ko'rgan bilvosita zararlar uchun javobgar bo'lmaydi, lekin muammoni imkon qadar tezroq bartaraf etishga harakat qiladi.
6.2. Tabiiy ofat, internet/aloqa uzilishi, davlat organlari qarorlari va boshqa tomonlar nazoratidan tashqari holatlar (fors-major) yuzasidan hech bir tomon ikkinchi tomon oldida javobgar bo'lmaydi.

7. MAXFIYLIK
7.1. Haydovchi buyurtma davomida olingan mijoz ma'lumotlarini (telefon raqami, manzili va h.k.) faqat buyurtmani bajarish maqsadida ishlatishi, uchinchi shaxslarga bermasligi shart.
7.2. Kompaniya Haydovchining shaxsiy ma'lumotlarini (jumladan elektron imzosini) faqat ushbu shartnoma doirasida, hisobot va huquqiy talablarni bajarish maqsadida saqlaydi va uchinchi shaxslarga oshkor qilmaydi.

8. TOMONLARNING HUQUQ VA MAJBURIYATLARI
8.1. Kompaniya buyurtmalarni imkon qadar adolatli taqsimlash, Haydovchi bilan qo'llab-quvvatlash aloqasini (chat, bot) ta'minlash, hisob-kitoblarni o'z vaqtida amalga oshirishga majburdir.
8.2. Ushbu shartnoma matni Kompaniya tomonidan yangilanishi mumkin — yangilangan taqdirda Haydovchidan shartnomani qayta ko'rib chiqib, qayta imzolashi so'raladi. Eski versiya bo'yicha qilingan harakatlar o'z kuchida qoladi.

9. MAS'ULIYAT CHEGARASI
9.1. Yo'l harakati qoidalarini buzish, transport vositasining texnik holati va yo'l-transport hodisalari yuzasidan to'liq mas'uliyat Haydovchi zimmasida bo'ladi.
9.2. Kompaniya faqat buyurtmalarni taqsimlovchi platforma bo'lib, Haydovchi va yo'lovchi o'rtasidagi bevosita xizmat ko'rsatish jarayoniga aralashmaydi va shu jarayonda yuzaga kelgan to'g'ridan-to'g'ri bo'lmagan (bilvosita) zararlar uchun javobgar emas.

10. NIZOLARNI HAL QILISH TARTIBI
10.1. Ushbu shartnoma yuzasidan kelib chiqadigan barcha kelishmovchiliklar avvalo tomonlar o'rtasida muzokaralar yo'li bilan hal qilinadi.
10.2. Muzokaralar orqali kelishuvga erishilmasa, nizo O'zbekiston Respublikasining amaldagi qonunchiligiga muvofiq hal qilinadi.

11. SHARTNOMANING AMAL QILISH MUDDATI VA BEKOR QILISH
11.1. Shartnoma Haydovchi elektron imzo qo'ygan kundan boshlab kuchga kiradi va muddatsiz amal qiladi.
11.2. Har ikki tomon istalgan vaqtda, kamida bildirishnoma asosida hamkorlikni to'xtatishi mumkin — Haydovchi tomonidan profilni faoliyatsizlantirish, Kompaniya tomonidan esa Platformadan chetlashtirish orqali.
11.3. Kompaniya ushbu shartnoma qoidalarini jiddiy buzgan (3.4-band kabi) Haydovchini oldindan ogohlantirmasdan Platformadan chetlashtirish huquqini o'zida saqlab qoladi.

12. YAKUNIY QOIDALAR
12.1. Elektron imzo qo'yish orqali Haydovchi yuqoridagi barcha shartlarni o'qigan, tushungan va ularga to'liq rozi ekanligini tasdiqlaydi.
12.2. Ushbu shartnomada nazarda tutilmagan masalalar O'zbekiston Respublikasining amaldagi qonunchiligi asosida tartibga solinadi.

Eslatma: ushbu matn namunaviy hamkorlik shartnomasi bo'lib, joriy qonunchilikka to'liq moslashtirish uchun yurist bilan maslahatlashish tavsiya etiladi."""


class ContractSettings(models.Model):
    """Singleton: haydovchi shartnomasi matni. Matn o'zgartirilsa versiya avtomatik
    oshadi va barcha haydovchilar shartnomani qayta imzolashi so'raladi."""
    title   = models.CharField(max_length=255, default='Haydovchi shartnomasi', verbose_name='Sarlavha')
    content = models.TextField(default=DEFAULT_CONTRACT_TEXT, verbose_name='Shartnoma matni')
    version = models.PositiveIntegerField(default=1, verbose_name='Versiya')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        try:
            old = ContractSettings.objects.get(pk=1)
            if old.content != self.content or old.title != self.title:
                self.version = old.version + 1
        except ContractSettings.DoesNotExist:
            pass
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'{self.title} (v{self.version})'

    class Meta:
        verbose_name = 'Shartnoma sozlamalari'
        verbose_name_plural = 'Shartnoma sozlamalari'


class DriverContractSignature(models.Model):
    """Haydovchi ma'lum bir shartnoma versiyasini imzolagani haqidagi yozuv."""
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='contract_signatures')
    version    = models.PositiveIntegerField()
    full_name  = models.CharField(max_length=255, verbose_name="Imzolagan payt to'liq ismi")
    signature  = models.ImageField(upload_to='signatures/', verbose_name="Imzo rasmi")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signed_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.driver.full_name} — v{self.version} ({self.signed_at:%d.%m.%Y})'

    class Meta:
        verbose_name = "Shartnoma imzosi"
        verbose_name_plural = "Shartnoma imzolari"
        constraints = [
            models.UniqueConstraint(fields=['driver', 'version'], name='unique_driver_contract_version'),
        ]
        ordering = ['-signed_at']


class FlyerVoucher(models.Model):
    """Reklama flayeridagi maxfiy tekshirish kodi — soxta (nusxa ko'chirilgan)
    flayerlarni aniqlash uchun. Har bir chop etilgan flayerda o'ziga xos kod
    bo'ladi; admin panelda kodni kiritib tekshirish va haydovchiga balans
    qo'shilganda 'ishlatilgan' deb belgilash mumkin."""
    code       = models.CharField(max_length=12, unique=True, db_index=True, verbose_name='Kod')
    amount     = models.DecimalField(max_digits=10, decimal_places=0, default=3000, verbose_name="Chegirma summasi")
    batch_note = models.CharField(max_length=100, blank=True, default='', verbose_name='Partiya izohi')
    owner_driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_vouchers',
                                      verbose_name='Vizitka egasi', help_text="Vizitka chop etilganda shu haydovchiga biriktirilgan bo'lsa")
    is_used    = models.BooleanField(default=False, verbose_name='Ishlatilgan')
    used_at    = models.DateTimeField(null=True, blank=True)
    used_by_driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='flyer_vouchers')
    verified_by    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'Flayer kuponi'
        verbose_name_plural = 'Flayer kuponlari'
        ordering = ['-created_at']


class VizitkaRewardLog(models.Model):
    """Haftalik 'Mijoz olib kel' vizitka reytingida g'olib bo'lgan haydovchiga
    bonus berilgani haqidagi yozuv — bitta haydovchiga bitta hafta uchun faqat
    bir marta bonus berilishini kafolatlaydi (UniqueConstraint orqali)."""
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vizitka_rewards')
    week_start = models.DateField(verbose_name='Hafta boshi')
    voucher_count = models.PositiveIntegerField(default=0, verbose_name="Shu hafta tarqatilgan vizitkalar soni")
    amount     = models.DecimalField(max_digits=10, decimal_places=0, default=100000, verbose_name='Bonus summasi')
    given_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    given_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver.full_name} — {self.week_start}"

    class Meta:
        verbose_name = 'Vizitka reytingi bonusi'
        verbose_name_plural = 'Vizitka reytingi bonuslari'
        constraints = [
            models.UniqueConstraint(fields=['driver', 'week_start'], name='unique_driver_vizitka_reward_per_week'),
        ]
        ordering = ['-week_start']


class Task(models.Model):
    """Admin panel uchun ichki vazifalar taxtasi (rejada / bajarilmoqda / bajarildi)."""
    STATUS_TODO = 'todo'
    STATUS_DOING = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_TODO,  'Rejada'),
        (STATUS_DOING, 'Bajarilmoqda'),
        (STATUS_DONE,  'Bajarildi'),
    ]

    title       = models.CharField(max_length=255, verbose_name='Vazifa')
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_TODO)
    created_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Vazifa'
        verbose_name_plural = 'Vazifalar'
        ordering = ['-created_at']


class LegalDocument(models.Model):
    """Kompaniyaning rasmiy hujjatlari (litsenziya, guvohnoma va h.k.) —
    kompaniya qonuniy ishlayotganini tasdiqlash va muddati tugashini
    kuzatib borish uchun."""
    TYPE_LICENSE     = 'license'
    TYPE_CERTIFICATE = 'certificate'
    TYPE_OTHER       = 'other'
    TYPE_CHOICES = (
        (TYPE_LICENSE,     'Litsenziya'),
        (TYPE_CERTIFICATE, 'Guvohnoma'),
        (TYPE_OTHER,       'Boshqa hujjat'),
    )

    title       = models.CharField(max_length=255, verbose_name='Hujjat nomi')
    doc_type    = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_LICENSE, verbose_name='Turi')
    number      = models.CharField(max_length=100, blank=True, default='', verbose_name='Hujjat raqami')
    file        = models.FileField(upload_to='legal_docs/', verbose_name='Fayl')
    issued_at   = models.DateField(null=True, blank=True, verbose_name='Berilgan sana')
    expires_at  = models.DateField(null=True, blank=True, verbose_name='Amal qilish muddati', help_text='Muddatsiz bo\'lsa bo\'sh qoldiring')
    notes       = models.TextField(blank=True, default='', verbose_name='Izoh')
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Yuklagan')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"

    class Meta:
        verbose_name = 'Yuridik hujjat'
        verbose_name_plural = 'Yuridik hujjatlar'
        ordering = ['-created_at']


class SecurityIncident(models.Model):
    """Kutilmagan jiddiy holatlar (tuhmat, shantaj, yuridik nizolar va h.k.)
    ro'yxati — bunday voqealar operator e'tiboridan chetda qolib, kompaniyaga
    huquqiy/obro' zarari yetkazmasligi uchun kuzatib va hal qilib boriladi."""
    TYPE_DEFAMATION = 'defamation'
    TYPE_BLACKMAIL  = 'blackmail'
    TYPE_LEGAL      = 'legal'
    TYPE_OTHER      = 'other'
    TYPE_CHOICES = (
        (TYPE_DEFAMATION, "Tuhmat / obro'ga putur"),
        (TYPE_BLACKMAIL,  'Shantaj / tahdid'),
        (TYPE_LEGAL,      'Yuridik nizo / sud ishi'),
        (TYPE_OTHER,      'Boshqa'),
    )

    STATUS_OPEN     = 'open'
    STATUS_PROGRESS = 'investigating'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = (
        (STATUS_OPEN,     'Ochiq'),
        (STATUS_PROGRESS, 'Tekshirilmoqda'),
        (STATUS_RESOLVED, 'Hal qilindi'),
    )

    title           = models.CharField(max_length=255, verbose_name='Qisqa tavsif')
    incident_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER, verbose_name='Turi')
    description     = models.TextField(verbose_name='Batafsil tavsif')
    related_driver  = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='security_incidents', verbose_name='Aloqador haydovchi')
    related_client  = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='security_incidents', verbose_name='Aloqador mijoz')
    evidence        = models.FileField(upload_to='security_evidence/', blank=True, null=True, verbose_name='Dalil (fayl/skrinshot)')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, verbose_name='Holati')
    resolution_note = models.TextField(blank=True, default='', verbose_name='Hal qilish izohi')
    created_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reported_incidents', verbose_name='Kim ro\'yxatga oldi')
    created_at      = models.DateTimeField(auto_now_add=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Xavfsizlik voqeasi"
        verbose_name_plural = "Xavfsizlik voqealari"
        ordering = ['-created_at']


class Region(models.Model):
    """Viloyat (yoki Qoraqalpog'iston Respublikasi / Toshkent shahri) —
    O'zbekiston bo'ylab manzillarni ajratish/filtrlash uchun eng yuqori
    daraja. Ro'yxat barqaror bo'lgani uchun bir martalik data-migratsiya
    orqali 14 tasi oldindan to'ldiriladi (Manzillar bo'limida operator
    qo'lda kiritmasin degan g'oyaning davomi)."""
    name  = models.CharField(max_length=100, unique=True, verbose_name='Nomi')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Viloyat'
        verbose_name_plural = 'Viloyatlar'
        ordering = ['order', 'name']


class District(models.Model):
    """Tuman/shahar — bitta Region'ga tegishli. Diqqat: bu ro'yxat
    OLDINDAN TO'LDIRILMAYDI (viloyatlardan farqli) — O'zbekiston bo'ylab
    200 dan ortiq tuman bor va ularni xotiradan aniq sanab chiqish xato
    ehtimolini oshiradi; operator o'z hududidagi tumanlarni "Viloyatlar"
    bo'limidan bir martalik qo'shib qo'yadi."""
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts', verbose_name='Viloyat')
    name   = models.CharField(max_length=100, verbose_name='Nomi')

    def __str__(self):
        return f'{self.name} ({self.region.name})'

    class Meta:
        verbose_name = 'Tuman'
        verbose_name_plural = 'Tumanlar'
        unique_together = [('region', 'name')]
        ordering = ['region__order', 'name']


class SavedAddress(models.Model):
    """Tez-tez ishlatiladigan manzillar — admin xaritadan nuqta tanlab, nom
    berib saqlaydi (Manzillar bo'limi). Yangi buyurtma oynasida tezkor
    tanlash uchun chiqadi — Yandex qidiruv ishlamasa ham manzilni tez
    kiritish imkonini beradi."""
    name        = models.CharField(max_length=100, verbose_name='Nomi', help_text="Masalan: Bozor, Aeroport, Markaziy stansiya")
    address     = models.CharField(max_length=255, blank=True, default='', verbose_name='Manzil matni')
    lat         = models.FloatField(verbose_name='Kenglik')
    lng         = models.FloatField(verbose_name='Uzunlik')
    district    = models.ForeignKey(District, null=True, blank=True, on_delete=models.SET_NULL, related_name='addresses', verbose_name='Tuman')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='Ishlatilgan soni')
    created_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Qo'shgan")
    created_at  = models.DateTimeField(auto_now_add=True)
    auto_created = models.BooleanField(default=False, verbose_name="Avtomatik yaratilgan", help_text="Operator qo'lda emas, haydovchi shu nuqtada turgani sababli tizim tomonidan avtomatik yaratilgan")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Tezkor manzil'
        verbose_name_plural = 'Tezkor manzillar'
        ordering = ['-usage_count', 'name']


class AddressQueueEntry(models.Model):
    """Haydovchi biror SavedAddress (masalan bozor, aeroport) radiusiga
    kirganda avtomatik yaratiladi, chiqib ketganda yopiladi (`left_at`) —
    kim birinchi kelgan bo'lsa (eng erta `joined_at`), o'sha manzilga
    tushgan buyurtma birinchi navbatda o'shanga taklif qilinadi (taksi
    bekati navbati kabi), oddiy "eng yaqin/adolatli" hisob-kitobidan
    mustaqil ravishda."""
    address    = models.ForeignKey(SavedAddress, on_delete=models.CASCADE, related_name='queue_entries', verbose_name="Manzil")
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='address_queue_entries', verbose_name="Haydovchi")
    joined_at  = models.DateTimeField(auto_now_add=True, verbose_name="Navbatga kirgan vaqt")
    left_at    = models.DateTimeField(null=True, blank=True, verbose_name="Navbatdan chiqqan vaqt")

    def __str__(self):
        return f"{self.driver} @ {self.address} ({'faol' if self.left_at is None else 'chiqqan'})"

    class Meta:
        ordering = ['joined_at']
        verbose_name = "Manzil navbati yozuvi"
        verbose_name_plural = "Manzil navbati yozuvlari"
        indexes = [
            models.Index(fields=['address', 'left_at']),
            models.Index(fields=['driver', 'left_at']),
        ]


class Employee(models.Model):
    """Kompaniyaning ichki hodimi (dispetcher, buxgalter, texnik xizmat va
    h.k.) — Driver/Client'dan farqli, taksi xizmatining o'zida ishlaydi.
    Operator panelidagi 'Hodimlar' bo'limida boshqariladi: profil, unga
    biriktirilgan vazifalar (EmployeeTask), smena jadvali (EmployeeShift)
    va davomat (EmployeeAttendance) shu modelga bog'lanadi."""
    full_name  = models.CharField(max_length=255, verbose_name="F.I.Sh.")
    position   = models.CharField(max_length=100, verbose_name='Lavozimi', help_text="Masalan: Dispetcher, Buxgalter, Texnik xizmat")
    phone      = models.CharField(max_length=20, blank=True, default='', verbose_name='Telefon raqami')
    photo      = models.ImageField(upload_to='employees/', blank=True, null=True, verbose_name='Rasm')
    hire_date  = models.DateField(default=timezone.localdate, verbose_name='Ishga qabul qilingan sana')
    is_active  = models.BooleanField(default=True, verbose_name='Faol')
    notes      = models.TextField(blank=True, default='', verbose_name='Izoh')
    user       = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile', verbose_name='Tizim akkaunti (ixtiyoriy)')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.position})"

    class Meta:
        verbose_name = 'Hodim'
        verbose_name_plural = 'Hodimlar'
        ordering = ['full_name']


class EmployeeTask(models.Model):
    """Muayyan hodimga biriktirilgan aniq topshiriq — Tizim panelidagi
    umumiy Task (kanban, hech kimga bog'lanmagan) dan farqli, doim bitta
    Employee'ga tegishli."""
    STATUS_TODO     = 'todo'
    STATUS_PROGRESS = 'in_progress'
    STATUS_DONE     = 'done'
    STATUS_CHOICES = (
        (STATUS_TODO,     'Bajarilishi kerak'),
        (STATUS_PROGRESS, 'Jarayonda'),
        (STATUS_DONE,     'Bajarildi'),
    )

    employee     = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks', verbose_name='Hodim')
    title        = models.CharField(max_length=255, verbose_name='Vazifa')
    description  = models.TextField(blank=True, default='', verbose_name='Tavsif')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, verbose_name='Holati')
    due_date     = models.DateField(null=True, blank=True, verbose_name='Muddati')
    assigned_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Kim topshirdi')
    created_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} — {self.employee.full_name}"

    class Meta:
        verbose_name = 'Hodim vazifasi'
        verbose_name_plural = 'Hodim vazifalari'
        ordering = ['status', '-created_at']


class EmployeeShift(models.Model):
    """Hodimning haftalik smena jadvali — har hafta kuni uchun bitta yozuv;
    biror kun uchun yozuv bo'lmasa, o'sha kun dam olish hisoblanadi."""
    WEEKDAY_CHOICES = (
        (0, 'Dushanba'), (1, 'Seshanba'), (2, 'Chorshanba'), (3, 'Payshanba'),
        (4, 'Juma'), (5, 'Shanba'), (6, 'Yakshanba'),
    )

    employee   = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='shifts', verbose_name='Hodim')
    weekday    = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES, verbose_name='Hafta kuni')
    start_time = models.TimeField(verbose_name='Boshlanish vaqti')
    end_time   = models.TimeField(verbose_name='Tugash vaqti')

    def __str__(self):
        return f"{self.employee.full_name} — {self.get_weekday_display()} {self.start_time}-{self.end_time}"

    class Meta:
        verbose_name = 'Smena'
        verbose_name_plural = 'Smena jadvali'
        unique_together = ('employee', 'weekday')
        ordering = ['weekday']


class EmployeeAttendance(models.Model):
    """Hodimning kunlik davomati — kelgan/ketgan vaqti operator tomonidan
    tugma orqali (bugungi kun) yoki qo'lda (istalgan sana uchun) belgilanadi."""
    STATUS_PRESENT = 'present'
    STATUS_LATE    = 'late'
    STATUS_ABSENT  = 'absent'
    STATUS_CHOICES = (
        (STATUS_PRESENT, 'Keldi'),
        (STATUS_LATE,    'Kech qoldi'),
        (STATUS_ABSENT,  'Kelmadi'),
    )

    employee  = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records', verbose_name='Hodim')
    date      = models.DateField(verbose_name='Sana')
    check_in  = models.DateTimeField(null=True, blank=True, verbose_name='Kelgan vaqti')
    check_out = models.DateTimeField(null=True, blank=True, verbose_name='Ketgan vaqti')
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PRESENT, verbose_name='Holati')
    note      = models.CharField(max_length=255, blank=True, default='', verbose_name='Izoh')

    def __str__(self):
        return f"{self.employee.full_name} — {self.date}"

    class Meta:
        verbose_name = 'Davomat yozuvi'
        verbose_name_plural = 'Davomat'
        unique_together = ('employee', 'date')
        ordering = ['-date']


class CallRecording(models.Model):
    """Qo'ng'iroq-kuzatuvchi Android ilova operator telefoniga kelgan
    qo'ng'iroqning audio yozuvini shu yerga yuklaydi (agar qurilma/OS versiyasi
    yozib olishga ruxsat bersa — Android 10+ da uchinchi tomon ilovalar uchun
    tizim darajasida cheklangan, shuning uchun ba'zi qurilmalarda ishlamasligi
    mumkin)."""
    phone_number = models.CharField(max_length=20, blank=True, default='', db_index=True, verbose_name="Telefon raqami")
    audio        = models.FileField(upload_to='call_recordings/%Y/%m/', verbose_name="Audio fayl")
    duration_sec = models.PositiveIntegerField(null=True, blank=True, verbose_name="Davomiyligi (soniya)")
    created_at   = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Vaqt")

    def __str__(self):
        phone = self.phone_number or "noma'lum"
        return f"{phone} — {self.created_at:%d.%m.%Y %H:%M}"

    class Meta:
        verbose_name = "Qo'ng'iroq yozuvi"
        verbose_name_plural = "Qo'ng'iroq yozuvlari"
        ordering = ['-created_at']


class OperatorPushToken(models.Model):
    """Native Android operator ilovasi (vijdon_operator_native, /api/operatorapp/)
    o'rnatgan FCM tokeni — yangi buyurtma/to'lov so'rovi/SOS kabi hodisalar
    haqida operatorlarga push yuborish uchun. Bitta operator bir nechta
    qurilmada kirishi mumkin, shu sabab Driver.fcm_token'dagidek User'ga
    bevosita maydon sifatida emas, alohida jadval sifatida saqlanadi."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='operator_push_tokens', verbose_name='Operator')
    fcm_token  = models.TextField(verbose_name='FCM Token')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yangilangan vaqt')

    def __str__(self):
        return f"{self.user.username} — {self.updated_at:%d.%m.%Y %H:%M}"

    class Meta:
        verbose_name = 'Operator push tokeni'
        verbose_name_plural = 'Operator push tokenlari'
        unique_together = ('user', 'fcm_token')


class SmsGatewayToken(models.Model):
    """SMS-shlyuz Android ilovasi (vijdon_sms_gateway) o'rnatilgan
    telefon(lar)ning FCM tokeni — navbatga yangi SMS qo'shilganda shu
    qurilma(lar)ga darhol signal yuborish uchun (`taxi/utils.py:
    notify_sms_gateway`). Bir nechta qurilma bo'lishi mumkin — shunda
    yuk bir nechta SIM karta orasida tabiiy taqsimlanadi (har biri
    navbatdan birinchi bo'sh xabarni oladi)."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_gateway_tokens', verbose_name='Foydalanuvchi')
    fcm_token  = models.TextField(verbose_name='FCM Token')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yangilangan vaqt')

    def __str__(self):
        return f"{self.user.username} — {self.updated_at:%d.%m.%Y %H:%M}"

    class Meta:
        verbose_name = 'SMS-shlyuz push tokeni'
        verbose_name_plural = 'SMS-shlyuz push tokenlari'
        unique_together = ('user', 'fcm_token')


class SmsGatewayMessage(models.Model):
    """`SmsSettings.provider == PROVIDER_LOCAL_GATEWAY` bo'lganda
    `taxi/utils.py: send_sms()` Eskiz.uz o'rniga shu navbatga yozadi —
    vijdon_sms_gateway ilovasi o'rnatilgan telefon(lar) buni o'qib
    (push + zaxira sifatida polling orqali), o'z SIM kartasi orqali
    haqiqiy SMS'ni yuboradi va natijani (`sent`/`failed`) qaytaradi."""
    STATUS_PENDING = 'pending'
    # Bir nechta SMS-shlyuz qurilmasi bo'lsa, ikkitasi HAM bir xil xabarni
    # "pending" holatida ko'rib, ikkalasi ham yuborib yuborishi mumkin edi
    # (poyga sharoiti). Shu sabab `pending/` so'ralganda xabar DARHOL shu
    # oraliq holatga o'tkaziladi (kim so'ragan bo'lsa, shu "band qilib
    # oladi") — boshqa qurilma uni endi ko'rmaydi.
    STATUS_SENDING = 'sending'
    STATUS_SENT    = 'sent'
    STATUS_FAILED  = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_SENDING, 'Yuborilmoqda'),
        (STATUS_SENT,    'Yuborildi'),
        (STATUS_FAILED,  'Xato'),
    )
    phone_number = models.CharField(max_length=20, verbose_name='Telefon raqami')
    text         = models.TextField(verbose_name='Matn')
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Holati')
    error        = models.CharField(max_length=255, blank=True, default='', verbose_name='Xato matni')
    sent_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_sms_messages', verbose_name='Yuborgan qurilma')
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')
    claimed_at   = models.DateTimeField(null=True, blank=True, verbose_name='Band qilingan vaqti')
    resolved_at  = models.DateTimeField(null=True, blank=True, verbose_name='Hal qilingan vaqti')

    def __str__(self):
        return f"{self.phone_number} — {self.get_status_display()}"

    @staticmethod
    def status_pending_or_stale_q(stale_cutoff):
        """`taxi/smsgatewayapp_views.py: pending()` uchun — hali hech kim
        band qilmagan (`pending`) YOKI biror qurilma band qilib, lekin
        javob bermay qo'ygan (`sending` + `claimed_at` juda eski)
        xabarlarni bir xilda tanlaydi."""
        return (
            models.Q(status=SmsGatewayMessage.STATUS_PENDING)
            | models.Q(status=SmsGatewayMessage.STATUS_SENDING, claimed_at__lt=stale_cutoff)
        )

    class Meta:
        verbose_name = 'SMS-shlyuz xabari'
        verbose_name_plural = 'SMS-shlyuz xabarlari'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'])]


class SmsGatewayIncoming(models.Model):
    """vijdon_sms_gateway ilovasi o'rnatilgan telefonning SIM kartasiga
    KELGAN SMS'lar (mijoz/haydovchi yuborilgan SMS'ga javob yozsa) —
    Eskiz/alfa-nomdan farqli, real SIM raqamiga javob yozish mumkin,
    shu sabab operator buni panelda ko'rishi kerak."""
    phone_number = models.CharField(max_length=20, verbose_name='Kimdan')
    text         = models.TextField(verbose_name='Matn')
    received_at  = models.DateTimeField(verbose_name="Qurilmada qabul qilingan vaqt")
    device       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='received_sms_messages', verbose_name='Qaysi qurilma')
    is_read      = models.BooleanField(default=False, verbose_name="O'qilgan")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name='Serverga tushgan vaqt')

    def __str__(self):
        return f"{self.phone_number}: {self.text[:30]}"

    class Meta:
        verbose_name = 'Kelgan SMS'
        verbose_name_plural = 'Kelgan SMS xabarlari'
        ordering = ['-received_at']


class Expense(models.Model):
    """Kompaniyaning operatsion xarajati (yoqilg'i, maosh, ijaraga, SMS/aloqa
    xizmatlari va h.k.) — Moliya bo'limidagi "sof foyda" (komissiya
    daromadi − xarajatlar) hisobiga kiradi."""
    CATEGORY_FUEL          = 'fuel'
    CATEGORY_SALARY        = 'salary'
    CATEGORY_BONUS         = 'bonus'
    CATEGORY_RENT          = 'rent'
    CATEGORY_MARKETING     = 'marketing'
    CATEGORY_MAINTENANCE   = 'maintenance'
    CATEGORY_COMMUNICATION = 'communication'
    CATEGORY_OTHER         = 'other'
    CATEGORY_CHOICES = (
        (CATEGORY_FUEL,          "Yoqilg'i"),
        (CATEGORY_SALARY,        'Xodimlar maoshi'),
        (CATEGORY_BONUS,         "Haydovchi bonusi/mukofot"),
        (CATEGORY_RENT,          'Ijaraga/ofis'),
        (CATEGORY_MARKETING,     'Reklama/marketing'),
        (CATEGORY_MAINTENANCE,   "Texnik xizmat/ta'mirlash"),
        (CATEGORY_COMMUNICATION, 'SMS/aloqa xizmatlari'),
        (CATEGORY_OTHER,         'Boshqa'),
    )

    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER, verbose_name='Turi')
    amount      = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Summa')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='Izoh')
    receipt     = models.ImageField(upload_to='expense_receipts/', blank=True, null=True, verbose_name='Chek/hujjat')
    spent_at    = models.DateField(default=timezone.localdate, verbose_name='Sana')
    created_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='expenses', verbose_name='Kim kiritdi')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} UZS ({self.spent_at})"

    class Meta:
        verbose_name = 'Xarajat'
        verbose_name_plural = 'Xarajatlar'
        ordering = ['-spent_at', '-created_at']


class Goal(models.Model):
    """Kompaniya/jamoa maqsadi — muddati (deadline) va o'lchov turi bilan.
    Ba'zi turlar (`METRIC_CUSTOM` bundan mustasno) joriy natijani DB'dan
    real vaqtda hisoblab beradi — alohida "progress" maydonini qo'lda
    yangilab yurish shart emas. Holat (`status`) `utils.check_goals()`
    orqali (scheduler tick'ida va sahifa ochilganda) avtomatik yangilanadi:
    maqsadga erishilsa "Erishildi", muddat o'tib ketsa "Muddati o'tdi"."""
    METRIC_REVENUE       = 'revenue'
    METRIC_ORDERS        = 'orders'
    METRIC_NEW_DRIVERS   = 'new_drivers'
    METRIC_ACTIVE_CLIENTS = 'active_clients'
    METRIC_CUSTOM        = 'custom'
    METRIC_CHOICES = (
        (METRIC_REVENUE,        "Komissiya daromadi (so'm)"),
        (METRIC_ORDERS,         'Yakunlangan buyurtmalar soni'),
        (METRIC_NEW_DRIVERS,    "Yangi ro'yxatdan o'tgan haydovchilar"),
        (METRIC_ACTIVE_CLIENTS, 'Faol mijozlar soni (buyurtma bergan)'),
        (METRIC_CUSTOM,         "Qo'lda kiritiladi"),
    )

    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED    = 'failed'
    STATUS_CHOICES = (
        (STATUS_ACTIVE,    'Faol'),
        (STATUS_COMPLETED, 'Erishildi'),
        (STATUS_FAILED,    "Muddati o'tdi"),
    )

    title        = models.CharField(max_length=200, verbose_name='Nomi')
    description  = models.TextField(blank=True, default='', verbose_name='Tavsif')
    metric       = models.CharField(max_length=20, choices=METRIC_CHOICES, default=METRIC_CUSTOM, verbose_name="O'lchov turi")
    target_value = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Maqsad qiymati')
    manual_value = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Joriy qiymat (qo'lda)",
                                        help_text="Faqat \"Qo'lda kiritiladi\" turi uchun — boshqa turlar avtomatik hisoblanadi")
    start_date   = models.DateField(default=timezone.localdate, verbose_name='Boshlanish sanasi')
    deadline     = models.DateField(verbose_name='Tugash muddati')
    status       = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name='Holati')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Erishilgan vaqt')
    notified_completed     = models.BooleanField(default=False)
    notified_deadline_soon = models.BooleanField(default=False)
    created_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals', verbose_name='Kim yaratdi')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Maqsad'
        verbose_name_plural = 'Maqsadlar'
        ordering = ['status', 'deadline']

    def __str__(self):
        return self.title

    def current_value(self):
        """Maqsad turiga qarab joriy natijani hisoblaydi — `custom` bo'lsa
        qo'lda kiritilgan qiymat, aks holda tegishli modeldan real vaqtda."""
        from django.utils import timezone as tz

        if self.metric == self.METRIC_CUSTOM:
            return self.manual_value

        end = min(tz.localdate(), self.deadline)
        if end < self.start_date:
            return 0

        if self.metric == self.METRIC_REVENUE:
            from django.db.models import Sum
            return Order.objects.filter(
                status='completed', created_at__date__gte=self.start_date, created_at__date__lte=end,
            ).aggregate(s=Sum('commission'))['s'] or 0
        if self.metric == self.METRIC_ORDERS:
            return Order.objects.filter(
                status='completed', created_at__date__gte=self.start_date, created_at__date__lte=end,
            ).count()
        if self.metric == self.METRIC_NEW_DRIVERS:
            return Driver.objects.filter(
                registered_at__date__gte=self.start_date, registered_at__date__lte=end,
            ).count()
        if self.metric == self.METRIC_ACTIVE_CLIENTS:
            return Order.objects.filter(
                status='completed', created_at__date__gte=self.start_date, created_at__date__lte=end,
            ).values('client').distinct().count()
        return 0

    def progress_pct(self):
        if not self.target_value:
            return 0
        pct = float(self.current_value()) / float(self.target_value) * 100
        return min(round(pct, 1), 100)

    def days_left(self):
        from django.utils import timezone as tz
        return (self.deadline - tz.localdate()).days


class OperatorPreference(models.Model):
    """Operator/admin akkaunti uchun panelda saqlanadigan shaxsiy
    sozlamalar — hozircha faqat "Yangi buyurtma" oynasidagi "Tezkor"
    manzil filtri (oxirgi tanlangan viloyat/tuman). Har bir akkaunt
    uchun alohida (1 ta User = 1 ta yozuv), shu sabab bitta kompyuterda
    bir necha operator alternativ kirib-chiqsa ham, har biriga o'zining
    oxirgi tanlovi qaytadi — brauzer/qurilmaga emas, akkauntga bog'liq."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='panel_preference', verbose_name='Foydalanuvchi')
    quick_address_region = models.ForeignKey('Region', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Tezkor manzil — oxirgi viloyat')
    quick_address_district = models.ForeignKey('District', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Tezkor manzil — oxirgi tuman')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Operator sozlamasi'
        verbose_name_plural = 'Operator sozlamalari'

    def __str__(self):
        return f'{self.user.username} sozlamalari'
