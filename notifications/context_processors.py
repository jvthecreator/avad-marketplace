from accounts.roles import tipo_usuario

from .models import Notification


def notificacoes(request):
    """Número de notificações não lidas do tipo de usuário atual (usado no sininho)."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'notif_count': 0}
    total = Notification.objects.filter(
        usuario=user, tipo_usuario=tipo_usuario(request), lida=False
    ).count()
    return {'notif_count': total}
