from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('', views.indice_view, name='indice'),
    # Catálogo (busca ao vivo)
    path('produtos/', views.produtos_view, name='produtos'),
    # Painel do vendedor
    path('vendedor/estatisticas/', views.estatisticas_view, name='estatisticas'),
    # Notificações (sininho)
    path('notificacoes/', views.notificacoes_view, name='notificacoes'),
    path('notificacoes/marcar-todas/', views.notificacoes_marcar_todas_view, name='notificacoes_marcar_todas'),
    path('notificacoes/<int:pk>/lida/', views.notificacao_lida_view, name='notificacao_lida'),
    # Carrinho
    path('carrinho/', views.carrinho_view, name='carrinho'),
    path('carrinho/<int:produto_id>/', views.carrinho_item_view, name='carrinho_item'),
    # Chat da disputa
    path('disputas/<int:disputa_id>/mensagens/', views.disputa_mensagens_view, name='disputa_mensagens'),
    # Rastreio do pedido
    path('pedidos/<int:pedido_id>/rastreio/', views.rastreio_view, name='rastreio'),
]
