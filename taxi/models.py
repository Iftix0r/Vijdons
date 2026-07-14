from django.db import models
from django.contrib.auth.models import User

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255, verbose_name="Haydovchi ismi")
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    car_model = models.CharField(max_length=100, verbose_name="Mashina modeli")
    car_number = models.CharField(max_length=20, verbose_name="Mashina raqami")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    
    def __str__(self):
        return f"{self.full_name} ({self.car_number})"
        
    class Meta:
        verbose_name = "Haydovchi"
        verbose_name_plural = "Haydovchilar"

class Client(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="Mijoz ismi", null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    
    def __str__(self):
        return self.full_name or self.phone_number

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    )
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders', verbose_name="Mijoz")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Haydovchi")
    from_address = models.CharField(max_length=255, verbose_name="Qayerdan")
    to_address = models.CharField(max_length=255, verbose_name="Qayerga")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Narxi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")
    
    def __str__(self):
        return f"Buyurtma #{self.id} - {self.client}"

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
