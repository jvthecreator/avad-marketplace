"""API REST do AVaD.

Endpoints em JSON consumidos pelo front-end em React (pasta frontend/). Usam a mesma sessão de
login do site: o navegador envia o cookie de sessão e, nos POST/PATCH/DELETE, o cabeçalho
X-CSRFToken. Cada endpoint aplica as mesmas regras de acesso das telas equivalentes.
"""
import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import dateformat, timezone
from django.utils.timesince import timesince

from accounts.roles import e_parte_do_pedido, tipo_usuario
from catalog.models import CATEGORIAS, Product
from dashboard.stats import estatisticas_painel
from disputes.forms import DisputeMessageForm
from disputes.models import Dispute, DisputeMessage
from disputes.views import salvar_evidencia
from notifications.models import Notification
from notifications.services import notificar_mensagem_disputa
from orders.cart import Cart
from orders.models import Order
from orders.services import confirmar_recebimentos_vencidos, estatisticas_vendedor

from .utils import api_login_required, corpo_json, dinheiro, erro, metodos, resposta

PRODUTOS_POR_PAGINA = 12
ETAPAS_PEDIDO = ['Aguardando pagamento', 'Confirmação vendedor', 'Preparando envio', 'Item a caminho', 'Item entregue']


def _ha_quanto_tempo(dt):
    if timezone.now() - dt < datetime.timedelta(minutes=1):
        return 'agora mesmo'
    return f"há {timesince(dt).split(',')[0]}"


def _data_hora(dt):
    return dateformat.format(timezone.localtime(dt), 'd/m/Y H:i')


# --------------------------------------------------------------------------- índice

@metodos('GET')
def indice_view(request):
    """Lista os endpoints disponíveis (documentação rápida da API)."""
    return resposta({
        'nome': 'API REST do AVaD',
        'autenticacao': 'Sessão do site (cookie) + cabeçalho X-CSRFToken em POST, PATCH e DELETE.',
        'endpoints': [
            {'metodo': 'GET', 'url': reverse('api:produtos'), 'descricao': 'Busca de produtos com filtros (q, categoria, preco_min, preco_max, sort, page).'},
            {'metodo': 'GET', 'url': reverse('api:estatisticas'), 'descricao': 'Estatísticas do painel do vendedor (periodo=total|anual|mensal|semanal|diario).'},
            {'metodo': 'GET', 'url': reverse('api:notificacoes'), 'descricao': 'Notificações do papel atual e quantas não foram lidas.'},
            {'metodo': 'POST', 'url': '/api/notificacoes/<id>/lida/', 'descricao': 'Marca uma notificação como lida.'},
            {'metodo': 'POST', 'url': reverse('api:notificacoes_marcar_todas'), 'descricao': 'Marca todas como lidas.'},
            {'metodo': 'GET, POST', 'url': reverse('api:carrinho'), 'descricao': 'Itens do carrinho; POST adiciona {produto_id, quantidade}.'},
            {'metodo': 'PATCH, DELETE', 'url': '/api/carrinho/<produto_id>/', 'descricao': 'Altera a quantidade {quantidade} ou remove o item.'},
            {'metodo': 'GET, POST', 'url': '/api/disputas/<id>/mensagens/', 'descricao': 'Mensagens e evidências da disputa; POST envia mensagem (multipart, com evidência opcional).'},
            {'metodo': 'GET', 'url': '/api/pedidos/<id>/rastreio/', 'descricao': 'Estado do pedido e histórico de rastreio.'},
        ],
    })


# --------------------------------------------------------------------------- catálogo

def _produto_json(p):
    perfil = getattr(p.vendedor, 'profile', None)
    return {
        'id': p.id,
        'titulo': p.titulo,
        'categoria': p.categoria,
        'categoria_nome': p.get_categoria_display(),
        'preco': dinheiro(p.preco),
        'parcelas': p.parcelas_sem_juros,
        'frete_gratis': p.frete_gratis,
        'estoque': p.estoque,
        'imagem': p.imagem.url if p.imagem else None,
        'nota_media': float(p.nota_media),
        'total_avaliacoes': p.total_avaliacoes,
        'url': reverse('catalog:product_detail', args=[p.id]),
        'vendedor': {
            'id': p.vendedor_id,
            'nome': (perfil.nome_loja or perfil.nome) if perfil else p.vendedor.username,
            'url': reverse('accounts:seller_profile', args=[p.vendedor_id]),
        },
    }


