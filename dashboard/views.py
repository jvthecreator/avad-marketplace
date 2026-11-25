from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from orders.models import Order, Review
from orders.services import estatisticas_vendedor
from .stats import estatisticas_painel, PERIODO_PADRAO
from catalog.models import Product
from finance.models import PaymentSplit
from django import forms
from django.contrib import messages
from accounts.models import UserProfile
from decimal import Decimal
import datetime
import json



class NomeLojaForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['nome_loja']
        labels = {'nome_loja': 'Nome da loja'}
        widgets = {'nome_loja': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '64',
                                                       'placeholder': 'Ex.: Tech Store Oficial'})}
        help_texts = {'nome_loja': 'Nome que os compradores veem nos seus anúncios e no seu perfil. '
                                   'Se ficar em branco, aparece o seu nome pessoal.'}

    def clean_nome_loja(self):
        nome = (self.cleaned_data.get('nome_loja') or '').strip()
        return nome or None  # vazio = usa o nome pessoal


class MetaMensalForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['meta_mensal']
        labels = {'meta_mensal': 'Meta mensal de vendas (R$)'}
        widgets = {'meta_mensal': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'step': '0.01'})}


@login_required
def overview_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    periodo = request.GET.get('periodo', PERIODO_PADRAO)
    painel = estatisticas_painel(user, periodo)

    # Meta mensal: sempre compara com o faturamento do mês corrente, independente do período escolhido
    vendas_mes = estatisticas_painel(user, 'mensal')['kpi']['bruto'] if painel['periodo'] != 'mensal' else painel['kpi']['bruto']
    meta_mensal = profile.meta_mensal if profile else Decimal('25000.00')
    pct_meta = round(float(vendas_mes) / float(meta_mensal) * 100, 1) if meta_mensal else 0
    progresso_meta = min(100, pct_meta)  # largura da barra (não passa de 100%)

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

    produtos_baixo_estoque = Product.objects.filter(vendedor=user, estoque__lte=5, ativo=True, removido=False)
    pedidos_aguardando = Order.objects.filter(vendedor=user, status='aguardando_confirmacao').count()

    # Recent orders
    pedidos_recentes = Order.objects.filter(vendedor=user).order_by('-criado_em')[:6]

    return render(request, 'dashboard/overview.html', {
        'profile': profile,
        **painel,
        'vendas_mes': vendas_mes,
        'avg_note': round(avg_note, 1),
        'total_rev': total_rev,
        'ultimo_comentario': ultimo_comentario,
        'dist_stars': dist_stars,
        'produtos_baixo_estoque': produtos_baixo_estoque,
        'pedidos_aguardando': pedidos_aguardando,
        'meta_mensal': meta_mensal,
        'progresso_meta': progresso_meta,
        'pct_meta': pct_meta,
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
    # Cada card da página tem seu próprio formulário; o botão enviado diz qual deles salvar
    enviado = request.POST.get('form') if request.method == 'POST' else None
    loja_form = NomeLojaForm(request.POST if enviado == 'loja' else None, instance=profile)
    meta_form = MetaMensalForm(request.POST if enviado == 'meta' else None, instance=profile)

    if profile is not None and enviado == 'loja' and loja_form.is_valid():
        loja_form.save()
        messages.success(request, 'Nome da loja atualizado com sucesso.')
        return redirect('dashboard:settings')
    if profile is not None and enviado == 'meta' and meta_form.is_valid():
        meta_form.save()
        messages.success(request, 'Meta mensal atualizada com sucesso.')
        return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html', {
        'profile': profile, 'loja_form': loja_form, 'meta_form': meta_form,
    })