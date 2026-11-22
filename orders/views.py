from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Order, TrackingEvent, Review, RefundRequest, generate_order_code, generate_tracking_code
from .forms import CheckoutForm, RefundForm, ReviewForm
from catalog.models import Product
from accounts.models import SavedCard
from finance.models import PaymentSplit
from decimal import Decimal
from django.views.decorators.http import require_POST
from .cart import Cart
from django.db import transaction
import datetime


@login_required
def checkout_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, ativo=True)
    saved_cards = SavedCard.objects.filter(usuario=request.user)

    qtd = int(request.GET.get('qtd', 1))
    if qtd < 1:
        qtd = 1

    # resumo (itens, subtotal, fretes) usado pelo template
    extra = _summary_context([{'product': product, 'qtd': qtd, 'subtotal': product.preco * qtd}])
    extra['is_cart'] = False

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            simulacao = form.cleaned_data['simulacao_gateway']

            # Simulator checks
            if simulacao == 'negar':
                messages.error(request, 'Transação negada pela instituição emissora do cartão. Verifique o limite ou tente outro cartão.')
                return render(request, 'orders/checkout.html', {
                    'product': product,
                    'form': form,
                    'saved_cards': saved_cards,
                    'qtd': qtd,
                    **extra,
                })
            elif simulacao == 'timeout':
                messages.error(request, 'Tempo limite de resposta excedido (> 40s) na comunicação com o banco emissor. Tente novamente.')
                return render(request, 'orders/checkout.html', {
                    'product': product,
                    'form': form,
                    'saved_cards': saved_cards,
                    'qtd': qtd,
                    **extra,
                })

            # Calculation
            metodo = form.cleaned_data['metodo_frete']
            frete_map = {
                'pac': (Decimal('0.00') if product.frete_gratis else Decimal('22.50'), 8),
                'sedex': (Decimal('45.90'), 3),
                'avad_express': (Decimal('58.00'), 2),
            }
            valor_frete, prazo_dias = frete_map.get(metodo, (Decimal('20.00'), 7))

            subtotal = product.preco * qtd
            total = subtotal + valor_frete

            forma_pgto = form.cleaned_data['forma_pagamento']
            parcelas = int(form.cleaned_data.get('parcelas') or 1)

            # Saved card or new card
            if forma_pgto == 'cartao' and form.cleaned_data.get('salvar_cartao'):
                num = form.cleaned_data.get('numero_cartao', '').replace(' ', '')
                if num and len(num) >= 4:
                    SavedCard.objects.create(
                        usuario=request.user,
                        ultimos_digitos=num[-4:],
                        bandeira='Mastercard' if num.startswith('5') else 'Visa',
                        nome_impresso=form.cleaned_data.get('nome_cartao', 'TITULAR'),
                        validade=form.cleaned_data.get('validade_cartao', '12/28'),
                        cpf_titular=form.cleaned_data.get('cpf_titular', '000.000.000-00')
                    )

            # Create Order
            endereco = f"{form.cleaned_data['rua']}, {form.cleaned_data.get('complemento', '')} - {form.cleaned_data['bairro']}, {form.cleaned_data['cidade']}/{form.cleaned_data['estado']}"
            rastreio = generate_tracking_code()

            order = Order.objects.create(
                comprador=request.user,
                vendedor=product.vendedor,
                produto=product,
                quantidade=qtd,
                preco_unitario=product.preco,
                valor_frete=valor_frete,
                metodo_frete=metodo,
                prazo_dias=prazo_dias,
                valor_total=total,
                forma_pagamento=forma_pgto,
                parcelas=parcelas,
                cep_entrega=form.cleaned_data['cep'],
                endereco_entrega=endereco,
                codigo_rastreio=rastreio,
                status='aguardando_confirmacao'
            )

            # Decrement stock
            if product.estoque >= qtd:
                product.estoque -= qtd
                product.save()

            # Tracking event inicial
            TrackingEvent.objects.create(
                pedido=order,
                titulo='Pagamento autorizado',
                descricao=f'Pagamento aprovado via {order.get_forma_pagamento_display()}. Aguardando confirmação da loja.',
                local='Sistema Central AVaD'
            )

            # PRO006 Split Financeiro
            comissao = round(subtotal * Decimal('0.065'), 2)
            liquido_vendedor = subtotal - comissao

            # Check escrow / conta bloqueada
            seller_profile = getattr(product.vendedor, 'profile', None)
            if seller_profile and seller_profile.conta_bancaria_bloqueada:
                status_repasse = 'retido'
            else:
                status_repasse = 'programado'

            PaymentSplit.objects.create(
                pedido=order,
                total_pago=total,
                comissao_marketplace=comissao,
                valor_frete_logistica=valor_frete,
                valor_liquido_vendedor=liquido_vendedor,
                status_repasse=status_repasse
            )

            Cart(request).remove(product.id)  # tira do carrinho o item comprado
            messages.success(request, f'Compra realizada com sucesso! Pedido {order.codigo} gerado.')
            return redirect('orders:tracking', order_id=order.id)
    else:
        initial_data = {
            'quantidade': qtd,
            'metodo_frete': 'pac',
            'forma_pagamento': 'cartao',
            'simulacao_gateway': 'aprovar',
            'endereco_cobranca_igual': True,
        }
        form = CheckoutForm(initial=initial_data)

    return render(request, 'orders/checkout.html', {
        'product': product,
        'form': form,
        'saved_cards': saved_cards,
        'qtd': qtd,
        **extra,
    })