def _numero(valor):
    try:
        return float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        return None


@metodos('GET')
def produtos_view(request):
    """Mesmos filtros da página do catálogo, para a busca ao vivo."""
    produtos = Product.objects.filter(ativo=True).select_related('vendedor__profile')

    q = request.GET.get('q', '').strip()
    if q:
        produtos = produtos.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q) | Q(categoria__icontains=q))
    categoria = request.GET.get('categoria', '')
    if categoria:
        produtos = produtos.filter(categoria=categoria)
    preco_min = _numero(request.GET.get('preco_min'))
    if preco_min is not None:
        produtos = produtos.filter(preco__gte=preco_min)
    preco_max = _numero(request.GET.get('preco_max'))
    if preco_max is not None:
        produtos = produtos.filter(preco__lte=preco_max)

    ordem = request.GET.get('sort', 'relevancia')
    produtos = produtos.order_by({'menor_preco': 'preco', 'maior_preco': '-preco'}.get(ordem, '-criado_em'))

    pagina = Paginator(produtos, PRODUTOS_POR_PAGINA).get_page(request.GET.get('page', 1))
    return resposta({
        'total': pagina.paginator.count,
        'pagina': pagina.number,
        'paginas': pagina.paginator.num_pages,
        'resultados': [_produto_json(p) for p in pagina],
        'categorias': [{'valor': v, 'nome': n} for v, n in CATEGORIAS],
    })


# --------------------------------------------------------------------------- painel do vendedor

def estatisticas_json(vendedor, periodo):
    """Estatísticas do painel em formato JSON (usado pela API e pelo primeiro carregamento da página)."""
    p = estatisticas_painel(vendedor, periodo)

    def kpi(d):
        if d is None:
            return None
        return {
            'bruto': dinheiro(d['bruto']),
            'liquido': dinheiro(d['liquido']),
            'pedidos': d['pedidos'],
            'unidades': d['unidades'],
            'ticket_medio': dinheiro(d['ticket_medio']),
            'pct_liquido': d['pct_liquido'],
        }

    return {
        'periodo': p['periodo'],
        'periodo_label': p['periodo_label'],
        'periodos': [{'valor': v, 'nome': n} for v, n in p['periodos']],
        'textos': p['textos'],
        'kpi': kpi(p['kpi']),
        'kpi_anterior': kpi(p['kpi_anterior']),
        'comparacao': p['comparacao'],
        'grafico': p['grafico'],
        'mais_vendidos': [
            {'produto_id': i['produto__id'], 'titulo': i['produto__titulo'],
             'quantidade': i['total_qtd'], 'valor': dinheiro(i['total_val'])}
            for i in p['mais_vendidos']
        ],
        'melhor_momento': p['melhor_momento'],
        'reputacao': estatisticas_vendedor(vendedor),
    }


@metodos('GET')
@api_login_required(papel='vendedor')
def estatisticas_view(request):
    return resposta(estatisticas_json(request.user, request.GET.get('periodo', 'mensal')))


# --------------------------------------------------------------------------- notificações

def _notificacoes_do_usuario(request):
    return Notification.objects.filter(usuario=request.user, tipo_usuario=tipo_usuario(request))


def _notificacoes_json(request, limite=8):
    qs = _notificacoes_do_usuario(request)
    return {
        'nao_lidas': qs.filter(lida=False).count(),
        'notificacoes': [
            {
                'id': n.id,
                'titulo': n.titulo,
                'mensagem': n.mensagem,
                'categoria': n.categoria,
                'lida': n.lida,
                'criada_em': n.criada_em.isoformat(),
                'quando': _ha_quanto_tempo(n.criada_em),
                'abrir_url': reverse('notifications:open', args=[n.id]),
            }
            for n in qs[:limite]
        ],
        'ver_todas_url': reverse('notifications:list'),
    }


