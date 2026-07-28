"""Django xatolarini (500'lar) DB'ga yozib qo'yuvchi log handler.

DEBUG=False bo'lganda brauzerda traceback ko'rinmay qoladi — bu handler
`django.request` logeriga ulanadi (Django HAR BIR ushlanmagan istisno uchun
shu logerga yozadi, xuddi AdminEmailHandler ishlatgani kabi), shunda
/system/ panelidagi Xavfsizlik/Jurnal sahifasida to'liq traceback'ni SSH'siz,
DEBUG'ni yoqmasdan ko'rish mumkin bo'ladi."""
import logging
import traceback as tb_module


class SystemAuditLogHandler(logging.Handler):
    def emit(self, record):
        try:
            from taxi.models import SystemAuditLog

            request = getattr(record, 'request', None)
            path = request.path if request is not None else ''
            user = None
            if request is not None:
                req_user = getattr(request, 'user', None)
                if req_user is not None and req_user.is_authenticated:
                    user = req_user

            detail = ''
            if record.exc_info:
                detail = ''.join(tb_module.format_exception(*record.exc_info))

            SystemAuditLog.objects.create(
                level='error',
                event_type='server_error',
                message=record.getMessage()[:500],
                detail=detail[:20000],
                user=user,
                path=path[:300],
            )
        except Exception:
            # Log handler o'zi hech qachon ilova ishlashini to'xtatmasligi kerak
            # (masalan DB shu payt mavjud bo'lmasa ham).
            pass
