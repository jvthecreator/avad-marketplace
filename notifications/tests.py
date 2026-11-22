from decimal import Decimal
import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from catalog.models import Product
from orders.models import Order
from .models import Notification


class NotificationTests(TestCase):
    def setUp(self):
        def criar(email, nome, cpf, **extra):
            user = User.objects.create_user(username=email, email=email, password='senha1234')
            UserProfile.objects.create(
                user=user, nome=nome, data_nascimento=datetime.date(1990, 1, 1),
                cpf=cpf, email_verificado=True, **extra
            )
            return user

        self.buyer = criar('marina@avad.com', 'Marina', '123.456.789-01')
        self.seller = criar('felipe@lojadech.com', 'Felipe', '987.654.321-00')
        self.mediator = criar('mediador@avad.com', 'Ana', '111.222.333-44', is_mediador=True)
        self.product = Product.objects.create(
            vendedor=self.seller, titulo='Smartphone Pro 5G', categoria='tecnologia',
            descricao='Excelente aparelho.', preco=Decimal('2000.00'), estoque=10,
            frete_gratis=True, ativo=True,
        )

    def entrar_como(self, username, tipo):
        self.client.login(username=username, password='senha1234')
        sessao = self.client.session
        sessao['tipo_usuario'] = tipo
        sessao.save()

    def criar_pedido(self, status):
        return Order.objects.create(
            comprador=self.buyer, vendedor=self.seller, produto=self.product, quantidade=1,
            preco_unitario=self.product.preco, valor_frete=Decimal('20.00'),
            valor_total=Decimal('2020.00'), status=status,
        )

    def test_novo_pedido_notifica_o_vendedor(self):
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.post(f'/orders/checkout/{self.product.id}/', {
            'quantidade': 1, 'cep': '01310-100', 'rua': 'Av Paulista, 100', 'bairro': 'Bela Vista',
            'cidade': 'São Paulo', 'estado': 'SP', 'metodo_frete': 'pac',
            'forma_pagamento': 'cartao', 'simulacao_gateway': 'aprovar',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(
            Notification.objects.filter(usuario=self.seller, tipo_usuario='vendedor', titulo='Novo pedido recebido').count(), 1
        )
        self.assertEqual(Notification.objects.filter(usuario=self.buyer).count(), 0)

    def test_mudanca_de_status_notifica_o_comprador(self):
        order = self.criar_pedido('preparando')
        self.entrar_como('felipe@lojadech.com', 'vendedor')
        self.client.get(f'/orders/advance-status/{order.id}/?status=a_caminho')
        notificacao = Notification.objects.get(usuario=self.buyer, tipo_usuario='comprador')
        self.assertEqual(notificacao.titulo, 'Seu pedido saiu para entrega')
        self.assertFalse(notificacao.lida)

    def test_disputa_notifica_vendedor_mediador_e_decisao_notifica_as_partes(self):
        order = self.criar_pedido('a_caminho')
        self.entrar_como('marina@avad.com', 'comprador')
        self.client.post(f'/disputes/open/{order.id}/', {
            'motivo': 'Produto não entregue', 'descricao': 'O prazo estourou.',
        })
        self.assertTrue(Notification.objects.filter(usuario=self.seller, tipo_usuario='vendedor', categoria='disputa').exists())
        self.assertTrue(Notification.objects.filter(usuario=self.mediator, tipo_usuario='mediador', categoria='disputa').exists())

        from disputes.models import Dispute
        dispute = Dispute.objects.get(pedido=order)
        self.entrar_como('mediador@avad.com', 'mediador')
        self.client.post(f'/disputes/mediation/{dispute.id}/', {
            'action_type': 'decision', 'fundamentacao': 'Atraso comprovado.', 'decisao': 'comprador',
        })
        for usuario, tipo in [(self.buyer, 'comprador'), (self.seller, 'vendedor')]:
            self.assertTrue(
                Notification.objects.filter(usuario=usuario, tipo_usuario=tipo, titulo='Disputa decidida pela mediação').exists()
            )

    def test_contador_por_tipo_leitura_e_marcar_todas(self):
        do_comprador = Notification.objects.create(usuario=self.seller, tipo_usuario='comprador', titulo='A', mensagem='a')
        do_vendedor = Notification.objects.create(usuario=self.seller, tipo_usuario='vendedor', titulo='B', mensagem='b')

        self.entrar_como('felipe@lojadech.com', 'vendedor')
        res = self.client.get('/notifications/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['notif_count'], 1)
        self.assertEqual([n.id for n in res.context['notificacoes']], [do_vendedor.id])

        # abrir marca como lida; a de outro tipo de usuário não é acessível
        self.assertEqual(self.client.get(f'/notifications/{do_vendedor.id}/open/').status_code, 302)
        do_vendedor.refresh_from_db()
        self.assertTrue(do_vendedor.lida)
        self.assertEqual(self.client.get(f'/notifications/{do_comprador.id}/open/').status_code, 404)

        Notification.objects.create(usuario=self.seller, tipo_usuario='vendedor', titulo='C', mensagem='c')
        self.client.post('/notifications/mark-all-read/')
        self.assertEqual(self.client.get('/notifications/').context['notif_count'], 0)
        do_comprador.refresh_from_db()
        self.assertFalse(do_comprador.lida)  # a de comprador continua não lida
