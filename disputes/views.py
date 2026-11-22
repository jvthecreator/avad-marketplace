from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Dispute, DisputeMessage, DisputeEvidence
from .forms import DisputeForm, DisputeMessageForm, MediatorDecisionForm
from orders.models import Order, TrackingEvent
from finance.models import PaymentSplit
from accounts.roles import e_parte_do_pedido, pagina_inicial, tipo_usuario
import random


@login_required
def open_dispute_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, comprador=request.user)

    if order.status not in ['a_caminho', 'entregue']:
        messages.error(request, 'Disputas só podem ser abertas para pedidos a caminho ou já entregues.')
        return redirect('orders:tracking', order_id=order.id)

    # Check if there is already an open dispute
    existing = Dispute.objects.filter(pedido=order).first()
    if existing:
        return redirect('disputes:dispute_detail', dispute_id=existing.id)

    if request.method == 'POST':
        form = DisputeForm(request.POST, request.FILES)
        if form.is_valid():
            codigo = f"#PRO{random.randint(100, 999):03d}"
            dispute = Dispute.objects.create(
                codigo=codigo,
                pedido=order,
                comprador=request.user,
                vendedor=order.vendedor,
                motivo=form.cleaned_data['motivo'],
                descricao=form.cleaned_data['descricao'],
                status='em_analise'
            )

            # Initial message
            DisputeMessage.objects.create(
                disputa=dispute,
                autor=request.user,
                papel='comprador',
                mensagem=form.cleaned_data['descricao']
            )

            # Upload evidence
            evidencia = form.cleaned_data.get('evidencia')
            if evidencia:
                ext = evidencia.name.split('.')[-1].lower() if '.' in evidencia.name else ''
                DisputeEvidence.objects.create(
                    disputa=dispute,
                    autor=request.user,
                    arquivo=evidencia,
                    tipo=ext,
                    descricao='Evidência inicial anexada pelo comprador'
                )

            # Bloqueio imediato do repasse financeiro ao vendedor (Custódia/Escrow)
            if hasattr(order, 'split'):
                split = order.split
                split.status_repasse = 'retido'
                split.save()

            TrackingEvent.objects.create(
                pedido=order,
                titulo='Disputa aberta pelo comprador',
                descricao=f'Disputa {dispute.codigo} instaurada. Repasse ao vendedor bloqueado preventivamente.',
                local='Câmara de Mediação AVaD'
            )

            messages.success(request, f'Disputa {dispute.codigo} aberta com sucesso! Repasse financeiro bloqueado e prazo de 48h iniciado.')
            return redirect('disputes:dispute_detail', dispute_id=dispute.id)
    else:
        form = DisputeForm()

    return render(request, 'disputes/open_dispute.html', {
        'order': order,
        'form': form,
    })


@login_required
def dispute_detail_view(request, dispute_id):
    dispute = get_object_or_404(Dispute, pk=dispute_id)

    if not e_parte_do_pedido(request, dispute.comprador, dispute.vendedor):
        messages.error(request, 'Acesso não autorizado.')
        return redirect(pagina_inicial(request))

    if request.method == 'POST':
        form = DisputeMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg_text = form.cleaned_data['mensagem']
            papel = tipo_usuario(request)  # comprador, vendedor ou mediador, conforme o login

            DisputeMessage.objects.create(
                disputa=dispute,
                autor=request.user,
                papel=papel,
                mensagem=msg_text
            )

            evidencia = form.cleaned_data.get('evidencia')
            if evidencia:
                ext = evidencia.name.split('.')[-1].lower() if '.' in evidencia.name else ''
                DisputeEvidence.objects.create(
                    disputa=dispute,
                    autor=request.user,
                    arquivo=evidencia,
                    tipo=ext,
                    descricao=f'Anexo enviado por {request.user.profile.nome if hasattr(request.user, "profile") else request.user.username}'
                )

            messages.success(request, 'Mensagem enviada com sucesso!')
            return redirect('disputes:dispute_detail', dispute_id=dispute.id)
    else:
        form = DisputeMessageForm()

    messages_list = dispute.messages.all().order_by('criado_em')
    evidences = dispute.evidences.all()

    return render(request, 'disputes/dispute_detail.html', {
        'dispute': dispute,
        'order': dispute.pedido,
        'form': form,
        'messages_list': messages_list,
        'evidences': evidences,
    })


