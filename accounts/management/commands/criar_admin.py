"""Cria (ou atualiza) a conta de administrador do Django a partir de variáveis de ambiente.

Uso local:
    python manage.py criar_admin --email admin@avad.com --senha "uma-senha-forte"

No Render (roda a cada deploy, pelo buildCommand do render.yaml), defina no painel:
    DJANGO_ADMIN_EMAIL     e-mail de login do admin
    DJANGO_ADMIN_PASSWORD  senha do admin

O comando pode rodar quantas vezes for preciso: se a conta já existe, só garante que ela é
superusuária e atualiza a senha. Sem as variáveis, ele só avisa e não interrompe o deploy.
A conta também ganha um perfil verificado com acesso de mediador, para conseguir entrar
pelo login do site, além de /admin/.
"""
import datetime
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Cria/atualiza o superusuário do Django (para acessar /admin/).'

    def add_arguments(self, parser):
        parser.add_argument('--email', default=os.environ.get('DJANGO_ADMIN_EMAIL'))
        parser.add_argument('--senha', default=os.environ.get('DJANGO_ADMIN_PASSWORD'))

    def handle(self, *args, **opts):
        email, senha = (opts['email'] or '').strip().lower(), opts['senha'] or ''
        if not email or not senha:
            self.stdout.write(self.style.WARNING(
                'Admin não criado: defina DJANGO_ADMIN_EMAIL e DJANGO_ADMIN_PASSWORD (ou use --email e --senha).'))
            return
        if len(senha) < 8:
            raise CommandError('A senha do admin precisa ter pelo menos 8 caracteres.')

        user, criado = User.objects.get_or_create(username=email, defaults={'email': email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(senha)
        user.save()

        perfil, _ = UserProfile.objects.get_or_create(user=user, defaults={
            'nome': 'Admin',
            'data_nascimento': datetime.date(1990, 1, 1),
            'cpf': f'ADMIN-{user.pk}',  # CPF é obrigatório e único no perfil; este é só um marcador
        })
        perfil.email_verificado = True
        perfil.is_mediador = True
        perfil.save()

        acao = 'criado' if criado else 'atualizado'
        self.stdout.write(self.style.SUCCESS(f'Admin {acao}: {email} (acesse /admin/)'))
