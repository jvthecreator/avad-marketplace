from django.db import models
from django.contrib.auth.models import User


CATEGORIAS = [
    ('tecnologia', 'Tecnologia'),
    ('eletronicos', 'Eletrônicos'),
    ('audio', 'Áudio'),
    ('eletrodomesticos', 'Eletrodomésticos'),
    ('brinquedos', 'Brinquedos'),
    ('servicos', 'Serviços'),
    ('decoracao', 'Decoração'),
    ('moda', 'Moda'),
    ('esportes', 'Esportes'),
    ('livros', 'Livros'),
    ('outros', 'Outros'),
]


class Product(models.Model):
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    titulo = models.CharField(max_length=200)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    descricao = models.TextField()
    caracteristicas = models.TextField(blank=True, help_text='Uma característica por linha')
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.PositiveIntegerField(default=0)
    imagem = models.ImageField(upload_to='products/', blank=True, null=True)
    frete_gratis = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    removido = models.BooleanField(default=False)  # anúncio removido pelo vendedor (some da loja e da lista)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo

    @property
    def nota_media(self):
        from orders.models import Review
        from django.db.models import Avg
        reviews = Review.objects.filter(pedido__produto=self)
        avg = reviews.aggregate(avg=Avg('nota_vendedor'))['avg']
        return round(avg, 1) if avg else 0

    @property
    def total_avaliacoes(self):
        from orders.models import Review
        return Review.objects.filter(pedido__produto=self).count()

    @property
    def parcelas_sem_juros(self):
        if self.preco >= 12:
            valor = f"{self.preco / 12:.2f}".replace('.', ',')
            return f"em até 12x de R$ {valor} sem juros"
        return ""