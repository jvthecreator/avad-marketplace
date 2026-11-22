import datetime

from django.utils import timezone

from notifications.services import notificar_recebimento_confirmado

from .models import Order, TrackingEvent, PRAZO_CONFIRMACAO_AUTOMATICA_DIAS


def confirmar_recebimentos_vencidos():
    """Confirma automaticamente o recebimento dos pedidos entregues há mais de 14 dias
    sem confirmação do comprador. Pedidos com disputa ou reembolso em andamento ficam de fora.
    Retorna quantos pedidos foram confirmados."""
    limite = timezone.now() - datetime.timedelta(days=PRAZO_CONFIRMACAO_AUTOMATICA_DIAS)
    candidatos = list(
        Order.objects
        .filter(status='entregue', recebimento_confirmado=False, entregue_em__lte=limite)
        .exclude(disputes__status='em_analise')
        .exclude(refund_requests__status__in=['solicitacao_enviada', 'vendedor_notificado', 'estorno_processamento'])
    )

    total = 0
    for order in candidatos:
        # o filtro evita confirmar duas vezes se dois acessos chegarem ao mesmo tempo
        atualizados = Order.objects.filter(pk=order.pk, recebimento_confirmado=False).update(recebimento_confirmado=True)
        if atualizados:
            TrackingEvent.objects.create(
                pedido=order,
                titulo='Recebimento confirmado automaticamente',
                descricao=f'O comprador não confirmou o recebimento em {PRAZO_CONFIRMACAO_AUTOMATICA_DIAS} dias; a confirmação foi feita automaticamente.',
                local=order.cep_entrega,
                data_hora=order.entregue_em + datetime.timedelta(days=PRAZO_CONFIRMACAO_AUTOMATICA_DIAS),
            )
            notificar_recebimento_confirmado(order, automatico=True)
            total += 1
    return total