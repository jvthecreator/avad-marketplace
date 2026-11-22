from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone


STATUS_CHOICES = [
    ('aguardando_pagamento', 'Aguardando pagamento'),
    ('aguardando_confirmacao', 'Aguardando confirmação do vendedor'),
    ('preparando', 'Item sendo preparado para entrega'),
    ('a_caminho', 'Item a caminho'),
    ('entregue', 'Item entregue'),
    ('cancelado', 'Cancelado/Estornado'),
]

METODO_FRETE_CHOICES = [
    ('pac', 'PAC'),
    ('sedex', 'SEDEX'),
    ('avad_express', 'Transportadora AVAD Express'),
]

FORMA_PAGAMENTO_CHOICES = [
    ('cartao', 'Cartão de crédito'),
    ('pix', 'PIX'),
    ('boleto', 'Boleto'),
]

REFUND_STATUS_CHOICES = [
    ('solicitacao_enviada', 'Solicitação enviada'),
    ('vendedor_notificado', 'Vendedor e banco notificados'),
    ('estorno_processamento', 'Estorno em processamento'),
    ('valor_devolvido', 'Valor devolvido'),
    ('negado', 'Negado pelo vendedor'),
]


def generate_order_code():
    num = random.randint(10000, 99999)
    return f"#AV-2026-{num:05d}"


def generate_tracking_code():
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))
    return f"BR{chars}AV"


def generate_refund_protocol():
    num = random.randint(100, 99999)
    return f"REE-2026-{num:05d}"


class Order(models.Model):
    codigo = models.CharField(max_length=20, unique=True, default=generate_order_code)
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendas')
    produto = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    valor_frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_frete = models.CharField(max_length=20, choices=METODO_FRETE_CHOICES, default='pac')
    prazo_dias = models.PositiveIntegerField(default=7)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, default='cartao')
    parcelas = models.PositiveIntegerField(default=1)
    cep_entrega = models.CharField(max_length=10, blank=True)
    endereco_entrega = models.TextField(blank=True)
    codigo_rastreio = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='aguardando_pagamento')
    recebimento_confirmado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.codigo} - {self.produto.titulo}"

    @property
    def status_display_badge(self):
        mapping = {
            'aguardando_pagamento': ('AGUARDANDO PAGAMENTO', 'warning'),
            'aguardando_confirmacao': ('AGUARDANDO CONFIRMAÇÃO', 'info'),
            'preparando': ('PREPARANDO ENVIO', 'info'),
            'a_caminho': ('ITEM A CAMINHO', 'primary'),
            'entregue': ('ITEM ENTREGUE', 'success'),
            'cancelado': ('CANCELADO/ESTORNADO', 'danger'),
        }
        return mapping.get(self.status, ('DESCONHECIDO', 'secondary'))

    @property
    def status_step(self):
        steps = ['aguardando_pagamento', 'aguardando_confirmacao', 'preparando', 'a_caminho', 'entregue']
        if self.status == 'cancelado':
            return -1
        return steps.index(self.status) if self.status in steps else 0


class TrackingEvent(models.Model):
    pedido = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_events')
    titulo = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)
    local = models.CharField(max_length=100, blank=True)
    data_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-data_hora']

    def __str__(self):
        return f"{self.titulo} - {self.pedido.codigo}"


class Review(models.Model):
    pedido = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_feitas')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_recebidas')
    nota_vendedor = models.IntegerField(default=0, choices=[(i, str(i)) for i in range(6)])
    comentario_vendedor = models.TextField(blank=True)
    nota_transporte = models.IntegerField(default=0, choices=[(i, str(i)) for i in range(6)])
    comentario_transporte = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"Review {self.pedido.codigo} - {self.nota_vendedor}★"


class RefundRequest(models.Model):
    protocolo = models.CharField(max_length=20, unique=True, default=generate_refund_protocol)
    pedido = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refund_requests')
    motivo = models.CharField(max_length=200)
    comentario = models.TextField(blank=True)
    valor_reembolso = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=REFUND_STATUS_CHOICES, default='solicitacao_enviada')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.protocolo} - {self.pedido.codigo}"


class CartItem(models.Model):
    """Item do carrinho de um usuário (fica salvo no banco, não na sessão)."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    produto = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='cart_items')
    quantidade = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['criado_em']
        unique_together = [('usuario', 'produto')]

    def __str__(self):
        return f"{self.usuario.username} - {self.produto.titulo} x{self.quantidade}"