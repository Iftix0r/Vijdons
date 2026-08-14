"""
REST API — native Android SMS-shlyuz ilovasi (vijdon_sms_gateway) uchun.
URL prefix: /api/smsgatewayapp/ — driverapp/operatorapp bilan bir xil
sababga ko'ra /panel/ prefiksisiz (Cloudflare WAF prefiks-istisnosi).

Auth: kirish uchun ALLAQACHON mavjud endpoint ishlatiladi —
`taxi/api_views.py: operator_login` (`/panel/api/operator/login/`,
qo'ng'iroq-kuzatuvchi ilova ham xuddi shundan foydalanadi) — is_staff
foydalanuvchiga DRF token beradi. Shu sabab bu yerda alohida login
endpoint YO'Q, faqat o'sha token bilan quyidagi amallar bajariladi.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SmsGatewayMessage, SmsGatewayToken, SmsGatewayIncoming
from .utils import normalize_phone_uz

# Band qilingan ("sending") holatda shuncha daqiqadan ko'p tursa —
# o'sha qurilma javob bermay qo'ygan (ilova o'chirilgan, tarmoq uzilgan
# va h.k.) deb hisoblanadi, xabar boshqa qurilma tomonidan qayta olinishi
# uchun yana "pending" ga qaytariladi.
CLAIM_STALE_MINUTES = 3


def _staff_only(request):
    return request.user.is_authenticated and request.user.is_staff


@api_view(['POST'])
def fcm_sync(request):
    if not _staff_only(request):
        return Response({'detail': "Ruxsat yo'q."}, status=403)
    token = str(request.data.get('fcm_token', '')).strip()
    if not token:
        return Response({'detail': 'fcm_token kiritilishi shart.'}, status=400)
    SmsGatewayToken.objects.get_or_create(user=request.user, fcm_token=token)
    return Response({'detail': 'FCM token yangilandi.'})


@api_view(['GET'])
def pending(request):
    """Kutilayotgan (yoki uzoq vaqt band bo'lib qolgan — pastga qarang)
    xabarlarni shu qurilmaga DARHOL "band qilib" beradi — shu sabab bir
    xil xabar ikkita qurilma tomonidan ikki marta yuborilmaydi."""
    if not _staff_only(request):
        return Response({'detail': "Ruxsat yo'q."}, status=403)

    stale_cutoff = timezone.now() - timezone.timedelta(minutes=CLAIM_STALE_MINUTES)
    with transaction.atomic():
        ids = list(
            SmsGatewayMessage.objects.select_for_update(skip_locked=True)
            .filter(
                SmsGatewayMessage.status_pending_or_stale_q(stale_cutoff),
            )
            .order_by('created_at')
            .values_list('id', flat=True)[:10]
        )
        SmsGatewayMessage.objects.filter(id__in=ids).update(
            status=SmsGatewayMessage.STATUS_SENDING, claimed_at=timezone.now(), sent_by=request.user,
        )
        messages = list(SmsGatewayMessage.objects.filter(id__in=ids).order_by('created_at'))

    return Response([
        {'id': m.id, 'phone_number': m.phone_number, 'text': m.text, 'created_at': m.created_at.isoformat()}
        for m in messages
    ])


@api_view(['POST'])
def report_result(request, pk):
    if not _staff_only(request):
        return Response({'detail': "Ruxsat yo'q."}, status=403)

    message = get_object_or_404(SmsGatewayMessage, pk=pk)
    if message.status not in (SmsGatewayMessage.STATUS_PENDING, SmsGatewayMessage.STATUS_SENDING):
        return Response({'detail': "Bu xabar allaqachon hal qilingan."}, status=400)
    status_value = request.data.get('status')
    if status_value not in (SmsGatewayMessage.STATUS_SENT, SmsGatewayMessage.STATUS_FAILED):
        return Response({'detail': "status 'sent' yoki 'failed' bo'lishi kerak."}, status=400)
    message.status = status_value
    message.error = str(request.data.get('error', ''))[:255]
    message.sent_by = request.user
    message.resolved_at = timezone.now()
    message.save(update_fields=['status', 'error', 'sent_by', 'resolved_at'])
    return Response({'detail': 'ok'})


@api_view(['POST'])
def incoming_report(request):
    """Qurilmaning SIM kartasiga kelgan SMS haqida — `IncomingSmsReceiver.kt`
    (SMS_RECEIVED broadcast) tomonidan chaqiriladi. Eskiz/alfa-nomdan farqli,
    real SIM raqamiga mijoz/haydovchi javob yozishi mumkin — operator buni
    panelda (`/system/sms/`) ko'rishi uchun."""
    if not _staff_only(request):
        return Response({'detail': "Ruxsat yo'q."}, status=403)

    phone = normalize_phone_uz(str(request.data.get('phone_number', '')).strip())
    text = str(request.data.get('text', '')).strip()
    if not phone or not text:
        return Response({'detail': "phone_number va text kiritilishi shart."}, status=400)

    received_at_raw = request.data.get('received_at')
    received_at = None
    if received_at_raw:
        from django.utils.dateparse import parse_datetime
        received_at = parse_datetime(str(received_at_raw))
    if not received_at:
        received_at = timezone.now()

    SmsGatewayIncoming.objects.create(
        phone_number=phone, text=text, received_at=received_at, device=request.user,
    )
    return Response({'detail': 'ok'})
