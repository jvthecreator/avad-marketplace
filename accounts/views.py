from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import RegisterForm, LoginForm, PasswordChangeForm
from .models import UserProfile
from .roles import tipo_usuario, pagina_inicial
from orders.models import Review
from orders.services import estatisticas_vendedor
from django.db.models import Avg, Count, Q
import uuid


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        missing = []
        for field_name in ['nome', 'data_nascimento', 'email', 'senha', 'cpf']:
            if not request.POST.get(field_name, '').strip():
                missing.append(field_name)
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return render(request, 'accounts/register.html', {'form': form, 'missing_fields': missing})

        if form.is_valid():
            token = uuid.uuid4().hex
            request.session['pending_registration'] = {
                'nome': form.cleaned_data['nome'],
                'data_nascimento': form.cleaned_data['data_nascimento'].isoformat(),
                'email': form.cleaned_data['email'],
                'senha': form.cleaned_data['senha'],
                'cpf': form.cleaned_data['cpf'],
                'cnpj': form.cleaned_data.get('cnpj', ''),
                'token': token,
            }
            messages.info(request, 'Aguardando confirmação. Verifique seu email para finalizar o cadastro')
            return render(request, 'accounts/register.html', {
                'form': form,
                'show_verification': True,
                'verify_url': f'/accounts/verify/{token}/',
                'email': form.cleaned_data['email'],
            })
        else:
            return render(request, 'accounts/register.html', {'form': form, 'missing_fields': missing})
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form, 'missing_fields': []})


def verify_email_view(request, token):
    pending = request.session.get('pending_registration', {})
    if pending.get('token') != token:
        messages.error(request, 'Token de verificação inválido ou expirado.')
        return redirect('accounts:register')

    from datetime import date
    user = User.objects.create_user(
        username=pending['email'],
        email=pending['email'],
        password=pending['senha'],
    )
    cnpj = pending.get('cnpj', '').strip()
    UserProfile.objects.create(
        user=user,
        nome=pending['nome'],
        data_nascimento=date.fromisoformat(pending['data_nascimento']),
        cpf=pending['cpf'],
        cnpj=cnpj if cnpj else None,
        tem_cnpj=bool(cnpj),
        email_verificado=True,
    )
    del request.session['pending_registration']
    messages.success(request, 'Verificação concluída! Sua conta foi criada com sucesso. Clique aqui para fazer seu login')
    return render(request, 'accounts/verification_complete.html', {'type': 'register'})


def login_view(request):
    # Quem já está logado não pode trocar de tipo por aqui: precisa sair da conta primeiro
    if request.user.is_authenticated:
        messages.info(
            request,
            f'Você já está logado como {tipo_usuario(request)}. '
            f'Para entrar com outro tipo de usuário, saia da conta primeiro.'
        )
        return redirect(pagina_inicial(request))

    if request.method == 'POST':
        form = LoginForm(request.POST)
        missing = []
        for field_name in ['email', 'senha', 'tipo_usuario']:
            if not request.POST.get(field_name, '').strip():
                missing.append(field_name)
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return render(request, 'accounts/login.html', {'form': form, 'missing_fields': missing})

        if form.is_valid():
            email = form.cleaned_data['email']
            senha = form.cleaned_data['senha']
            tipo = form.cleaned_data['tipo_usuario']

            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'email_not_found')
                return render(request, 'accounts/login.html', {'form': form, 'missing_fields': []})

            user = authenticate(request, username=user_obj.username, password=senha)
            if user is None:
                messages.error(request, 'wrong_password')
                return render(request, 'accounts/login.html', {'form': form, 'missing_fields': []})

            if not hasattr(user, 'profile') or not user.profile.email_verificado:
                messages.error(request, 'Email não verificado. Verifique sua caixa de entrada.')
                return render(request, 'accounts/login.html', {'form': form, 'missing_fields': []})

            # Bloqueia quem escolheu "mediador" mas não é mediador (antes de criar a sessão)
            if tipo == 'mediador' and not user.profile.is_mediador:
                messages.error(request, 'Este usuário não é mediador. Selecione outro tipo de usuário para entrar.')
                return render(request, 'accounts/login.html', {'form': form, 'missing_fields': []})

            login(request, user)
            request.session['tipo_usuario'] = tipo

            if tipo == 'mediador':
                return redirect('disputes:mediation_panel')
            elif tipo == 'vendedor':
                return redirect('dashboard:overview')
            else:
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form, 'missing_fields': []})


