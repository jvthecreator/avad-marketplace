from django.db import models
from django.contrib.auth.models import User


SPLIT_STATUS_CHOICES = [
    ('realizado', 'Repasse realizado'),
    ('programado', 'Programado'),
    ('retido', 'Retido'),
    ('estornado', 'Estornado'),
]


class PaymentSplit(models.Model):
    pedido = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='split')
    total_pago = models.DecimalField(max_digits=10, decimal_places=2)
    comissao_marketplace = models.DecimalField(max_digits=10, decimal_places=2)
    valor_frete_logistica = models.DecimalField(max_digits=10, decimal_places=2)
    valor_liquido_vendedor = models.DecimalField(max_digits=10, decimal_places=2)
    status_repasse = models.CharField(max_length=20, choices=SPLIT_STATUS_CHOICES, default='programado')
    data_lancamento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Split {self.pedido.codigo} - {self.get_status_repasse_display()}"

    @property
    def percentual_comissao(self):
        if self.total_pago > 0:
            return round((self.comissao_marketplace / self.total_pago) * 100, 1)
        return 0

    @property
    def percentual_vendedor(self):
        if self.total_pago > 0:
            return round((self.valor_liquido_vendedor / self.total_pago) * 100, 1)
        return 0

    @property
    def percentual_frete(self):
        if self.total_pago > 0:
            return round((self.valor_frete_logistica / self.total_pago) * 100, 1)
        return 0
