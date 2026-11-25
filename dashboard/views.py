from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from orders.models import Order, Review
from orders.services import estatisticas_vendedor
from catalog.models import Product
from finance.models import PaymentSplit
import datetime
import json


@login_required
def overview_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    # All seller orders
    vendas = Order.objects.filter(vendedor=user).exclude(status='cancelado')

    # Date ranges
    now = timezone.now()
    inicio_ano = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0)
    inicio_semana = now - datetime.timedelta(days=now.weekday())

    # KPIs
    vendas_ano = vendas.filter(criado_em__gte=inicio_ano).aggregate(s=Sum('valor_total'))['s'] or 0
    vendas_mes = vendas.filter(criado_em__gte=inicio_mes).aggregate(s=Sum('valor_total'))['s'] or 0
    vendas_semana = vendas.filter(criado_em__gte=inicio_semana).aggregate(s=Sum('valor_total'))['s'] or 0

    splits = PaymentSplit.objects.filter(pedido__vendedor=user).exclude(status_repasse='estornado')
    receita_liquida = splits.aggregate(s=Sum('valor_liquido_vendedor'))['s'] or 0
    total_pedidos = vendas.count()

    # Sales evolution chart data (Months 1 to 12)
    meses_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    ano_atual_dados = [0] * 12
    ano_anterior_dados = [0] * 12

    # Fill year data
    for m in range(1, 13):
        total_m = vendas.filter(criado_em__year=now.year, criado_em__month=m).aggregate(s=Sum('valor_total'))['s'] or 0
        ano_atual_dados[m - 1] = float(total_m)
        # Mock previous year data for comparison if needed
        ano_anterior_dados[m - 1] = round(float(total_m) * 0.85 if total_m else (m * 420.0), 2)

    # Reviews summary
    reviews = Review.objects.filter(vendedor=user)
    total_rev = reviews.count()
    avg_note = reviews.aggregate(avg=Avg('nota_vendedor'))['avg'] or 0
    ultimo_comentario = reviews.exclude(comentario_vendedor='').first()

    dist_stars = {}
    for i in range(1, 6):
        c = reviews.filter(nota_vendedor=i).count()
        dist_stars[i] = {
            'count': c,
            'percent': round((c / total_rev) * 100) if total_rev else 0
        }

    # Best sellers (last 30 days)
    trinta_dias = now - datetime.timedelta(days=30)
    mais_vendidos = (
        Order.objects.filter(vendedor=user, criado_em__gte=trinta_dias)
        .values('produto__id', 'produto__titulo', 'produto__preco')
        .annotate(total_qtd=Sum('quantidade'), total_val=Sum('valor_total'))
        .order_by('-total_qtd')[:5]
    )

    # Quick insights
    produtos_baixo_estoque = Product.objects.filter(vendedor=user, estoque__lte=5, ativo=True)
    meta_mensal = 25000.00
    progresso_meta = min(100, round((float(vendas_mes) / meta_mensal) * 100, 1)) if meta_mensal else 0

    # Recent orders
    pedidos_recentes = Order.objects.filter(vendedor=user).order_by('-criado_em')[:6]

    return render(request, 'dashboard/overview.html', {
        'profile': profile,
        'vendas_ano': vendas_ano,
        'vendas_mes': vendas_mes,
        'vendas_semana': vendas_semana,
        'receita_liquida': receita_liquida,
        'total_pedidos': total_pedidos,
        'meses_labels': json.dumps(meses_labels),
        'ano_atual_dados': json.dumps(ano_atual_dados),
        'ano_anterior_dados': json.dumps(ano_anterior_dados),
        'avg_note': round(avg_note, 1),
        'total_rev': total_rev,
        'ultimo_comentario': ultimo_comentario,
        'dist_stars': dist_stars,
        'mais_vendidos': mais_vendidos,
        'produtos_baixo_estoque': produtos_baixo_estoque,
        'meta_mensal': meta_mensal,
        'progresso_meta': progresso_meta,
        'pedidos_recentes': pedidos_recentes,
        'stats': estatisticas_vendedor(user),
    })


@login_required
def products_view(request):
    products = Product.objects.filter(vendedor=request.user, removido=False)
    return render(request, 'dashboard/products.html', {'products': products})


@login_required
def reviews_view(request):
    reviews = Review.objects.filter(vendedor=request.user).order_by('-criado_em')
    return render(request, 'dashboard/reviews.html', {'reviews': reviews})


@login_required
def customers_view(request):
    compradores = (
        Order.objects.filter(vendedor=request.user)
        .values('comprador__id', 'comprador__profile__nome', 'comprador__email')
        .annotate(total_compras=Count('id'), total_gasto=Sum('valor_total'))
        .order_by('-total_gasto')
    )
    return render(request, 'dashboard/customers.html', {'compradores': compradores})


@login_required
def settings_view(request):
    profile = getattr(request.user, 'profile', None)
    return render(request, 'dashboard/settings.html', {'profile': profile})