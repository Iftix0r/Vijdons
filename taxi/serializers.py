from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Driver, Order, Client


class DriverRegisterSerializer(serializers.Serializer):
    """Step 1: haydovchi ro'yxatdan o'tish."""
    full_name    = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=20)
    car_model    = serializers.CharField(max_length=100)
    car_number   = serializers.CharField(max_length=20)
    password     = serializers.CharField(write_only=True, min_length=6)

    def validate_phone_number(self, value):
        if Driver.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        phone    = validated_data['phone_number']
        # create django user with phone as username
        user = User.objects.create_user(username=phone, password=password)
        driver = Driver.objects.create(
            user=user,
            approval_status=Driver.APPROVAL_PENDING,
            is_active=False,
            **validated_data,
        )
        return driver


class DriverLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password     = serializers.CharField(write_only=True)


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Driver
        fields = [
            'id', 'full_name', 'phone_number', 'car_model', 'car_number',
            'is_active', 'is_on_duty', 'approval_status', 'registered_at', 'balance'
        ]
        read_only_fields = ['approval_status', 'registered_at']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Client
        fields = ['id', 'full_name', 'phone_number']


class OrderSerializer(serializers.ModelSerializer):
    client_name  = serializers.CharField(source='client.full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    driver_name  = serializers.CharField(source='driver.full_name', read_only=True, allow_null=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'client_name', 'client_phone', 'driver_name',
            'from_address', 'to_address', 'price', 'commission', 'distance_km',
            'payment_type', 'note',
            'status', 'status_label', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        driver = None
        if request and hasattr(request.user, 'driver_profile'):
            driver = request.user.driver_profile
        
        # Hide contact details if the order is not accepted by this driver
        if instance.status == 'pending' or (instance.driver and driver and instance.driver.id != driver.id):
            data['client_phone'] = '+998 ** *** ** **'
            data['client_name'] = 'Mijoz'
            
        return data
