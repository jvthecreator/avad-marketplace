from django.contrib import messages
from django.shortcuts import redirect

from .roles import COMPRADOR, VENDEDOR, MEDIADOR, PAGINA_INICIAL, tipo_usuario

# Qual tipo de usuário pode abrir cada tela. Telas que não estão aqui são públicas
# ou compartilhadas (orders:tracking, orders:refund_status e disputes:dispute_detail
# conferem o papel dentro da própria view).
ACESSO_POR_VIEW = {
    # --- comprador ---
    'orders:checkout': COMPRADOR,
    'orders:my_orders': COMPRADOR,
    'orders:review': COMPRADOR,
    'orders:confirm_receipt': COMPRADOR,
    'orders:refund': COMPRADOR,
    'orders:cart': COMPRADOR,
    'orders:cart_add': COMPRADOR,
    'orders:cart_update': COMPRADOR,
    'orders:cart_remove': COMPRADOR,
    'orders:cart_checkout': COMPRADOR,
    'disputes:open_dispute': COMPRADOR,
    # --- vendedor ---
    'orders:seller_orders': VENDEDOR,
    'orders:advance_status': VENDEDOR,
    'orders:refund_action': VENDEDOR,
    'catalog:product_create': VENDEDOR,
    'catalog:product_edit': VENDEDOR,
    'catalog:product_remove': VENDEDOR,
    'disputes:seller_disputes': VENDEDOR,
    'disputes:seller_dispute_detail': VENDEDOR,
    # --- mediador ---
    'disputes:mediation_panel': MEDIADOR,
    'disputes:mediation_detail': MEDIADOR,
}

# Apps inteiros restritos a um tipo
ACESSO_POR_APP = {
    'dashboard': VENDEDOR,
    'finance': VENDEDOR,
}


class RoleAccessMiddleware:
    """Impede que quem entrou como comprador, vendedor ou mediador use as telas dos outros tipos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tipo_usuario = tipo_usuario(request)  # usado nos templates
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        atual = request.tipo_usuario
        if atual is None:  # visitante: quem barra é o @login_required da view
            return None

        match = request.resolver_match
        exigido = ACESSO_POR_VIEW.get(match.view_name) or ACESSO_POR_APP.get(match.namespace)
        if exigido is None or exigido == atual:
            return None

        messages.error(
            request,
            f'Você entrou como {atual} e esta área é exclusiva para {exigido}. '
            f'Para acessá-la, saia da conta e entre novamente escolhendo "{exigido.capitalize()}" '
            f'como tipo de usuário.'
        )
        return redirect(PAGINA_INICIAL[atual])