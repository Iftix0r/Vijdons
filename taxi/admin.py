from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.html import format_html
from .models import Driver, Client, Order, DriverActivityLog, GroupMessage


class DashboardAdmin(admin.AdminSite):
    site_header = 'Vijdon Taxi'
    site_title  = 'Vijdon Admin'
    index_title = 'Boshqaruv paneli'

    def index(self, request, extra_context=None):
        today = timezone.now().date()
        stats = {
            'today_orders':    Order.objects.filter(created_at__date=today).count(),
            'today_completed': Order.objects.filter(created_at__date=today, status='completed').count(),
            'today_cancelled': Order.objects.filter(created_at__date=today, status='cancelled').count(),
            'today_earned':    Order.objects.filter(created_at__date=today, status='completed').aggregate(s=Sum('price'))['s'] or 0,
            'active_drivers':  Driver.objects.filter(is_on_duty=True).count(),
            'total_drivers':   Driver.objects.filter(approval_status='approved').count(),
            'pending_orders':  Order.objects.filter(status='pending').count(),
            'active_orders':   Order.objects.filter(status__in=['accepted','on_way','arrived']).count(),
        }
        extra_context = extra_context or {}
        extra_context['dashboard_stats'] = stats
        return super().index(request, extra_context)


admin_site = DashboardAdmin(name='admin')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('photo_thumb', 'full_name', 'phone_number', 'car_model', 'car_number', 'balance_display', 'approval_status', 'is_active', 'is_on_duty', 'registered_at')
    search_fields = ('full_name', 'phone_number', 'car_number')
    list_filter   = ('is_active', 'approval_status', 'is_on_duty')
    list_editable = ('approval_status', 'is_active')
    readonly_fields = ('registered_at', 'photo_thumb')
    actions = ['approve_drivers', 'reject_drivers']

    def photo_thumb(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:50%">', obj.photo.url)
        return '—'
    photo_thumb.short_description = 'Rasm'

    def balance_display(self, obj):
        color = '#FF3B30' if obj.balance < 0 else '#34C759'
        return format_html('<b style="color:{}">{:,} so\'m</b>', color, int(obj.balance))
    balance_display.short_description = 'Balans'

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


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display  = ('driver', 'short_text', 'has_audio', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('driver__full_name', 'driver__car_number', 'text')
    readonly_fields = ('driver', 'text', 'audio', 'created_at')

    def short_text(self, obj):
        return obj.text[:60] or '🎤 Ovozli xabar'
    short_text.short_description = 'Xabar'

    def has_audio(self, obj):
        return format_html('<span style="color:#34C759">🎤 Ha</span>') if obj.audio else '—'
    has_audio.short_description = 'Audio'

