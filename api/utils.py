"""Ferramentas comuns da API REST do AVaD (respostas JSON, autenticação e leitura do corpo)."""
import json
from decimal import Decimal
from functools import wraps

from django.http import JsonResponse

from accounts.roles import tipo_usuario


def resposta(dados, status=200):
    return JsonResponse(dados, status=status, json_dumps_params={'ensure_ascii': False})


def erro(mensagem, status=400, **extra):
    return resposta({'erro': mensagem, **extra}, status=status)


def dinheiro(valor):
    """Decimal -> float com 2 casas (o JSON não tem tipo decimal)."""
    if valor is None:
        return None
    return float(Decimal(valor).quantize(Decimal('0.01')))


def corpo_json(request):
    """Lê o corpo da requisição como JSON (aceita também formulário comum)."""
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body or b'{}')
        except ValueError:
            return None
    return request.POST


def api_login_required(papel=None):
    """Como @login_required, mas responde 401/403 em JSON em vez de redirecionar.
    papel: exige que o usuário tenha entrado com esse tipo (comprador, vendedor ou mediador)."""
    def decorador(view):
        @wraps(view)
        def envolvida(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return erro('Faça login para usar esta API.', status=401)
            if papel and tipo_usuario(request) != papel:
                return erro(f'Disponível apenas para quem entrou como {papel}.', status=403)
            return view(request, *args, **kwargs)
        return envolvida
    return decorador


def metodos(*permitidos):
    """Responde 405 em JSON para métodos HTTP não aceitos."""
    def decorador(view):
        @wraps(view)
        def envolvida(request, *args, **kwargs):
            if request.method not in permitidos:
                resp = erro(f'Método {request.method} não permitido.', status=405)
                resp['Allow'] = ', '.join(permitidos)
                return resp
            return view(request, *args, **kwargs)
        return envolvida
    return decorador
