from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'vendedor', 'categoria', 'preco', 'estoque', 'ativo', 'removido', 'criado_em')
    list_filter = ('categoria', 'ativo', 'removido', 'frete_gratis')
    search_fields = ('titulo', 'vendedor__email', 'vendedor__profile__nome_loja')
