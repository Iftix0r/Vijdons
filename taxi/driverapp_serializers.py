"""
Serializerlar — native Android haydovchi ilovasi uchun (/api/driverapp/).
Ro'yxatdan o'tish/kirish uchun taxi/serializers.py'dagi mavjud
DriverRegisterSerializer/DriverLoginSerializer qayta ishlatiladi (aynan bir
xil maydonlar/tekshiruvlar kerak) — bu yerda faqat shu ilovaga xos, yangi
javob shakllari (profil, buyurtma — taximetr maydonlari bilan) beriladi.
"""
from rest_framework import serializers

from .models import Driver, Order


class DriverAppProfileSerializer(serializers.ModelSerializer):
    """`/me/` javobi — haydovchining o'zi haqidagi to'liq holat."""
    car_type_display = serializers.CharField(source='get_car_type_display', read_only=True)
    approval_status_display = serializers.CharField(source='get_approval_status_display', read_only=True)
    photo_url = serializers.SerializerMethodField()
    level = serializers.ReadOnlyField()

    class Meta:
        model = Driver
        fields = [
            'id', 'full_name', 'phone_number',
            'car_model', 'car_number', 'car_type', 'car_type_display',
            'is_active', 'is_on_duty', 'is_frozen',
            'approval_status', 'approval_status_display', 'registered_at',
            'balance', 'rating', 'trips_count', 'level', 'photo_url',
            'destination_mode', 'destination_lat', 'destination_lng', 'destination_address',
        ]
        read_only_fields = [
            'id', 'full_name', 'phone_number', 'car_model', 'car_number', 'car_type',
            'is_active', 'is_on_duty', 'is_frozen', 'approval_status', 'registered_at',
            'balance', 'rating', 'trips_count',
        ]

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url


class DriverAppOrderSerializer(serializers.ModelSerializer):
    """Buyurtma javob shakli — taximetr (`tmx_*`) maydonlari bilan, chunki
    ular ilova ichida masofa/narxni real vaqtda ko'rsatish uchun shart, va
    mavjud (eski) OrderSerializer (taxi/serializers.py) ularni bermaydi."""
    client_name        = serializers.SerializerMethodField()
    client_phone        = serializers.SerializerMethodField()
    status_label        = serializers.CharField(source='get_status_display', read_only=True)
    car_type_display     = serializers.CharField(source='get_car_type_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    is_dispatched        = serializers.SerializerMethodField()
    timer_sec             = serializers.SerializerMethodField()
    client_rating         = serializers.SerializerMethodField()
    client_trips_count    = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_label',
            'from_address', 'from_lat', 'from_lng',
            'to_address', 'to_lat', 'to_lng',
            'on_way_address', 'arrived_address',
            'client_name', 'client_phone', 'client_rating', 'client_trips_count',
            'price', 'commission', 'distance_km',
            'payment_type', 'payment_type_display', 'car_type', 'car_type_display',
            'note', 'is_dispatched', 'timer_sec',
            'tmx_dist_km', 'tmx_paused', 'tmx_paused_ms', 'tmx_start_time',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def _driver(self):
        return self.context.get('driver')

    def _masked(self, instance):
        driver = self._driver()
        return instance.status == 'pending' or (instance.driver_id and driver and instance.driver_id != driver.id)

    def get_client_name(self, instance):
        if self._masked(instance):
            return 'Mijoz'
        return instance.client.full_name or 'Mijoz'

    def get_client_phone(self, instance):
        if self._masked(instance):
            from .driver_views import _mask_phone
            return _mask_phone(instance.client.phone_number)
        return instance.client.phone_number

    def get_is_dispatched(self, instance):
        driver = self._driver()
        return bool(driver and instance.dispatched_to_id == driver.id)

    def get_timer_sec(self, instance):
        driver = self._driver()
        if instance.status == 'pending' and driver and instance.dispatched_to_id == driver.id and instance.dispatched_at:
            from django.utils import timezone
            from .models import TariffSettings
            timeout = TariffSettings.get().dispatch_timeout
            elapsed = (timezone.now() - instance.dispatched_at).total_seconds()
            return max(0, int(timeout - elapsed))
        return None

    def get_client_rating(self, instance):
        return float(instance.client.rating) if instance.status == 'pending' else None

    def get_client_trips_count(self, instance):
        return instance.client.trips_count if instance.status == 'pending' else None
