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

# Pedidos com estes status não contam como venda (pagamento não concluído ou venda desfeita)
STATUS_NAO_CONTAM_COMO_VENDA = ['aguardando_pagamento', 'cancelado']


def estatisticas_vendedor(vendedor):
    """Reputação do vendedor desde que entrou na plataforma: total de vendas e disputas.

    - total_vendas: pedidos recebidos que não foram cancelados/estornados.
    - total_disputas: todas as disputas abertas contra o vendedor (inclusive em análise).
    - pct_disputas_vencidas: % das disputas JÁ DECIDIDAS que terminaram a favor do vendedor
      (as que estão em análise ainda não entram na conta). None se nenhuma foi decidida.
    """
    from disputes.models import Dispute

    total_vendas = Order.objects.filter(vendedor=vendedor).exclude(status__in=STATUS_NAO_CONTAM_COMO_VENDA).count()

    disputas = Dispute.objects.filter(vendedor=vendedor)
    total_disputas = disputas.count()
    vencidas = disputas.filter(status='decidida_vendedor').count()
    perdidas = disputas.filter(status='decidida_comprador').count()
    decididas = vencidas + perdidas

    return {
        'total_vendas': total_vendas,
        'total_disputas': total_disputas,
        'disputas_vencidas': vencidas,
        'disputas_perdidas': perdidas,
        'disputas_decididas': decididas,
        'disputas_em_analise': total_disputas - decididas,
        'pct_disputas_vencidas': round(vencidas / decididas * 100) if decididas else None,
    }
