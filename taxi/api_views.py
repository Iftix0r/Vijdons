"""
REST API — Haydovchi mobil ilovasi uchun.

Endpoints:
  POST /api/driver/register/        — Ro'yxatdan o'tish
  POST /api/driver/login/           — Kirish → token
  GET  /api/driver/profile/         — O'z profili
  POST /api/driver/duty/            — is_on_duty toggle
  PUT  /api/driver/fcm/             — FCM token yangilash
  POST /api/driver/location/        — GPS lokatsiyani yangilash

  GET  /api/orders/available/       — Pending + o'z faol buyurtmalari
  GET  /api/orders/my/              — O'z tarixi
  POST /api/orders/<id>/accept/     — Qabul qilish (komissiya yechiladi)
  POST /api/orders/<id>/on_way/     — Yo'lda
  POST /api/orders/<id>/complete/   — Yakunlash
  POST /api/orders/<id>/cancel/     — Bekor qilish

  GET  /api/tariff/                 — Joriy tariff (base_price, price_per_km)
"""

from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Driver, Order, TariffSettings, ChatMessage
from .serializers import (
    DriverRegisterSerializer,
    DriverLoginSerializer,
    DriverProfileSerializer,
    OrderSerializer,
)
from .utils import send_telegram, dispatch_order


# ── helpers ───────────────────────────────────────────────────────────────────

def get_driver(request):
    try:
        return request.user.driver_profile
    except Driver.DoesNotExist:
        return None


def driver_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        driver = get_driver(request)
        if driver is None:
            return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)
        if driver.approval_status != Driver.APPROVAL_APPROVED:
            return Response(
                {'detail': 'Hisobingiz hali tasdiqlanmagan. Admin tasdiqlashini kuting.'},
                status=403,
            )
        return fn(request, driver, *args, **kwargs)
    return wrapper


def get_driver_by_user(user):
    try:
        return user.driver_profile
    except Exception:
        return None


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def driver_register(request):
    serializer = DriverRegisterSerializer(data=request.data)
    if serializer.is_valid():
        driver = serializer.save()
        return Response(
            {
                'detail': "Ro'yxatdan muvaffaqiyatli o'tdingiz. Admin tasdiqlagandan so'ng kirishingiz mumkin.",
                'driver_id': driver.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def driver_login(request):
    serializer = DriverLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    phone    = serializer.validated_data['phone_number']
    password = serializer.validated_data['password']
    user     = authenticate(request, username=phone, password=password)

    if user is None:
        return Response({'detail': "Telefon raqami yoki parol noto'g'ri."}, status=401)

    driver = get_driver_by_user(user)
    if driver is None:
        return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)
    if driver.approval_status == Driver.APPROVAL_REJECTED:
        return Response({'detail': "Hisobingiz rad etilgan. Admin bilan bog'laning."}, status=403)
    if driver.approval_status == Driver.APPROVAL_PENDING:
        return Response({'detail': 'Hisobingiz hali tasdiqlanmagan. Admin tasdiqlashini kuting.'}, status=403)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'driver': DriverProfileSerializer(driver).data})