@metodos('GET')
@api_login_required()
def notificacoes_view(request):
    try:
        limite = max(1, min(int(request.GET.get('limite', 8)), 50))
    except ValueError:
        limite = 8
    return resposta(_notificacoes_json(request, limite))


@metodos('POST')
@api_login_required()
def notificacao_lida_view(request, pk):
    notificacao = _notificacoes_do_usuario(request).filter(pk=pk).first()
    if notificacao is None:
        return erro('Notificação não encontrada.', status=404)
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save(update_fields=['lida'])
    return resposta(_notificacoes_json(request))


@metodos('POST')
@api_login_required()
def notificacoes_marcar_todas_view(request):
    _notificacoes_do_usuario(request).filter(lida=False).update(lida=True)
    return resposta(_notificacoes_json(request))


# --------------------------------------------------------------------------- carrinho

def _carrinho_json(request, aviso=''):
    itens = Cart(request).items()
    return {
        'itens': [
            {
                'produto_id': i['product'].id,
                'titulo': i['product'].titulo,
                'preco': dinheiro(i['product'].preco),
                'quantidade': i['qtd'],
                'estoque': i['product'].estoque,
                'disponivel': i['disponivel'],
                'subtotal': dinheiro(i['subtotal']),
                'imagem': i['product'].imagem.url if i['product'].imagem else None,
                'url': reverse('catalog:product_detail', args=[i['product'].id]),
                'comprar_url': reverse('orders:checkout', args=[i['product'].id]) + f"?qtd={i['qtd']}",
            }
            for i in itens
        ],
        'unidades': sum(i['qtd'] for i in itens if i['disponivel']),
        'subtotal': dinheiro(sum((i['subtotal'] for i in itens if i['disponivel']), 0)),
        'finalizar_url': reverse('orders:cart_checkout'),
        'aviso': aviso,
    }


def _quantidade(dados, padrao=None):
    try:
        return int(dados.get('quantidade', padrao))
    except (TypeError, ValueError):
        return None


@metodos('GET', 'POST')
@api_login_required(papel='comprador')
def carrinho_view(request):
    if request.method == 'GET':
        return resposta(_carrinho_json(request))

    dados = corpo_json(request)
    if dados is None:
        return erro('JSON inválido.')
    produto = Product.objects.filter(pk=dados.get('produto_id'), ativo=True).first()
    if produto is None:
        return erro('Produto não encontrado.', status=404)
    if produto.estoque <= 0:
        return erro('Produto esgotado.', status=409)
    qtd = _quantidade(dados, 1)
    if qtd is None or qtd < 1:
        return erro('Quantidade inválida.')

    carrinho = Cart(request)
    desejada = carrinho.get_qtd(produto.id) + qtd
    carrinho.set(produto.id, min(desejada, produto.estoque))
    aviso = f'Quantidade ajustada ao estoque disponível ({produto.estoque} unid.).' if desejada > produto.estoque else ''
    return resposta(_carrinho_json(request, aviso), status=201)


@metodos('PATCH', 'DELETE')
@api_login_required(papel='comprador')
def carrinho_item_view(request, produto_id):
    carrinho = Cart(request)
    if request.method == 'DELETE':
        carrinho.remove(produto_id)
        return resposta(_carrinho_json(request))

    dados = corpo_json(request)
    qtd = _quantidade(dados or {})
    if qtd is None:
        return erro('Informe a quantidade.')
    produto = Product.objects.filter(pk=produto_id, ativo=True).first()
    if produto is None:
        carrinho.remove(produto_id)
        return erro('Produto não está mais disponível.', status=404)

    aviso = ''
    if qtd < 1 or produto.estoque <= 0:
        carrinho.remove(produto.id)
    else:
        carrinho.set(produto.id, min(qtd, produto.estoque))
        if qtd > produto.estoque:
            aviso = f'Quantidade ajustada ao estoque disponível ({produto.estoque} unid.).'
    return resposta(_carrinho_json(request, aviso))


# --------------------------------------------------------------------------- chat da disputa

def _nome(user):
    perfil = getattr(user, 'profile', None)
    return perfil.nome if perfil else user.username


