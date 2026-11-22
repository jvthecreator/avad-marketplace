from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.timesince import timesince


class Notification(models.Model):
    """Notificação para um usuário, num tipo específico (comprador, vendedor ou mediador).

    Como o tipo de usuário é escolhido no login, cada tipo enxerga só as suas notificações.
    """
    TIPOS = [
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
        ('mediador', 'Mediador'),
    ]
    CATEGORIAS = [
        ('pedido', 'Pedido'),
        ('disputa', 'Disputa'),
        ('reembolso', 'Reembolso'),
        ('avaliacao', 'Avaliação'),
    ]
    ICONES = {
        'pedido': '📦',
        'disputa': '⚖️',
        'reembolso': '💸',
        'avaliacao': '⭐',
    }

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    tipo_usuario = models.CharField(max_length=20, choices=TIPOS)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='pedido')
    titulo = models.CharField(max_length=120)
    mensagem = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.usuario.username} ({self.tipo_usuario}): {self.titulo}"

    @property
    def icone(self):
        return self.ICONES.get(self.categoria, '🔔')

    @property
    def quando(self):
        if (timezone.now() - self.criada_em).total_seconds() < 60:
            return 'agora mesmo'
        return f'há {timesince(self.criada_em)}'