# ── Profile ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_profile(request, driver):
    return Response(DriverProfileSerializer(driver).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_duty_toggle(request, driver):
    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    return Response({'is_on_duty': driver.is_on_duty})


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_fcm_update(request, driver):
    token = request.data.get('fcm_token', '').strip()
    if not token:
        return Response({'detail': 'fcm_token maydoni talab qilinadi.'}, status=400)
    driver.fcm_token = token
    driver.save(update_fields=['fcm_token'])
    return Response({'detail': 'FCM token yangilandi.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_location_update(request, driver):
    """GPS koordinatalarni yangilash."""
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    if lat is None or lng is None:
        return Response({'detail': 'latitude va longitude talab qilinadi.'}, status=400)
    try:
        driver.latitude  = float(lat)
        driver.longitude = float(lng)
        driver.save(update_fields=['latitude', 'longitude'])
        return Response({'detail': 'Lokatsiya yangilandi.', 'latitude': driver.latitude, 'longitude': driver.longitude})
    except (ValueError, TypeError):
        return Response({'detail': "Noto'g'ri koordinatalar."}, status=400)


# ── Tariff ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def get_tariff(request):
    """Joriy tariff ma'lumotlarini qaytaradi (ilovada narx hisoblash uchun)."""
    t = TariffSettings.get()
    return Response({
        'base_price':   str(t.base_price),
        'price_per_km': str(t.price_per_km),
        'commission':   str(t.commission),
    })


# ── Orders ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def available_orders(request, driver):
    """
    Faqat bu haydovchiga dispatch qilingan pending buyurtma + o'z faol buyurtmalari.
    """
    qs = Order.objects.select_related('client', 'driver').filter(
        Q(status='pending', dispatched_to=driver) |
        Q(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
    ).order_by('-created_at')
    return Response(OrderSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def my_orders(request, driver):
    qs = Order.objects.select_related('client').filter(driver=driver).order_by('-created_at')[:50]
    return Response(OrderSerializer(qs, many=True, context={'request': request}).data)


def _order_action(request, driver, pk, allowed_statuses, new_status):
    try:
        order = Order.objects.select_related('client', 'driver').get(pk=pk)
    except Order.DoesNotExist:
        return Response({'detail': 'Buyurtma topilmadi.'}, status=404)

    if order.status not in allowed_statuses:
        return Response(
            {'detail': f"Bu amalni '{order.get_status_display()}' holatida bajarib bo'lmaydi."},
            status=400,
        )

    if order.driver_id and order.driver_id != driver.id:
        return Response({'detail': 'Bu buyurtma sizga tegishli emas.'}, status=403)

    update_fields = ['status', 'updated_at']

    if new_status == 'accepted':
        tariff = TariffSettings.get()
        commission = order.commission if order.commission else tariff.commission
        if driver.balance < commission:
            return Response(
                {'detail': f"Balansingizda yetarli mablag' yo'q. Komissiya: {commission} UZS. Joriy balans: {driver.balance} UZS."},
                status=400,
            )
        from decimal import Decimal
        driver.balance -= Decimal(str(commission))
        driver.save(update_fields=['balance'])
        order.driver = driver
        order.commission = commission
        update_fields = ['status', 'driver', 'commission', 'updated_at']

    order.status = new_status
    order.save(update_fields=update_fields)

    # Telegram xabarlari
    _notify_telegram(order, new_status, driver)

    return Response(OrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_reject(request, driver, pk):
    """Haydovchi rad etadi — keyingi yaqin haydovchiga yuboriladi."""
    try:
        order = Order.objects.get(pk=pk, status='pending', dispatched_to=driver)
    except Order.DoesNotExist:
        return Response({'detail': 'Buyurtma topilmadi.'}, status=404)

    order.rejected_by.add(driver)
    order.dispatched_to = None
    order.save(update_fields=['dispatched_to'])

    # Keyingi haydovchiga yuborish
    import threading
    threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

    return Response({'detail': 'Rad etildi.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_accept(request, driver, pk):
    return _order_action(request, driver, pk, ['pending'], 'accepted')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_on_way(request, driver, pk):
    return _order_action(request, driver, pk, ['accepted'], 'on_way')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_arrived(request, driver, pk):
    return _order_action(request, driver, pk, ['on_way'], 'arrived')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_complete(request, driver, pk):
    return _order_action(request, driver, pk, ['arrived', 'on_way', 'accepted'], 'completed')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_cancel(request, driver, pk):
    return _order_action(request, driver, pk, ['accepted', 'on_way', 'arrived'], 'cancelled')


def _notify_telegram(order, new_status, driver):
    msgs = {
        'accepted': (
            f"🚖 <b>Buyurtma #{order.id} qabul qilindi</b>\n"
            f"👤 Mijoz: {order.client.full_name or order.client.phone_number}\n"
            f"📍 {order.from_address} → {order.to_address}\n"
            f"🚗 Haydovchi: {driver.full_name} ({driver.car_number})\n"
            f"💰 Narx: {order.price or '—'} UZS"
        ),
        'on_way': (
            f"🚗 <b>Haydovchi yo'lda #{order.id}</b>\n"
            f"👤 {order.client.full_name or order.client.phone_number} ({order.client.phone_number})\n"
            f"🚗 {driver.full_name} — {driver.car_model} ({driver.car_number})"
        ),
        'arrived': (
            f"📍 <b>Haydovchi yetib keldi #{order.id}</b>\n"
            f"👤 {order.client.full_name or order.client.phone_number} ({order.client.phone_number})\n"
            f"🚗 {driver.full_name} — {driver.car_number} kutmoqda"
        ),
        'completed': (
            f"✅ <b>Buyurtma yakunlandi #{order.id}</b>\n"
            f"👤 {order.client.full_name or order.client.phone_number}\n"
            f"📍 {order.from_address} → {order.to_address}\n"
            f"💰 {order.price or '—'} UZS | 🚗 {driver.full_name}"
        ),
        'cancelled': (
            f"❌ <b>Buyurtma bekor qilindi #{order.id}</b>\n"
            f"🚗 Haydovchi: {driver.full_name}"
        ),
    }
    msg = msgs.get(new_status)
    if msg:
        send_telegram(msg)


# ── Chat ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_messages(request, driver):
    """Haydovchining barcha xabarlari + o'qilmagan operatordan xabarlarni o'qildi deb belgilash."""
    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).update(is_read=True)
    msgs = ChatMessage.objects.filter(driver=driver).order_by('created_at')[:100]
    data = [{
        'id':         m.id,
        'sender':     m.sender,
        'text':       m.text,
        'is_read':    m.is_read,
        'created_at': m.created_at.isoformat(),
    } for m in msgs]
    return Response({'messages': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_send(request, driver):
    """Haydovchidan operator ga xabar."""
    text = request.data.get('text', '').strip()
    if not text:
        return Response({'detail': 'text maydoni talab qilinadi.'}, status=400)
    msg = ChatMessage.objects.create(
        driver=driver,
        sender=ChatMessage.SENDER_DRIVER,
        text=text,
    )
    # Telegram ga ham yuborish
    send_telegram(f"💬 <b>{driver.full_name}</b> ({driver.car_number}):\n{text}")
    return Response({'id': msg.id, 'sender': msg.sender, 'text': msg.text, 'created_at': msg.created_at.isoformat()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_unread_count(request, driver):
    """O'qilmagan operatordan xabarlar soni."""
    count = ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).count()
    return Response({'unread': count})
