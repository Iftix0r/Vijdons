"""
REST API — Haydovchi mobil ilovasi uchun.

Endpoints:
  POST /api/driver/register/      — Ro'yxatdan o'tish (admin tasdiqlashini kutadi)
  POST /api/driver/login/         — Kirish → token qaytaradi
  GET  /api/driver/profile/       — O'z profili
  POST /api/driver/duty/          — is_on_duty toggle
  PUT  /api/driver/fcm/           — FCM token yangilash

  GET  /api/orders/available/     — Haydovchiga tegishli / pending buyurtmalar
  GET  /api/orders/my/            — O'z buyurtmalari (history)
  POST /api/orders/<id>/accept/   — Buyurtmani qabul qilish
  POST /api/orders/<id>/on_way/   — Yo'lda
  POST /api/orders/<id>/complete/ — Yakunlash
  POST /api/orders/<id>/cancel/   — Bekor qilish
"""

from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Driver, Order
from .serializers import (
    DriverRegisterSerializer,
    DriverLoginSerializer,
    DriverProfileSerializer,
    OrderSerializer,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def get_driver(request):
    """Return Driver for the authenticated user, or None."""
    try:
        return request.user.driver_profile
    except Driver.DoesNotExist:
        return None


def driver_required(fn):
    """Decorator: user must have a driver profile and be approved."""
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

    # username == phone_number
    user = authenticate(request, username=phone, password=password)
    if user is None:
        return Response({'detail': 'Telefon raqami yoki parol noto\'g\'ri.'}, status=401)

    driver = get_driver_by_user(user)
    if driver is None:
        return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)

    if driver.approval_status == Driver.APPROVAL_REJECTED:
        return Response({'detail': 'Hisobingiz rad etilgan. Admin bilan bog\'laning.'}, status=403)

    if driver.approval_status == Driver.APPROVAL_PENDING:
        return Response(
            {'detail': 'Hisobingiz hali tasdiqlanmagan. Admin tasdiqlashini kuting.'},
            status=403,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            'token': token.key,
            'driver': DriverProfileSerializer(driver).data,
        }
    )


def get_driver_by_user(user):
    try:
        return user.driver_profile
    except Exception:
        return None


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


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_fcm_update(request, driver):
    token = request.data.get('fcm_token', '').strip()
    if not token:
        return Response({'detail': 'fcm_token maydoni talab qilinadi.'}, status=400)
    driver.fcm_token = token
    driver.save(update_fields=['fcm_token'])
    return Response({'detail': 'FCM token yangilandi.'})


# ── Orders ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def available_orders(request, driver):
    """
    Pending orders that have no driver assigned yet
    + orders already assigned to this driver that are active.
    """
    qs = Order.objects.select_related('client', 'driver').filter(
        Q(status='pending', driver__isnull=True) |
        Q(driver=driver, status__in=['accepted', 'on_way'])
    ).order_by('-created_at')
    return Response(OrderSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def my_orders(request, driver):
    qs = Order.objects.select_related('client').filter(driver=driver).order_by('-created_at')[:50]
    return Response(OrderSerializer(qs, many=True).data)


def _order_action(request, driver, pk, allowed_statuses, new_status):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({'detail': 'Buyurtma topilmadi.'}, status=404)

    if order.status not in allowed_statuses:
        return Response({'detail': f'Bu amalni {order.get_status_display()} holatida bajarib bo\'lmaydi.'}, status=400)

    # Only assigned driver can change (except accepting unassigned ones)
    if order.driver_id and order.driver_id != driver.id:
        return Response({'detail': 'Bu buyurtma sizga tegishli emas.'}, status=403)

    if new_status == 'accepted':
        order.driver = driver
    order.status = new_status
    order.save(update_fields=['status', 'driver', 'updated_at'] if new_status == 'accepted' else ['status', 'updated_at'])
    return Response(OrderSerializer(order).data)


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
def order_complete(request, driver, pk):
    return _order_action(request, driver, pk, ['on_way', 'accepted'], 'completed')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_cancel(request, driver, pk):
    return _order_action(request, driver, pk, ['accepted', 'on_way'], 'cancelled')
