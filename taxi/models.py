from django.db import models
from django.contrib.auth.models import User


class Driver(models.Model):
    APPROVAL_PENDING  = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_CHOICES = (
        (APPROVAL_PENDING,  'Kutilmoqda'),
        (APPROVAL_APPROVED, 'Tasdiqlangan'),
        (APPROVAL_REJECTED, 'Rad etilgan'),
    )

    user         = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='driver_profile')
    full_name    = models.CharField(max_length=255, verbose_name="Haydovchi ismi")
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    car_model    = models.CharField(max_length=100, verbose_name="Mashina modeli")
    car_number   = models.CharField(max_length=20, verbose_name="Mashina raqami")
    is_active    = models.BooleanField(default=True, verbose_name="Faol")
    # Registration / approval
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_PENDING,
        verbose_name="Tasdiqlash holati"
    )
    fcm_token    = models.TextField(blank=True, null=True, verbose_name="FCM Token")
    is_on_duty   = models.BooleanField(default=False, verbose_name="Ish navbatida")
    latitude     = models.FloatField(null=True, blank=True, verbose_name="Kenglik (Latitude)")
    longitude    = models.FloatField(null=True, blank=True, verbose_name="Uzunlik (Longitude)")
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name="Ro'yxatdan o'tgan vaqt")

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
        ('on_way',    'Yo\'lda'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    )

    client       = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders', verbose_name="Mijoz")
    driver       = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Haydovchi")
    from_address = models.CharField(max_length=255, verbose_name="Qayerdan")
    from_lat     = models.FloatField(null=True, blank=True, verbose_name="Qayerdan Kenglik (Lat)")
    from_lng     = models.FloatField(null=True, blank=True, verbose_name="Qayerdan Uzunlik (Lng)")
    to_address   = models.CharField(max_length=255, verbose_name="Qayerga")
    to_lat       = models.FloatField(null=True, blank=True, verbose_name="Qayerga Kenglik (Lat)")
    to_lng       = models.FloatField(null=True, blank=True, verbose_name="Qayerga Uzunlik (Lng)")
    distance_km  = models.FloatField(null=True, blank=True, verbose_name="Masofa (km)")
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Narxi")
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at   = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.client}"

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"

