"""
Serializerlar — native Android operator ilovasi uchun (/api/operatorapp/).
`taxi/driverapp_serializers.py`dagi bilan bir xil naqsh, lekin bu yerda
mijoz/haydovchi ma'lumotlari HECH QACHON maskalanmaydi — operator har doim
to'liq ma'lumotni ko'rishi kerak (haydovchi ilovasidagi `_masked()` mantig'i
bu yerda yo'q)."""
from rest_framework import serializers

from .models import Driver, Order, DispatchAttempt


class OperatorAppDriverSerializer(serializers.ModelSerializer):
    car_type_display = serializers.CharField(source='get_car_type_display', read_only=True)
    approval_status_display = serializers.CharField(source='get_approval_status_display', read_only=True)
    photo_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    # `driver_list` annotatsiya qilingan queryset beradi (completed_count/
    # cancelled_count) — lekin `driver_detail`/`driver_approve` va h.k. oddiy
    # `Driver` instansida bu atributlar YO'Q, shu sabab IntegerField emas,
    # `getattr(..., None)` bilan xavfsiz o'qiydigan SerializerMethodField.
    completed_count = serializers.SerializerMethodField()
    cancelled_count = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = [
            'id', 'full_name', 'phone_number',
            'car_model', 'car_number', 'car_type', 'car_type_display',
            'is_active', 'is_on_duty', 'is_frozen', 'is_qarzdor', 'qarz_note',
            'approval_status', 'approval_status_display', 'registered_at',
            'balance', 'rating', 'trips_count', 'photo_url', 'last_seen',
            'is_online', 'completed_count', 'cancelled_count',
        ]
        read_only_fields = fields

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_is_online(self, obj):
        if not obj.last_seen:
            return False
        from django.utils import timezone
        return (timezone.now() - obj.last_seen).total_seconds() < 120

    def get_completed_count(self, obj):
        return getattr(obj, 'completed_count', None)

    def get_cancelled_count(self, obj):
        return getattr(obj, 'cancelled_count', None)


class _DispatchAttemptSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    result_label = serializers.CharField(source='get_result_display', read_only=True)

    class Meta:
        model = DispatchAttempt
        fields = ['driver_id', 'driver_name', 'distance_km', 'attempt_number', 'result', 'result_label', 'created_at', 'resolved_at']


class OperatorAppOrderSerializer(serializers.ModelSerializer):
    """Buyurtma javob shakli — client/driver ma'lumotlari to'liq (maskalanmagan),
    dispetcherlash tarixi (`dispatch_attempts`) va rad etgan haydovchilar
    (`rejected_by`) bilan — operator dispetcher taxtasini ko'rsatishi uchun."""
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    car_type_display = serializers.CharField(source='get_car_type_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)

    client_id = serializers.IntegerField(source='client.id', read_only=True)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    client_is_blocked = serializers.BooleanField(source='client.is_blocked', read_only=True)

    driver_id = serializers.IntegerField(read_only=True)
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()

    dispatched_to_id = serializers.IntegerField(read_only=True)
    dispatched_to_name = serializers.SerializerMethodField()

    rejected_by = serializers.SerializerMethodField()
    dispatch_attempts = _DispatchAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_label',
            'from_address', 'from_lat', 'from_lng',
            'to_address', 'to_lat', 'to_lng',
            'on_way_address', 'arrived_address',
            'client_id', 'client_name', 'client_phone', 'client_is_blocked',
            'driver_id', 'driver_name', 'driver_phone',
            'dispatched_to_id', 'dispatched_to_name', 'dispatched_at',
            'price', 'commission', 'distance_km',
            'payment_type', 'payment_type_display', 'car_type', 'car_type_display',
            'is_delivery', 'note', 'cancel_reason',
            'rejected_by', 'dispatch_attempts',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_driver_name(self, instance):
        return instance.driver.full_name if instance.driver else None

    def get_driver_phone(self, instance):
        return instance.driver.phone_number if instance.driver else None

    def get_dispatched_to_name(self, instance):
        return instance.dispatched_to.full_name if instance.dispatched_to else None

    def get_rejected_by(self, instance):
        return [{'id': d.id, 'full_name': d.full_name} for d in instance.rejected_by.all()]
