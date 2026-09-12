from django.conf import settings
from django.core.mail import send_mail

def _link(path, token):
    return f'{settings.FRONTEND_URL}{path}?token={token}'


def send_verification_email(user, token):
    link = _link('/verify-email', token)
    send_mail(
        'Xác thực email tài khoản Health Care Monitor',
        f'Xin chào {user.get_full_name() or user.username},\n\n'
        f'Vui lòng mở liên kết sau để xác thực email (có hiệu lực trong {settings.AUTH_TOKEN_TTL_MINUTES} phút):\n{link}\n\n'
        'Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    link = _link('/reset-password', token)
    send_mail(
        'Đặt lại mật khẩu Health Care Monitor',
        f'Vui lòng mở liên kết sau để đặt mật khẩu mới (có hiệu lực trong {settings.AUTH_TOKEN_TTL_MINUTES} phút):\n{link}\n\n'
        'Nếu bạn không yêu cầu, hãy bỏ qua email này.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
