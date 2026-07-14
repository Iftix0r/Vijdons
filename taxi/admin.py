from django.contrib import admin
from .models import Driver, Client, Order


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'phone_number', 'car_model', 'car_number', 'approval_status', 'is_active', 'is_on_duty', 'registered_at')
    search_fields = ('full_name', 'phone_number', 'car_number')
    list_filter   = ('is_active', 'approval_status', 'is_on_duty')
    list_editable = ('approval_status', 'is_active')
    readonly_fields = ('registered_at',)
    actions = ['approve_drivers', 'reject_drivers']

    @admin.action(description='Tanlangan haydovchilarni tasdiqlash')
    def approve_drivers(self, request, queryset):
        for driver in queryset:
            driver.approval_status = Driver.APPROVAL_APPROVED
            driver.is_active = True
            if driver.user:
                driver.user.is_active = True
                driver.user.save(update_fields=['is_active'])
            driver.save(update_fields=['approval_status', 'is_active'])
        self.message_user(request, f'{queryset.count()} ta haydovchi tasdiqlandi.')

    @admin.action(description='Tanlangan haydovchilarni rad etish')
    def reject_drivers(self, request, queryset):
        queryset.update(approval_status=Driver.APPROVAL_REJECTED, is_active=False)
        self.message_user(request, f'{queryset.count()} ta haydovchi rad etildi.')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'phone_number')
    search_fields = ('full_name', 'phone_number')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display    = ('id', 'client', 'driver', 'from_address', 'to_address', 'status', 'created_at')
    list_filter     = ('status', 'created_at')
    search_fields   = ('client__phone_number', 'driver__full_name', 'from_address', 'to_address')
    list_editable   = ('status', 'driver')
    autocomplete_fields = ['client', 'driver']

