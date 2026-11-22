from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Avg
from .models import Product, CATEGORIAS
from .forms import ProductForm
from orders.models import Review
import random


def home_view(request):
    products = Product.objects.filter(ativo=True)[:8]
    return render(request, 'catalog/home.html', {'products': products, 'categorias': CATEGORIAS})


def product_list_view(request):
    products = Product.objects.filter(ativo=True)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(titulo__icontains=q) | Q(descricao__icontains=q) | Q(categoria__icontains=q)
        )

    # Category filter
    cat = request.GET.get('categoria', '')
    if cat:
        products = products.filter(categoria=cat)

    # Price filters
    preco_min = request.GET.get('preco_min', '')
    preco_max = request.GET.get('preco_max', '')
    if preco_min:
        try:
            products = products.filter(preco__gte=float(preco_min))
        except ValueError:
            pass
    if preco_max:
        try:
            products = products.filter(preco__lte=float(preco_max))
        except ValueError:
            pass

    # Sorting
    sort = request.GET.get('sort', 'relevancia')
    if sort == 'menor_preco':
        products = products.order_by('preco')
    elif sort == 'maior_preco':
        products = products.order_by('-preco')
    else:
        products = products.order_by('-criado_em')

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    return render(request, 'catalog/product_list.html', {
        'products': products_page,
        'categorias': CATEGORIAS,
        'q': q,
        'cat': cat,
        'preco_min': preco_min,
        'preco_max': preco_max,
        'sort': sort,
    })


def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk, ativo=True)
    reviews = Review.objects.filter(pedido__produto=product)
    avg_note = reviews.aggregate(avg=Avg('nota_vendedor'))['avg'] or 0
    seller_profile = product.vendedor.profile if hasattr(product.vendedor, 'profile') else None

    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_note': round(avg_note, 1),
        'total_reviews': reviews.count(),
        'seller_profile': seller_profile,
        'caracteristicas_list': [c.strip() for c in product.caracteristicas.split('\n') if c.strip()] if product.caracteristicas else [],
    })


@login_required
def product_create_view(request):
    if not hasattr(request.user, 'profile'):
        return redirect('home')
    profile = request.user.profile
    if profile.suspenso:
        from django.contrib import messages
        messages.error(request, 'Sua conta está suspensa. Não é possível criar anúncios.')
        return redirect('dashboard:overview')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendedor = request.user
            product.save()
            from django.contrib import messages
            messages.success(request, 'Anúncio publicado com sucesso!')
            return redirect('catalog:product_detail', pk=product.pk)
    else:
        form = ProductForm()

    return render(request, 'catalog/product_create.html', {'form': form})


def calculate_frete_view(request):
    cep = request.GET.get('cep', '').replace('-', '').strip()
    product_id = request.GET.get('product_id', '')

    if not cep or len(cep) < 8:
        return JsonResponse({'error': 'CEP inválido'})

    # Simulated freight calculator
    seed = sum(ord(c) for c in cep)
    random.seed(seed)

    base_pac = round(random.uniform(15, 35), 2)
    base_sedex = round(base_pac * 1.8, 2)
    base_express = round(base_pac * 2.2, 2)

    try:
        product = Product.objects.get(pk=product_id)
        if product.frete_gratis:
            base_pac = 0
    except (Product.DoesNotExist, ValueError):
        pass

    options = [
        {
            'method': 'PAC',
            'price': 'R$ ' + f'{base_pac:.2f}'.replace('.', ',') if base_pac > 0 else 'Grátis',
            'price_value': base_pac,
            'days': random.randint(7, 15),
        },
        {
            'method': 'SEDEX',
            'price': 'R$ ' + f'{base_sedex:.2f}'.replace('.', ','),
            'price_value': base_sedex,
            'days': random.randint(3, 7),
        },
        {
            'method': 'Transportadora AVAD Express',
            'price': 'R$ ' + f'{base_express:.2f}'.replace('.', ','),
            'price_value': base_express,
            'days': random.randint(1, 3),
        },
    ]
    return JsonResponse({'options': options})