@login_required
def my_orders_view(request):
    orders = Order.objects.filter(comprador=request.user)

    # Filter tab
    aba = request.GET.get('aba', 'todos')
    if aba == 'em_andamento':
        orders = orders.filter(status__in=['aguardando_pagamento', 'aguardando_confirmacao', 'preparando', 'a_caminho'])
    elif aba == 'entregues':
        orders = orders.filter(status='entregue')
    elif aba == 'cancelados':
        orders = orders.filter(status='cancelado')

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(codigo__icontains=q) | orders.filter(produto__titulo__icontains=q)

    # Period filter
    periodo = request.GET.get('periodo', '6m')
    if periodo == '6m':
        seis_meses_atras = timezone.now() - datetime.timedelta(days=180)
        orders = orders.filter(criado_em__gte=seis_meses_atras)

    return render(request, 'orders/my_orders.html', {
        'orders': orders,
        'aba': aba,
        'q': q,
        'periodo': periodo,
    })


@login_required
def tracking_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if order.comprador != request.user and order.vendedor != request.user and not (hasattr(request.user, 'profile') and request.user.profile.is_mediador):
        messages.error(request, 'Acesso não autorizado.')
        return redirect('orders:my_orders')

    events = order.tracking_events.all().order_by('-data_hora')
    previsao_entrega = order.criado_em + datetime.timedelta(days=order.prazo_dias)

    return render(request, 'orders/tracking.html', {
        'order': order,
        'events': events,
        'previsao_entrega': previsao_entrega,
    })


@login_required
def confirm_receipt_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, comprador=request.user)
    if request.method == 'POST':
        order.recebimento_confirmado = True
        order.status = 'entregue'
        order.save()

        TrackingEvent.objects.create(
            pedido=order,
            titulo='Entrega confirmada pelo comprador',
            descricao='O comprador confirmou o recebimento do pacote em perfeito estado.',
            local=order.cep_entrega
        )

        messages.success(request, 'Recebimento confirmado! Por favor, avalie a sua experiência.')
        return redirect('orders:review', order_id=order.id)

    return render(request, 'orders/confirm_receipt_modal.html', {'order': order})


@login_required
def review_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, comprador=request.user)

    # Check if already reviewed
    existing_review = getattr(order, 'review', None)
    if existing_review:
        messages.info(request, 'Você já avaliou este pedido.')
        return redirect('orders:my_orders')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.create(
                pedido=order,
                comprador=request.user,
                vendedor=order.vendedor,
                nota_vendedor=form.cleaned_data['nota_vendedor'],
                comentario_vendedor=form.cleaned_data['comentario_vendedor'],
                nota_transporte=form.cleaned_data['nota_transporte'],
                comentario_transporte=form.cleaned_data['comentario_transporte']
            )
            messages.success(request, 'Avaliação enviada com sucesso! Obrigado pela colaboração.')
            return redirect('accounts:seller_profile', user_id=order.vendedor.id)
    else:
        form = ReviewForm()

    return render(request, 'orders/review.html', {
        'order': order,
        'form': form,
    })


