"""Estatísticas do painel do vendedor por período (desde o começo, anual, mensal, semanal, diário).

Todas as datas são tratadas no fuso do projeto (settings.TIME_ZONE). A semana começa no DOMINGO
(padrão brasileiro). As comparações com o período anterior usam o MESMO trecho já decorrido
(ex.: semana atual até quarta 12h  x  semana passada até quarta 12h), para a comparação ser justa.
"""
import calendar
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from orders.models import Order
from orders.services import STATUS_NAO_CONTAM_COMO_VENDA
from finance.models import PaymentSplit


PERIODOS = [
    ('total', 'Desde o começo'),
    ('anual', 'Anual'),
    ('mensal', 'Mensal'),
    ('semanal', 'Semanal'),
    ('diario', 'Diário'),
]
PERIODO_PADRAO = 'mensal'

MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']  # semana começando no domingo
DIAS_SEMANA_EXTENSO = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']

# Textos que mudam conforme o período escolhido
TEXTOS = {
    'total':   {'vendas': 'Vendas desde o começo', 'comparacao': None},
    'anual':   {'vendas': 'Vendas no ano',    'comparacao': 'vs ano anterior'},
    'mensal':  {'vendas': 'Vendas no mês',    'comparacao': 'vs mês anterior'},
    'semanal': {'vendas': 'Vendas na semana', 'comparacao': 'vs semana anterior'},
    'diario':  {'vendas': 'Vendas hoje',      'comparacao': 'vs ontem'},
}


def vendas_do_vendedor(vendedor):
    """Pedidos que contam como venda (mesma regra usada no perfil do vendedor)."""
    return Order.objects.filter(vendedor=vendedor).exclude(status__in=STATUS_NAO_CONTAM_COMO_VENDA)


