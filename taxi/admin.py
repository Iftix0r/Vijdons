from django.contrib import admin
from .models import Driver, Client, Order

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'car_model', 'car_number', 'is_active')
    search_fields = ('full_name', 'phone_number', 'car_number')
    list_filter = ('is_active',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number')
    search_fields = ('full_name', 'phone_number')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'driver', 'from_address', 'to_address', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('client__phone_number', 'driver__full_name', 'from_address', 'to_address')
    list_editable = ('status', 'driver')
    autocomplete_fields = ['client', 'driver']
