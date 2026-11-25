from django.contrib import admin

from .models import Order, TrackingEvent, Review, RefundRequest, CartItem


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'produto', 'comprador', 'vendedor', 'quantidade', 'valor_total', 'status',
                    'recebimento_confirmado', 'criado_em')
    list_filter = ('status', 'recebimento_confirmado', 'forma_pagamento', 'metodo_frete')
    search_fields = ('codigo', 'codigo_rastreio', 'comprador__email', 'vendedor__email', 'produto__titulo')
    date_hierarchy = 'criado_em'
    inlines = [TrackingEventInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'vendedor', 'comprador', 'nota_vendedor', 'nota_transporte', 'criado_em')
    list_filter = ('nota_vendedor',)


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('protocolo', 'pedido', 'valor_reembolso', 'status', 'criado_em')
    list_filter = ('status',)
    search_fields = ('protocolo', 'pedido__codigo')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'produto', 'quantidade', 'atualizado_em')
