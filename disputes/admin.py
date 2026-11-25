from django.contrib import admin

from .models import Dispute, DisputeMessage, DisputeEvidence


class DisputeMessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'pedido', 'comprador', 'vendedor', 'motivo', 'status', 'criado_em')
    list_filter = ('status',)
    search_fields = ('codigo', 'pedido__codigo', 'comprador__email', 'vendedor__email')
    inlines = [DisputeMessageInline, DisputeEvidenceInline]