@login_required
def refund_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, comprador=request.user)

    if order.status == 'cancelado':
        messages.warning(request, 'Este pedido já foi cancelado ou reembolsado.')
        return redirect('orders:my_orders')

    if request.method == 'POST':
        form = RefundForm(request.POST)
        if form.is_valid():
            refund = RefundRequest.objects.create(
                pedido=order,
                motivo=form.cleaned_data['motivo'],
                comentario=form.cleaned_data['comentario'],
                valor_reembolso=order.valor_total,
                status='solicitacao_enviada'
            )
            messages.success(request, f'Solicitação de reembolso {refund.protocolo} enviada.')
            return redirect('orders:refund_status', refund_id=refund.id)
    else:
        form = RefundForm()

    return render(request, 'orders/refund.html', {
        'order': order,
        'form': form,
    })


@login_required
def refund_status_view(request, refund_id):
    refund = get_object_or_404(RefundRequest, pk=refund_id)
    if refund.pedido.comprador != request.user and refund.pedido.vendedor != request.user:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('orders:my_orders')

    return render(request, 'orders/refund_status.html', {
        'refund': refund,
        'order': refund.pedido,
    })


@login_required
def seller_orders_view(request):
    orders = Order.objects.filter(vendedor=request.user)
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, 'orders/seller_orders.html', {
        'orders': orders,
        'status_filter': status_filter,
    })


@login_required
def advance_status_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, vendedor=request.user)
    novo_status = request.POST.get('status') or request.GET.get('status')

    status_transitions = {
        'aguardando_confirmacao': ('preparando', 'Pedido confirmado pela loja', 'O vendedor confirmou o pedido e iniciou a separação em estoque.'),
        'preparando': ('a_caminho', 'Objeto postado e a caminho', f'Pacote despachado via {order.get_metodo_frete_display()} com código {order.codigo_rastreio}.'),
        'a_caminho': ('entregue', 'Objeto entregue ao destinatário', 'Entrega finalizada com sucesso no endereço cadastrado.'),
    }

    if novo_status and novo_status in ['preparando', 'a_caminho', 'entregue', 'cancelado']:
        order.status = novo_status
        order.save()

        # Add event
        event_info = {
            'preparando': ('Pedido confirmado pela loja', 'Vendedor iniciou a preparação do pacote.'),
            'a_caminho': ('Objeto despachado', f'Postado sob código {order.codigo_rastreio}.'),
            'entregue': ('Objeto entregue', 'Entrega efetuada com sucesso.'),
            'cancelado': ('Pedido cancelado', 'Cancelamento registrado.'),
        }.get(novo_status, ('Atualização de status', 'Status alterado'))

        TrackingEvent.objects.create(
            pedido=order,
            titulo=event_info[0],
            descricao=event_info[1],
            local='Centro de Distribuição AVaD'
        )
        messages.success(request, f'Status do pedido {order.codigo} atualizado para {order.get_status_display()}.')
    elif order.status in status_transitions:
        next_status, title, desc = status_transitions[order.status]
        order.status = next_status
        order.save()

        TrackingEvent.objects.create(
            pedido=order,
            titulo=title,
            descricao=desc,
            local='Centro de Distribuição'
        )
        messages.success(request, f'Status do pedido {order.codigo} avançado para {order.get_status_display()}.')

    return redirect('orders:seller_orders')


@login_required
def refund_action_view(request, refund_id, action):
    refund = get_object_or_404(RefundRequest, pk=refund_id, pedido__vendedor=request.user)

    if action == 'aprovar':
        refund.status = 'valor_devolvido'
        refund.save()
        order = refund.pedido
        order.status = 'cancelado'
        order.save()

        if hasattr(order, 'split'):
            split = order.split
            split.status_repasse = 'estornado'
            split.save()

        TrackingEvent.objects.create(
            pedido=order,
            titulo='Reembolso aprovado pelo vendedor',
            descricao=f'Estorno de R$ {refund.valor_reembolso} efetuado integralmente.',
            local='Central Financeira AVaD'
        )
        messages.success(request, f'Reembolso {refund.protocolo} aprovado e estorno concluído.')
    elif action == 'negar':
        refund.status = 'negado'
        refund.save()
        messages.warning(request, f'Reembolso {refund.protocolo} negado.')

    return redirect('orders:seller_orders')


# ---------------- CARRINHO ----------------

