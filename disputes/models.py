from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


DISPUTE_STATUS_CHOICES = [
    ('em_analise', 'EM ANÁLISE'),
    ('decidida_comprador', 'DECIDIDA COMPRADOR'),
    ('decidida_vendedor', 'DECIDIDA VENDEDOR'),
]


class Dispute(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    pedido = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='disputes')
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputas_abertas')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputas_recebidas')
    motivo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='em_analise')
    fundamentacao_mediador = models.TextField(blank=True)
    sla_limite = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.codigo} - {self.pedido.codigo}"

    def save(self, *args, **kwargs):
        if not self.sla_limite:
            self.sla_limite = timezone.now() + datetime.timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def sla_restante(self):
        if self.sla_limite:
            delta = self.sla_limite - timezone.now()
            if delta.total_seconds() > 0:
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}min"
        return "Expirado"


class DisputeMessage(models.Model):
    disputa = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    papel = models.CharField(max_length=20, choices=[
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
        ('mediador', 'Mediador'),
    ])
    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

    def __str__(self):
        return f"{self.papel}: {self.mensagem[:50]}"


class DisputeEvidence(models.Model):
    disputa = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidences')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    arquivo = models.FileField(upload_to='evidences/')
    tipo = models.CharField(max_length=10, blank=True)
    nome = models.CharField(max_length=100, blank=True)  # nome dado por quem anexou (ex.: "Foto da caixa amassada")
    descricao = models.CharField(max_length=200, blank=True)  # contexto automático (ex.: "Anexo enviado por Fe")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

    def __str__(self):
        return f"{self.titulo} - {self.disputa.codigo}"

    @property
    def titulo(self):
        """Nome escolhido por quem anexou; evidências antigas (sem nome) usam a descrição automática."""
        return self.nome or self.descricao or 'Arquivo de evidência'
