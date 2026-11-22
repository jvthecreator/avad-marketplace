"""Criação das notificações. As views só chamam estas funções nos pontos em que algo acontece."""
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Notification


def _nome(user):
    profile = getattr(user, 'profile', None)
    return profile.nome if profile else user.username


def notificar(usuario, tipo_usuario, titulo, mensagem, link='', categoria='pedido'):
    return Notification.objects.create(
        usuario=usuario,
        tipo_usuario=tipo_usuario,
        categoria=categoria,
        titulo=titulo[:120],
        mensagem=mensagem[:300],
        link=link,
    )


def notificar_mediadores(titulo, mensagem, link, categoria='disputa'):
    for mediador in User.objects.filter(profile__is_mediador=True):
        notificar(mediador, 'mediador', titulo, mensagem, link, categoria)


# ---------------- pedidos ----------------

def _link_pedido(order):
    return reverse('orders:tracking', args=[order.id])


def notificar_novo_pedido(order):
    """Vendedor: alguém fez um pedido."""
    notificar(
        order.vendedor, 'vendedor', 'Novo pedido recebido',
        f'{_nome(order.comprador)} comprou {order.quantidade}x {order.produto.titulo} (pedido {order.codigo}).',
        _link_pedido(order), 'pedido',
    )


def notificar_status_pedido(order):
    """Comprador: o vendedor mudou o status do pedido (preparando, a caminho, entregue...)."""
    if order.status == 'preparando':
        titulo = 'Pedido confirmado pela loja'
        msg = f'A loja confirmou o pedido {order.codigo} e está preparando o envio.'
    elif order.status == 'a_caminho':
        titulo = 'Seu pedido saiu para entrega'
        msg = f'O pedido {order.codigo} foi despachado. Código de rastreio: {order.codigo_rastreio}.'
    elif order.status == 'entregue':
        titulo = 'Seu pedido foi entregue'
        msg = f'O pedido {order.codigo} consta como entregue. Confirme o recebimento'
        if order.confirmacao_automatica_em:
            msg += f' até {order.confirmacao_automatica_em.strftime("%d/%m/%Y")} (depois disso a confirmação é automática)'
        msg += '.'
    elif order.status == 'cancelado':
        titulo = 'Pedido cancelado'
        msg = f'O pedido {order.codigo} foi cancelado.'
    else:
        return
    notificar(order.comprador, 'comprador', titulo, msg, _link_pedido(order), 'pedido')


def notificar_recebimento_confirmado(order, automatico=False):
    """Vendedor (e comprador, se for automática): o recebimento foi confirmado."""
    if automatico:
        notificar(
            order.vendedor, 'vendedor', 'Recebimento confirmado automaticamente',
            f'O comprador não confirmou o pedido {order.codigo} no prazo, e o recebimento foi confirmado automaticamente.',
            _link_pedido(order), 'pedido',
        )
        notificar(
            order.comprador, 'comprador', 'Recebimento confirmado automaticamente',
            f'O prazo para confirmar o pedido {order.codigo} terminou, e o recebimento foi confirmado automaticamente.',
            _link_pedido(order), 'pedido',
        )
    else:
        notificar(
            order.vendedor, 'vendedor', 'Recebimento confirmado',
            f'{_nome(order.comprador)} confirmou o recebimento do pedido {order.codigo}.',
            _link_pedido(order), 'pedido',
        )


def notificar_nova_avaliacao(order, nota_vendedor):
    """Vendedor: recebeu uma avaliação."""
    notificar(
        order.vendedor, 'vendedor', 'Nova avaliação recebida',
        f'{_nome(order.comprador)} avaliou você com {nota_vendedor} estrela(s) no pedido {order.codigo}.',
        reverse('accounts:seller_profile', args=[order.vendedor.id]), 'avaliacao',
    )


# ---------------- reembolsos ----------------

def notificar_reembolso_solicitado(refund):
    """Vendedor: o comprador pediu reembolso."""
    order = refund.pedido
    notificar(
        order.vendedor, 'vendedor', 'Pedido de reembolso',
        f'{_nome(order.comprador)} solicitou reembolso do pedido {order.codigo} (protocolo {refund.protocolo}).',
        reverse('orders:seller_orders'), 'reembolso',
    )


def notificar_reembolso_resposta(refund):
    """Comprador: o vendedor aprovou ou negou o reembolso."""
    order = refund.pedido
    if refund.status == 'valor_devolvido':
        titulo = 'Reembolso aprovado'
        msg = f'O vendedor aprovou o reembolso {refund.protocolo} do pedido {order.codigo}. O valor foi estornado.'
    else:
        titulo = 'Reembolso negado'
        msg = f'O vendedor negou o reembolso {refund.protocolo} do pedido {order.codigo}.'
    notificar(order.comprador, 'comprador', titulo, msg, reverse('orders:refund_status', args=[refund.id]), 'reembolso')


# ---------------- disputas ----------------

def _link_disputa(dispute):
    return reverse('disputes:dispute_detail', args=[dispute.id])


def _link_mediacao(dispute):
    return reverse('disputes:mediation_detail', args=[dispute.id])


def notificar_disputa_aberta(dispute):
    """Vendedor e mediadores: o comprador abriu uma disputa."""
    msg = f'{_nome(dispute.comprador)} abriu a disputa {dispute.codigo} sobre o pedido {dispute.pedido.codigo}.'
    notificar(
        dispute.vendedor, 'vendedor', 'Disputa aberta contra você',
        msg + ' O repasse ficou retido até a decisão.', _link_disputa(dispute), 'disputa',
    )
    notificar_mediadores('Nova disputa para mediar', msg, _link_mediacao(dispute))


def notificar_mensagem_disputa(dispute, papel):
    """Os outros envolvidos na disputa: alguém enviou uma mensagem. papel = quem escreveu."""
    titulo = 'Nova mensagem na disputa'
    msg = f'Há uma nova mensagem ({papel}) na disputa {dispute.codigo}.'
    if papel != 'comprador':
        notificar(dispute.comprador, 'comprador', titulo, msg, _link_disputa(dispute), 'disputa')
    if papel != 'vendedor':
        notificar(dispute.vendedor, 'vendedor', titulo, msg, _link_disputa(dispute), 'disputa')
    if papel != 'mediador':
        notificar_mediadores(titulo, msg, _link_mediacao(dispute))


def notificar_decisao_disputa(dispute):
    """Comprador e vendedor: a mediação decidiu a disputa."""
    favorecido = 'comprador' if dispute.status == 'decidida_comprador' else 'vendedor'
    titulo = 'Disputa decidida pela mediação'
    msg = f'A mediação decidiu a favor do {favorecido} na disputa {dispute.codigo}.'
    notificar(dispute.comprador, 'comprador', titulo, msg, _link_disputa(dispute), 'disputa')
    notificar(dispute.vendedor, 'vendedor', titulo, msg, _link_disputa(dispute), 'disputa')