def _parse_qtd(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@login_required
def cart_view(request):
    items = Cart(request).items()
    total = sum(i['subtotal'] for i in items if i['disponivel'])
    return render(request, 'orders/cart.html', {'items': items, 'total': total})


@login_required
@require_POST
def cart_add_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, ativo=True)
    if product.estoque <= 0:
        messages.error(request, 'Produto esgotado.')
        return redirect('catalog:product_detail', pk=product.id)

    qtd = max(_parse_qtd(request.POST.get('qtd')), 1)
    cart = Cart(request)
    desejada = cart.get_qtd(product.id) + qtd
    final = min(desejada, product.estoque)
    cart.set(product.id, final)

    if desejada > product.estoque:
        messages.warning(request, f'Quantidade ajustada ao estoque disponível ({product.estoque} unid.).')
    else:
        messages.success(request, f'"{product.titulo}" adicionado ao carrinho.')
    return redirect('orders:cart')


@login_required
@require_POST
def cart_update_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, ativo=True)
    qtd = _parse_qtd(request.POST.get('qtd'))
    cart = Cart(request)

    if qtd < 1 or product.estoque <= 0:
        cart.remove(product.id)
        messages.info(request, f'"{product.titulo}" removido do carrinho.')
    else:
        final = min(qtd, product.estoque)
        cart.set(product.id, final)
        if qtd > product.estoque:
            messages.warning(request, f'Quantidade ajustada ao estoque disponível ({product.estoque} unid.).')
    return redirect('orders:cart')


@login_required
@require_POST
def cart_remove_view(request, product_id):
    Cart(request).remove(product_id)
    messages.info(request, 'Item removido do carrinho.')
    return redirect('orders:cart')


# ---------------- CHECKOUT DO CARRINHO (todos os itens de uma vez) ----------------

def _frete_e_prazo(metodo, product):
    """Mesma tabela de frete do checkout de 1 produto: (valor, prazo em dias)."""
    if metodo == 'pac':
        return (Decimal('0.00') if product.frete_gratis else Decimal('22.50'), 8)
    tabela = {
        'sedex': (Decimal('45.90'), 3),
        'avad_express': (Decimal('58.00'), 2),
    }
    return tabela.get(metodo, (Decimal('20.00'), 7))


def _summary_context(items):
    """items: lista de dicts {product, qtd, subtotal}. Calcula subtotal e frete de cada método.

    O frete é cobrado UMA vez por compra (valor de 1 produto), mesmo com vários itens.
    No PAC só é grátis se todos os produtos tiverem frete grátis.
    """
    subtotal = sum(i['subtotal'] for i in items)
    fretes = {
        m: max(_frete_e_prazo(m, i['product'])[0] for i in items)
        for m in ('pac', 'sedex', 'avad_express')
    }
    return {
        'items': items,
        'subtotal': subtotal,
        'frete_pac': fretes['pac'],
        'frete_sedex': fretes['sedex'],
        'frete_express': fretes['avad_express'],
        'total_inicial': subtotal + fretes['pac'],
    }


def _criar_pedido(request, form, product, qtd, cobrar_frete=True):
    """Cria Order + TrackingEvent + PaymentSplit de UM produto do carrinho."""
    metodo = form.cleaned_data['metodo_frete']
    valor_frete, prazo_dias = _frete_e_prazo(metodo, product)
    if not cobrar_frete:
        valor_frete = Decimal('0.00')  # o frete da compra já foi cobrado em outro pedido
    subtotal = product.preco * qtd
    total = subtotal + valor_frete

    forma_pgto = form.cleaned_data['forma_pagamento']
    parcelas = int(form.cleaned_data.get('parcelas') or 1)

    endereco = f"{form.cleaned_data['rua']}, {form.cleaned_data.get('complemento', '')} - {form.cleaned_data['bairro']}, {form.cleaned_data['cidade']}/{form.cleaned_data['estado']}"

    order = Order.objects.create(
        comprador=request.user,
        vendedor=product.vendedor,
        produto=product,
        quantidade=qtd,
        preco_unitario=product.preco,
        valor_frete=valor_frete,
        metodo_frete=metodo,
        prazo_dias=prazo_dias,
        valor_total=total,
        forma_pagamento=forma_pgto,
        parcelas=parcelas,
        cep_entrega=form.cleaned_data['cep'],
        endereco_entrega=endereco,
        codigo_rastreio=generate_tracking_code(),
        status='aguardando_confirmacao'
    )

    if product.estoque >= qtd:
        product.estoque -= qtd
        product.save()

    TrackingEvent.objects.create(
        pedido=order,
        titulo='Pagamento autorizado',
        descricao=f'Pagamento aprovado via {order.get_forma_pagamento_display()}. Aguardando confirmação da loja.',
        local='Sistema Central AVaD'
    )

    comissao = round(subtotal * Decimal('0.065'), 2)
    liquido_vendedor = subtotal - comissao
    seller_profile = getattr(product.vendedor, 'profile', None)
    if seller_profile and seller_profile.conta_bancaria_bloqueada:
        status_repasse = 'retido'
    else:
        status_repasse = 'programado'

    PaymentSplit.objects.create(
        pedido=order,
        total_pago=total,
        comissao_marketplace=comissao,
        valor_frete_logistica=valor_frete,
        valor_liquido_vendedor=liquido_vendedor,
        status_repasse=status_repasse
    )
    return order


