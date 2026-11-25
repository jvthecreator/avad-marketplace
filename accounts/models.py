from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nome = models.CharField(max_length=16)
    data_nascimento = models.DateField()
    cpf = models.CharField(max_length=14, unique=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True, unique=True)
    tem_cnpj = models.BooleanField(default=False)
    email_verificado = models.BooleanField(default=False)
    is_mediador = models.BooleanField(default=False)
    conta_bancaria_bloqueada = models.BooleanField(default=False)
    suspenso = models.BooleanField(default=False)
    token_verificacao = models.CharField(max_length=64, blank=True, null=True)
    tipo_usuario = models.CharField(max_length=20, choices=[
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
        ('mediador', 'Mediador'),
    ], default='comprador')
    nome_loja = models.CharField(max_length=64, blank=True, null=True)
    # Meta de faturamento bruto mensal do vendedor (exibida no painel). Editável em Configurações.
    meta_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('25000.00'),
                                      validators=[MinValueValidator(Decimal('1.00'))])

    def __str__(self):
        return f"{self.nome} ({self.user.email})"

    @property
    def avaliacao_percentual(self):
        from orders.models import Review
        reviews = Review.objects.filter(vendedor=self.user)
        if not reviews.exists():
            return 0
        positivas = reviews.filter(nota_vendedor__gte=4).count()
        return round((positivas / reviews.count()) * 100)

    @property
    def nota_media(self):
        from orders.models import Review
        from django.db.models import Avg
        avg = Review.objects.filter(vendedor=self.user).aggregate(avg=Avg('nota_vendedor'))['avg']
        return round(avg, 1) if avg else 0

    @property
    def total_avaliacoes(self):
        from orders.models import Review
        return Review.objects.filter(vendedor=self.user).count()


class SavedCard(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_cards')
    ultimos_digitos = models.CharField(max_length=4)
    bandeira = models.CharField(max_length=20)
    nome_impresso = models.CharField(max_length=64)
    validade = models.CharField(max_length=5)
    cpf_titular = models.CharField(max_length=14)

    def __str__(self):
        return f"{self.bandeira} •••• {self.ultimos_digitos}"
