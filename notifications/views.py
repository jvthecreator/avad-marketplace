from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.roles import tipo_usuario

from .models import Notification


def _do_usuario(request):
    """Só as notificações da pessoa, no tipo de usuário com que ela entrou."""
    return Notification.objects.filter(usuario=request.user, tipo_usuario=tipo_usuario(request))


@login_required
def list_view(request):
    apenas_nao_lidas = request.GET.get('filtro') == 'nao_lidas'
    notificacoes = _do_usuario(request)
    if apenas_nao_lidas:
        notificacoes = notificacoes.filter(lida=False)
    return render(request, 'notifications/list.html', {
        'notificacoes': notificacoes[:50],
        'apenas_nao_lidas': apenas_nao_lidas,
    })


@login_required
def open_view(request, pk):
    """Marca como lida e leva para a tela do assunto."""
    notificacao = get_object_or_404(_do_usuario(request), pk=pk)
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save(update_fields=['lida'])
    return redirect(notificacao.link or 'notifications:list')


@login_required
@require_POST
def mark_all_read_view(request):
    _do_usuario(request).filter(lida=False).update(lida=True)
    messages.success(request, 'Todas as notificações foram marcadas como lidas.')
    return redirect('notifications:list')