def _meia_noite(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _dias_no_mes(ano, mes):
    return calendar.monthrange(ano, mes)[1]


def _mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def limites_periodo(periodo, agora):
    """Retorna (inicio_atual, inicio_anterior, fim_anterior_equivalente, fim_anterior_completo).
    Para 'total' não existe período anterior: os três últimos valores são None."""
    hoje = _meia_noite(agora)

    if periodo == 'diario':
        inicio = hoje
        inicio_ant = hoje - datetime.timedelta(days=1)
        return inicio, inicio_ant, inicio_ant + (agora - inicio), inicio

    if periodo == 'semanal':
        dias_desde_domingo = (agora.weekday() + 1) % 7  # weekday(): seg=0 ... dom=6
        inicio = hoje - datetime.timedelta(days=dias_desde_domingo)
        inicio_ant = inicio - datetime.timedelta(days=7)
        return inicio, inicio_ant, inicio_ant + (agora - inicio), inicio

    if periodo == 'mensal':
        inicio = hoje.replace(day=1)
        ano_ant, mes_ant = _mes_anterior(agora.year, agora.month)
        inicio_ant = inicio.replace(year=ano_ant, month=mes_ant)
        # mesmo dia/hora do mês anterior (limitado ao último dia dele, ex.: 31/03 -> 28/02)
        dia_eq = min(agora.day, _dias_no_mes(ano_ant, mes_ant))
        fim_eq = agora.replace(year=ano_ant, month=mes_ant, day=dia_eq)
        return inicio, inicio_ant, min(fim_eq, inicio), inicio

    if periodo == 'anual':
        inicio = hoje.replace(month=1, day=1)
        inicio_ant = inicio.replace(year=agora.year - 1)
        dia_eq = min(agora.day, _dias_no_mes(agora.year - 1, agora.month))  # 29/02 em ano não bissexto
        fim_eq = agora.replace(year=agora.year - 1, day=dia_eq)
        return inicio, inicio_ant, fim_eq, inicio

    return None, None, None, None  # 'total'


def _resumo(pedidos):
    """Totais de um conjunto de pedidos (que já contam como venda)."""
    agg = pedidos.aggregate(bruto=Sum('valor_total'), unidades=Sum('quantidade'))
    bruto = agg['bruto'] or Decimal('0')
    qtd_pedidos = pedidos.count()
    liquido = (
        PaymentSplit.objects.filter(pedido__in=pedidos)
        .exclude(status_repasse='estornado')
        .aggregate(s=Sum('valor_liquido_vendedor'))['s']
    ) or Decimal('0')
    return {
        'bruto': bruto,
        'liquido': liquido,
        'pedidos': qtd_pedidos,
        'unidades': agg['unidades'] or 0,
        'ticket_medio': (bruto / qtd_pedidos) if qtd_pedidos else Decimal('0'),
        'pct_liquido': round(float(liquido / bruto) * 100, 1) if bruto else None,
    }


def _variacao(atual, anterior):
    """Variação percentual. None quando não há base de comparação (anterior = 0)."""
    if not anterior:
        return None
    return round((float(atual) - float(anterior)) / float(anterior) * 100, 1)


def _serie_grafico(vendas, periodo, agora, inicio, inicio_ant, fim_ant):
    """Monta rótulos e as duas séries (atual e anterior) do gráfico de evolução.
    Pontos futuros do período atual ficam como None, para a linha parar em 'agora'."""
    local = timezone.localtime

    if periodo == 'total':
        pedidos = list(vendas.values_list('criado_em', 'valor_total'))
        primeiro_ano = min([local(c).year for c, _ in pedidos] + [agora.year])
        anos = list(range(primeiro_ano, agora.year + 1))
        por_ano = defaultdict(float)
        for criado, valor in pedidos:
            por_ano[local(criado).year] += float(valor)
        return {
            'labels': [str(a) for a in anos],
            'atual': [round(por_ano[a], 2) for a in anos],
            'anterior': None,
            'legenda_atual': 'Faturamento por ano',
            'legenda_anterior': None,
            'subtitulo': 'Receita bruta de cada ano desde o início das suas vendas',
        }

    if periodo == 'anual':
        labels = MESES
        chave = lambda dt: dt.month - 1
        n_atual = agora.month
        legenda_atual, legenda_ant = str(agora.year), str(agora.year - 1)
        subtitulo = 'Receita bruta mês a mês: ano atual x ano anterior'
    elif periodo == 'mensal':
        ano_ant, mes_ant = inicio_ant.year, inicio_ant.month
        dias = max(_dias_no_mes(agora.year, agora.month), _dias_no_mes(ano_ant, mes_ant))
        labels = [str(d) for d in range(1, dias + 1)]
        chave = lambda dt: dt.day - 1
        n_atual = agora.day
        legenda_atual = f'{MESES[agora.month - 1]}/{agora.year}'
        legenda_ant = f'{MESES[mes_ant - 1]}/{ano_ant}'
        subtitulo = 'Receita bruta dia a dia: mês atual x mês anterior'
    elif periodo == 'semanal':
        labels = DIAS_SEMANA
        chave = lambda dt: (dt.weekday() + 1) % 7
        n_atual = (agora.weekday() + 1) % 7 + 1
        legenda_atual, legenda_ant = 'Esta semana', 'Semana anterior'
        subtitulo = 'Receita bruta dia a dia: semana atual x semana anterior (domingo a sábado)'
    else:  # diario
        labels = [f'{h}h' for h in range(24)]
        chave = lambda dt: dt.hour
        n_atual = agora.hour + 1
        legenda_atual, legenda_ant = 'Hoje', 'Ontem'
        subtitulo = 'Receita bruta hora a hora: hoje x ontem'

    atual = [0.0] * len(labels)
    anterior = [0.0] * len(labels)
    for criado, valor in vendas.filter(criado_em__gte=inicio).values_list('criado_em', 'valor_total'):
        atual[chave(local(criado))] += float(valor)
    for criado, valor in vendas.filter(criado_em__gte=inicio_ant, criado_em__lt=fim_ant).values_list('criado_em', 'valor_total'):
        anterior[chave(local(criado))] += float(valor)

    atual = [round(v, 2) if i < n_atual else None for i, v in enumerate(atual)]
    anterior = [round(v, 2) for v in anterior]
    if periodo == 'mensal':  # mês anterior mais curto: dias inexistentes ficam vazios
        dias_ant = _dias_no_mes(inicio_ant.year, inicio_ant.month)
        anterior = [v if i < dias_ant else None for i, v in enumerate(anterior)]

    return {
        'labels': labels, 'atual': atual, 'anterior': anterior,
        'legenda_atual': legenda_atual, 'legenda_anterior': legenda_ant, 'subtitulo': subtitulo,
    }


def _melhor_momento(pedidos, periodo):
    """Dia da semana (ou hora, no diário) com maior faturamento entre os pedidos dados."""
    totais = defaultdict(float)
    for criado, valor in pedidos.values_list('criado_em', 'valor_total'):
        dt = timezone.localtime(criado)
        chave = dt.hour if periodo == 'diario' else (dt.weekday() + 1) % 7
        totais[chave] += float(valor)
    if not totais:
        return None
    chave = max(totais, key=totais.get)
    if periodo == 'diario':
        return {'rotulo': 'Melhor horário de vendas', 'valor': f'{chave}h às {chave + 1}h'}
    return {'rotulo': 'Melhor dia de vendas', 'valor': DIAS_SEMANA_EXTENSO[chave]}


def estatisticas_painel(vendedor, periodo):
    if periodo not in dict(PERIODOS):
        periodo = PERIODO_PADRAO
    agora = timezone.localtime()
    vendas = vendas_do_vendedor(vendedor)
    inicio, inicio_ant, fim_eq, fim_ant = limites_periodo(periodo, agora)

    pedidos_atual = vendas if inicio is None else vendas.filter(criado_em__gte=inicio)
    atual = _resumo(pedidos_atual)

    if inicio_ant is not None:
        anterior = _resumo(vendas.filter(criado_em__gte=inicio_ant, criado_em__lt=fim_eq))
        comparacao = {
            'bruto': _variacao(atual['bruto'], anterior['bruto']),
            'liquido': _variacao(atual['liquido'], anterior['liquido']),
            'pedidos_diff': atual['pedidos'] - anterior['pedidos'],
            'unidades_diff': atual['unidades'] - anterior['unidades'],
            'ticket_medio': _variacao(atual['ticket_medio'], anterior['ticket_medio']),
        }
    else:
        anterior, comparacao = None, None

    mais_vendidos = (
        pedidos_atual.values('produto__id', 'produto__titulo')
        .annotate(total_qtd=Sum('quantidade'), total_val=Sum('valor_total'))
        .order_by('-total_qtd', '-total_val')[:5]
    )

    return {
        'periodo': periodo,
        'periodos': PERIODOS,
        'periodo_label': dict(PERIODOS)[periodo],
        'textos': TEXTOS[periodo],
        'kpi': atual,
        'kpi_anterior': anterior,
        'comparacao': comparacao,
        'grafico': _serie_grafico(vendas, periodo, agora, inicio, inicio_ant, fim_ant),
        'mais_vendidos': mais_vendidos,
        'melhor_momento': _melhor_momento(pedidos_atual, periodo),
    }