def _disputa_json(request, disputa):
    return {
        'disputa': {
            'id': disputa.id,
            'codigo': disputa.codigo,
            'status': disputa.status,
            'status_texto': disputa.get_status_display(),
            'aberta': disputa.status == 'em_analise',
            'sla_restante': disputa.sla_restante,
        },
        'papel': tipo_usuario(request),
        'pode_enviar': disputa.status == 'em_analise',
        'mensagens': [
            {
                'id': m.id,
                'papel': m.papel,
                'papel_texto': m.get_papel_display(),
                'autor': _nome(m.autor),
                'minha': m.autor_id == request.user.id,
                'texto': m.mensagem,
                'criado_em': m.criado_em.isoformat(),
                'criado_em_texto': _data_hora(m.criado_em),
            }
            for m in disputa.messages.select_related('autor__profile').order_by('criado_em')
        ],
        'evidencias': [
            {
                'id': e.id,
                'titulo': e.titulo,
                'autor': _nome(e.autor),
                'tipo': e.tipo,
                'url': e.arquivo.url if e.arquivo else None,
                'criado_em_texto': _data_hora(e.criado_em),
            }
            for e in disputa.evidences.select_related('autor__profile')
        ],
    }


@metodos('GET', 'POST')
@api_login_required()
def disputa_mensagens_view(request, disputa_id):
    disputa = Dispute.objects.filter(pk=disputa_id).first()
    if disputa is None:
        return erro('Disputa não encontrada.', status=404)
    if not e_parte_do_pedido(request, disputa.comprador, disputa.vendedor):
        return erro('Você não participa desta disputa.', status=403)

    if request.method == 'GET':
        return resposta(_disputa_json(request, disputa))

    if disputa.status != 'em_analise':
        return erro('Esta disputa já foi encerrada pela mediação.', status=409)
    form = DisputeMessageForm(request.POST, request.FILES)
    if not form.is_valid():
        return erro('Corrija os campos destacados.', erros={c: [str(m) for m in ms] for c, ms in form.errors.items()})

    papel = tipo_usuario(request)
    DisputeMessage.objects.create(disputa=disputa, autor=request.user, papel=papel, mensagem=form.cleaned_data['mensagem'])
    descricao = 'Documento anexado pela Mediação' if papel == 'mediador' else f'Anexo enviado por {_nome(request.user)} ({papel})'
    salvar_evidencia(form, disputa, request.user, descricao)
    notificar_mensagem_disputa(disputa, papel)
    return resposta(_disputa_json(request, disputa), status=201)


# --------------------------------------------------------------------------- rastreio

@metodos('GET')
@api_login_required()
def rastreio_view(request, pedido_id):
    confirmar_recebimentos_vencidos()
    pedido = Order.objects.filter(pk=pedido_id).first()
    if pedido is None:
        return erro('Pedido não encontrado.', status=404)
    if not e_parte_do_pedido(request, pedido.comprador, pedido.vendedor):
        return erro('Você não participa deste pedido.', status=403)

    previsao = timezone.localtime(pedido.criado_em) + datetime.timedelta(days=pedido.prazo_dias)
    texto_badge, cor_badge = pedido.status_display_badge
    return resposta({
        'pedido': {
            'id': pedido.id,
            'codigo': pedido.codigo,
            'codigo_rastreio': pedido.codigo_rastreio,
            'status': pedido.status,
            'status_texto': texto_badge,
            'status_cor': cor_badge,
            'etapa': pedido.status_step,  # 0 a 4; -1 = cancelado
            'cancelado': pedido.status == 'cancelado',
            'previsao_entrega': dateformat.format(previsao, r'd \d\e F \d\e Y'),
        },
        'etapas': ETAPAS_PEDIDO,
        'eventos': [
            {
                'id': e.id,
                'titulo': e.titulo,
                'descricao': e.descricao,
                'local': e.local,
                'data_hora_texto': dateformat.format(timezone.localtime(e.data_hora), r'd/m/Y \à\s H:i'),
            }
            for e in pedido.tracking_events.order_by('-data_hora')
        ],
        'atualizado_em': timezone.now().isoformat(),
    })