@login_required
def cart_checkout_view(request):
    cart = Cart(request)
    cart_items = [i for i in cart.items() if i['disponivel']]
    if not cart_items:
        messages.warning(request, 'Seu carrinho está vazio ou sem itens disponíveis.')
        return redirect('orders:cart')

    saved_cards = SavedCard.objects.filter(usuario=request.user)
    contexto = {'saved_cards': saved_cards, 'is_cart': True, **_summary_context(cart_items)}

    if request.method == 'POST':
        dados = request.POST.copy()
        dados['quantidade'] = '1'  # campo obrigatório do form, não usado no carrinho
        form = CheckoutForm(dados)
        if form.is_valid():
            simulacao = form.cleaned_data['simulacao_gateway']
            if simulacao == 'negar':
                messages.error(request, 'Transação negada pela instituição emissora do cartão. Verifique o limite ou tente outro cartão.')
                return render(request, 'orders/checkout.html', {'form': form, **contexto})
            elif simulacao == 'timeout':
                messages.error(request, 'Tempo limite de resposta excedido (> 40s) na comunicação com o banco emissor. Tente novamente.')
                return render(request, 'orders/checkout.html', {'form': form, **contexto})

            # Cartão salvo (uma vez por compra, não por item)
            if form.cleaned_data['forma_pagamento'] == 'cartao' and form.cleaned_data.get('salvar_cartao'):
                num = form.cleaned_data.get('numero_cartao', '').replace(' ', '')
                if num and len(num) >= 4:
                    SavedCard.objects.create(
                        usuario=request.user,
                        ultimos_digitos=num[-4:],
                        bandeira='Mastercard' if num.startswith('5') else 'Visa',
                        nome_impresso=form.cleaned_data.get('nome_cartao', 'TITULAR'),
                        validade=form.cleaned_data.get('validade_cartao', '12/28'),
                        cpf_titular=form.cleaned_data.get('cpf_titular', '000.000.000-00')
                    )

            # Um pedido por produto, tudo ou nada (se der erro em um, nenhum é criado)
            # O frete é cobrado uma única vez: fica no pedido do item de maior frete
            metodo = form.cleaned_data['metodo_frete']
            fretes = [_frete_e_prazo(metodo, i['product'])[0] for i in cart_items]
            idx_frete = fretes.index(max(fretes))

            pedidos = []
            with transaction.atomic():
                for idx, item in enumerate(cart_items):
                    pedidos.append(_criar_pedido(
                        request, form, item['product'], item['qtd'],
                        cobrar_frete=(idx == idx_frete),
                    ))
                    cart.remove(item['product'].id)

            if len(pedidos) == 1:
                messages.success(request, f'Compra realizada com sucesso! Pedido {pedidos[0].codigo} gerado.')
                return redirect('orders:tracking', order_id=pedidos[0].id)
            codigos = ', '.join(p.codigo for p in pedidos)
            messages.success(request, f'Compra realizada com sucesso! {len(pedidos)} pedidos gerados: {codigos}.')
            return redirect('orders:my_orders')
    else:
        form = CheckoutForm(initial={
            'metodo_frete': 'pac',
            'forma_pagamento': 'cartao',
            'simulacao_gateway': 'aprovar',
            'endereco_cobranca_igual': True,
        })

    return render(request, 'orders/checkout.html', {'form': form, **contexto})