@login_required
def seller_disputes_view(request):
    disputes = Dispute.objects.filter(vendedor=request.user)
    return render(request, 'disputes/seller_disputes.html', {'disputes': disputes})


@login_required
def seller_dispute_detail_view(request, dispute_id):
    dispute = get_object_or_404(Dispute, pk=dispute_id, vendedor=request.user)
    return dispute_detail_view(request, dispute_id)


@login_required
def mediation_panel_view(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_mediador:
        messages.error(request, 'Área restrita ao Suporte de Vendas e Mediadores.')
        return redirect('home')

    disputes = Dispute.objects.all().order_by('-criado_em')
    status_filter = request.GET.get('status', '')
    if status_filter:
        disputes = disputes.filter(status=status_filter)

    return render(request, 'disputes/mediation_panel.html', {
        'disputes': disputes,
        'status_filter': status_filter,
    })


@login_required
def mediation_detail_view(request, dispute_id):
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_mediador:
        messages.error(request, 'Área restrita ao Suporte de Vendas e Mediadores.')
        return redirect('home')

    dispute = get_object_or_404(Dispute, pk=dispute_id)
    order = dispute.pedido
    split = getattr(order, 'split', None)
    tracking_events = order.tracking_events.all().order_by('-data_hora')

    message_form = DisputeMessageForm()
    decision_form = MediatorDecisionForm()

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'message':
            message_form = DisputeMessageForm(request.POST, request.FILES)
            if message_form.is_valid():
                DisputeMessage.objects.create(
                    disputa=dispute,
                    autor=request.user,
                    papel='mediador',
                    mensagem=message_form.cleaned_data['mensagem']
                )
                evidencia = message_form.cleaned_data.get('evidencia')
                if evidencia:
                    ext = evidencia.name.split('.')[-1].lower() if '.' in evidencia.name else ''
                    DisputeEvidence.objects.create(
                        disputa=dispute,
                        autor=request.user,
                        arquivo=evidencia,
                        tipo=ext,
                        descricao='Documento anexado pela Mediação'
                    )
                messages.success(request, 'Mensagem oficial da mediação enviada.')
                return redirect('disputes:mediation_detail', dispute_id=dispute.id)

        elif action_type == 'decision':
            decision_form = MediatorDecisionForm(request.POST)
            if decision_form.is_valid():
                decisao = decision_form.cleaned_data['decisao']
                fundamentacao = decision_form.cleaned_data['fundamentacao']

                dispute.fundamentacao_mediador = fundamentacao

                if decisao == 'comprador':
                    dispute.status = 'decidida_comprador'
                    order.status = 'cancelado'
                    order.save()

                    if split:
                        split.status_repasse = 'estornado'
                        split.save()

                    TrackingEvent.objects.create(
                        pedido=order,
                        titulo='Decisão favorável ao comprador',
                        descricao=f'Estorno bancário acionado pelo Mediador. Motivo: {fundamentacao}',
                        local='Câmara de Mediação AVaD'
                    )
                    messages.success(request, 'Decisão registrada a favor do Comprador. Estorno acionado com sucesso.')

                elif decisao == 'vendedor':
                    dispute.status = 'decidida_vendedor'
                    if split:
                        split.status_repasse = 'programado'
                        split.save()

                    TrackingEvent.objects.create(
                        pedido=order,
                        titulo='Decisão favorável ao vendedor',
                        descricao=f'Repasse em custódia liberado pelo Mediador. Motivo: {fundamentacao}',
                        local='Câmara de Mediação AVaD'
                    )
                    messages.success(request, 'Decisão registrada a favor do Vendedor. Repasse em custódia liberado.')

                dispute.save()
                return redirect('disputes:mediation_detail', dispute_id=dispute.id)

    return render(request, 'disputes/mediation_detail.html', {
        'dispute': dispute,
        'order': order,
        'split': split,
        'tracking_events': tracking_events,
        'message_form': message_form,
        'decision_form': decision_form,
        'messages_list': dispute.messages.all().order_by('criado_em'),
        'evidences': dispute.evidences.all(),
    })