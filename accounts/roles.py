"""Tipos de usuário (papéis) do AVaD.

O tipo é escolhido no login e fica guardado na sessão (request.session['tipo_usuario']).
Ele só muda saindo da conta e entrando de novo.
"""

COMPRADOR = 'comprador'
VENDEDOR = 'vendedor'
MEDIADOR = 'mediador'
TIPOS = (COMPRADOR, VENDEDOR, MEDIADOR)

# Para onde cada tipo vai quando entra ou tenta acessar uma área que não é dele
PAGINA_INICIAL = {
    COMPRADOR: 'home',
    VENDEDOR: 'dashboard:overview',
    MEDIADOR: 'disputes:mediation_panel',
}


def tipo_usuario(request):
    """Tipo com que o usuário entrou (None se não estiver logado)."""
    if not request.user.is_authenticated:
        return None
    tipo = request.session.get('tipo_usuario')
    return tipo if tipo in TIPOS else COMPRADOR


def pagina_inicial(request):
    return PAGINA_INICIAL.get(tipo_usuario(request), 'home')


def e_parte_do_pedido(request, comprador, vendedor):
    """Vale para telas compartilhadas (rastreio, disputa): o usuário só enxerga o que
    pertence ao papel com que entrou."""
    tipo = tipo_usuario(request)
    if tipo == COMPRADOR:
        return request.user == comprador
    if tipo == VENDEDOR:
        return request.user == vendedor
    if tipo == MEDIADOR:
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.is_mediador)
    return False