from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Driver, Order, Client


class DriverRegisterSerializer(serializers.Serializer):
    """Step 1: haydovchi ro'yxatdan o'tish."""
    full_name    = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=20)
    car_model    = serializers.CharField(max_length=100)
    car_number   = serializers.CharField(max_length=20)
    car_type     = serializers.ChoiceField(choices=Driver.CAR_TYPE_CHOICES, default=Driver.CAR_TYPE_LIGHT, required=False)
    password     = serializers.CharField(write_only=True, min_length=6)

    def validate_phone_number(self, value):
        # Driver.phone_number o'zi unique, lekin User.username (login uchun
        # ishlatiladigan) buni bilmaydi — agar shu raqam allaqachon boshqa
        # turdagi hisob (masalan yo'lovchi) tomonidan User sifatida band
        # qilingan bo'lsa, create_user() IntegrityError bilan qulaydi. Shu
        # sabab ikkalasini ham oldindan tekshiramiz.
        if Driver.objects.filter(phone_number=value).exists() or User.objects.filter(username=value).exists():
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
    photo_url = serializers.SerializerMethodField()

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    class Meta:
        model  = Driver
        fields = [
            'id', 'full_name', 'phone_number', 'car_model', 'car_number', 'car_type',
            'is_active', 'is_on_duty', 'approval_status', 'registered_at', 'balance',
            'photo_url',
        ]
        read_only_fields = ['approval_status', 'registered_at']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Client
        fields = ['id', 'full_name', 'phone_number']


class ClientRegisterSerializer(serializers.Serializer):
    """Yolovchi ilovasi — ro'yxatdan o'tish."""
    full_name    = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=20)
    password     = serializers.CharField(write_only=True, min_length=6)

    def validate_phone_number(self, value):
        # Client (bot orqali user=None holida) mavjud bo'lishi mumkin — muammo
        # emas, create() uni akkauntga bog'laydi. Lekin shu raqam allaqachon
        # BOSHQA bir hisob (masalan haydovchi) uchun User.username sifatida
        # band bo'lsa, create_user() IntegrityError bilan qulaydi.
        if Client.objects.filter(phone_number=value, user__isnull=False).exists() or User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        return value

    def create(self, validated_data):
        full_name = validated_data['full_name']
        phone     = validated_data['phone_number']
        password  = validated_data['password']
        user = User.objects.create_user(username=phone, password=password)
        # Telegram bot orqali avval band bo'lgan bo'lishi mumkin (user=None) — o'sha
        # yozuvni akkauntga bog'laymiz, tarixi (safarlar, reyting) saqlanib qoladi.
        client, _ = Client.objects.get_or_create(phone_number=phone)
        client.user = user
        if not client.full_name:
            client.full_name = full_name
        client.save(update_fields=['user', 'full_name'])
        return client


class OrderSerializer(serializers.ModelSerializer):
    client_name          = serializers.CharField(source='client.full_name', read_only=True)
    client_phone         = serializers.CharField(source='client.phone_number', read_only=True)
    driver_name          = serializers.CharField(source='driver.full_name', read_only=True, allow_null=True)
    status_label         = serializers.CharField(source='get_status_display', read_only=True)
    seconds_left         = serializers.SerializerMethodField(read_only=True)
    # Yangi maydonlar
    client_rating        = serializers.SerializerMethodField(read_only=True)
    client_trips_count   = serializers.SerializerMethodField(read_only=True)
    driver_distance_km   = serializers.SerializerMethodField(read_only=True)
    driver_eta_minutes   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'client_name', 'client_phone', 'driver_name',
            'from_address', 'from_lat', 'from_lng',
            'to_address', 'to_lat', 'to_lng',
            'price', 'commission', 'distance_km',
            'payment_type', 'car_type', 'note',
            'status', 'status_label', 'created_at', 'updated_at',
            'seconds_left',
            'client_rating', 'client_trips_count',
            'driver_distance_km', 'driver_eta_minutes',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def _get_driver(self):
        request = self.context.get('request')
        if request and hasattr(request.user, 'driver_profile'):
            return request.user.driver_profile
        return None

    def get_seconds_left(self, instance):
        driver = self._get_driver()
        if instance.status == 'pending' and instance.dispatched_to == driver:
            from django.utils import timezone
            from .models import TariffSettings
            tariff = TariffSettings.get()
            if instance.dispatched_at:
                passed = (timezone.now() - instance.dispatched_at).total_seconds()
                return max(0, int(tariff.dispatch_timeout - passed))
            return tariff.dispatch_timeout
        return None

    def get_client_rating(self, instance):
        """Mijozning reytingini qaytaradi (faqat pending/dispatch paytida)."""
        if instance.status in ('pending',):
            return float(instance.client.rating)
        return None

    def get_client_trips_count(self, instance):
        if instance.status in ('pending',):
            return instance.client.trips_count
        return None

    def get_driver_distance_km(self, instance):
        """Haydovchi → mijoz orasidagi masofa (faqat pending buyurtmada)."""
        if instance.status != 'pending':
            return None
        driver = self._get_driver()
        if not driver or driver.latitude is None or driver.longitude is None:
            return None
        if instance.from_lat is None or instance.from_lng is None:
            return None
        from .utils import haversine
        dist = haversine(driver.latitude, driver.longitude,
                         instance.from_lat, instance.from_lng)
        return round(dist, 2) if dist is not None else None

    def get_driver_eta_minutes(self, instance):
        """Taxminiy yetib kelish vaqti (minutda). 30 km/h o'rtacha tezlik."""
        dist = self.get_driver_distance_km(instance)
        if dist is None:
            return None
        eta = dist / 30 * 60      # 30 km/h → minutlarga
        return max(1, round(eta))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        driver = self._get_driver()

        # Pending yoki boshqa haydovchi buyurtmasida kontakt yashirish
        if instance.status == 'pending' or (
            instance.driver and driver and instance.driver.id != driver.id
        ):
            data['client_phone'] = '+998 ** *** ** **'
            data['client_name']  = 'Mijoz'
        return data
