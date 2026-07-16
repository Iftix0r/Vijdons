from django.contrib import admin
from .models import Driver, Client, Order, DriverActivityLog


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('photo_thumb', 'full_name', 'phone_number', 'car_model', 'car_number', 'approval_status', 'is_active', 'is_on_duty', 'registered_at')
    search_fields = ('full_name', 'phone_number', 'car_number')
    list_filter   = ('is_active', 'approval_status', 'is_on_duty')
    list_editable = ('approval_status', 'is_active')
    readonly_fields = ('registered_at', 'photo_thumb')
    actions = ['approve_drivers', 'reject_drivers']

    def photo_thumb(self, obj):
        from django.utils.html import format_html
        if obj.photo:
            return format_html('<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:50%">', obj.photo.url)
        return '—'
    photo_thumb.short_description = 'Rasm'

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


@admin.register(DriverActivityLog)
class DriverActivityLogAdmin(admin.ModelAdmin):
    list_display  = ('driver', 'action', 'detail', 'ip_address', 'created_at')
    list_filter   = ('action', 'created_at')
    search_fields = ('driver__full_name', 'ip_address', 'detail')
    readonly_fields = ('driver', 'action', 'detail', 'ip_address', 'user_agent', 'created_at')

