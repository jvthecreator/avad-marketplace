from django.contrib import admin

from .models import PaymentSplit


@admin.register(PaymentSplit)
class PaymentSplitAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'total_pago', 'comissao_marketplace', 'valor_liquido_vendedor', 'status_repasse',
                    'data_lancamento')
    list_filter = ('status_repasse',)
    search_fields = ('pedido__codigo',)