def logout_view(request):
    logout(request)
    return redirect('home')


def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        missing = []
        for field_name in ['email', 'nova_senha']:
            if not request.POST.get(field_name, '').strip():
                missing.append(field_name)
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return render(request, 'accounts/password_change.html', {'form': form, 'missing_fields': missing})

        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'Email não encontrado.')
                return render(request, 'accounts/password_change.html', {'form': form, 'missing_fields': []})

            token = uuid.uuid4().hex
            request.session['pending_password_change'] = {
                'email': email,
                'nova_senha': form.cleaned_data['nova_senha'],
                'token': token,
            }
            messages.info(request, 'Aguardando confirmação. Verifique seu email para finalizar a mudança de senha')
            return render(request, 'accounts/password_change.html', {
                'form': form,
                'show_verification': True,
                'verify_url': f'/accounts/verify-password/{token}/',
                'email': email,
                'missing_fields': [],
            })
    else:
        form = PasswordChangeForm()
    return render(request, 'accounts/password_change.html', {'form': form, 'missing_fields': []})


def verify_password_view(request, token):
    pending = request.session.get('pending_password_change', {})
    if pending.get('token') != token:
        messages.error(request, 'Token de verificação inválido ou expirado.')
        return redirect('accounts:password_change')

    user = User.objects.get(email=pending['email'])
    user.set_password(pending['nova_senha'])
    user.save()
    del request.session['pending_password_change']
    messages.success(request, 'Verificação concluída! Sua senha foi alterada com sucesso. Clique aqui para fazer seu login')
    return render(request, 'accounts/verification_complete.html', {'type': 'password'})


def seller_profile_view(request, user_id):
    seller = get_object_or_404(User, pk=user_id)
    profile = seller.profile

    reviews = Review.objects.filter(vendedor=seller)

    # Filters
    filter_type = request.GET.get('filter', 'todas')
    sort_by = request.GET.get('sort', 'recentes')

    if filter_type == 'com_comentario':
        reviews = reviews.exclude(comentario_vendedor='')
    elif filter_type == '5_estrelas':
        reviews = reviews.filter(nota_vendedor=5)
    elif filter_type == '1_a_3':
        reviews = reviews.filter(nota_vendedor__lte=3)

    if sort_by == 'maior':
        reviews = reviews.order_by('-nota_vendedor')
    elif sort_by == 'menor':
        reviews = reviews.order_by('nota_vendedor')
    else:
        reviews = reviews.order_by('-criado_em')

    # Statistics
    all_reviews = Review.objects.filter(vendedor=seller)
    total = all_reviews.count()
    avg_note = all_reviews.aggregate(avg=Avg('nota_vendedor'))['avg'] or 0
    distribution = {}
    for i in range(1, 6):
        count = all_reviews.filter(nota_vendedor=i).count()
        distribution[i] = {
            'count': count,
            'percent': round((count / total) * 100) if total else 0,
        }
    positivas = all_reviews.filter(nota_vendedor__gte=4).count()
    pct_positivas = round((positivas / total) * 100) if total else 0
    com_comentario = all_reviews.exclude(comentario_vendedor='').count()

    products = seller.products.filter(ativo=True)

    return render(request, 'accounts/seller_profile.html', {
        'seller': seller,
        'stats': estatisticas_vendedor(seller),
        'profile': profile,
        'reviews': reviews,
        'products': products,
        'total': total,
        'avg_note': round(avg_note, 1),
        'distribution': distribution,
        'pct_positivas': pct_positivas,
        'com_comentario': com_comentario,
        'filter_type': filter_type,
        'sort_by': sort_by,
    })