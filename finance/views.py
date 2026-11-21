from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from .models import PaymentSplit
import csv


@login_required
def finance_view(request):
    splits = PaymentSplit.objects.filter(pedido__vendedor=request.user).order_by('-data_lancamento')

    # Sum totals
    realizados = splits.filter(status_repasse='realizado').aggregate(sum=Sum('valor_liquido_vendedor'))['sum'] or 0
    programados = splits.filter(status_repasse='programado').aggregate(sum=Sum('valor_liquido_vendedor'))['sum'] or 0
    retidos = splits.filter(status_repasse='retido').aggregate(sum=Sum('valor_liquido_vendedor'))['sum'] or 0

    profile = getattr(request.user, 'profile', None)
    conta_bloqueada = profile.conta_bancaria_bloqueada if profile else False

    # Selected split for lateral detail panel
    selected_id = request.GET.get('split_id')
    selected_split = None
    if selected_id:
        selected_split = splits.filter(id=selected_id).first()
    if not selected_split and splits.exists():
        selected_split = splits.first()

    return render(request, 'finance/finance.html', {
        'splits': splits,
        'realizados': realizados,
        'programados': programados,
        'retidos': retidos,
        'conta_bloqueada': conta_bloqueada,
        'selected_split': selected_split,
    })


@login_required
def regularize_view(request):
    profile = getattr(request.user, 'profile', None)
    if profile:
        profile.conta_bancaria_bloqueada = False
        profile.save()

        # Update retained splits to programado
        PaymentSplit.objects.filter(pedido__vendedor=request.user, status_repasse='retido').update(status_repasse='programado')

        messages.success(request, 'Conta bancária regularizada com sucesso! Os valores retidos em conta transitória (escrow) foram liberados e programados.')
    return redirect('finance:finance')


@login_required
def export_csv_view(request):
    splits = PaymentSplit.objects.filter(pedido__vendedor=request.user).order_by('-data_lancamento')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="extrato_financeiro_avad.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['PEDIDO', 'DATA', 'TOTAL PAGO (R$)', 'COMISSAO AVAD (R$)', 'FRETE (R$)', 'LIQUIDO VENDEDOR (R$)', 'STATUS'])

    for s in splits:
        writer.writerow([
            s.pedido.codigo,
            s.data_lancamento.strftime('%d/%m/%Y %H:%M'),
            f"{s.total_pago:.2f}".replace('.', ','),
            f"{s.comissao_marketplace:.2f}".replace('.', ','),
            f"{s.valor_frete_logistica:.2f}".replace('.', ','),
            f"{s.valor_liquido_vendedor:.2f}".replace('.', ','),
            s.get_status_repasse_display()
        ])

    return response
