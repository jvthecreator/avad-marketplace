from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import UserProfile
from catalog.models import Product
from orders.models import Order, TrackingEvent, Review, RefundRequest
from finance.models import PaymentSplit
from disputes.models import Dispute, DisputeMessage
from decimal import Decimal
import datetime


class AVaDMarketplaceUseCaseTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create buyer
        self.buyer = User.objects.create_user(username='marina@avad.com', email='marina@avad.com', password='senha1234')
        self.buyer_profile = UserProfile.objects.create(
            user=self.buyer,
            nome='Marina',
            data_nascimento=datetime.date(1995, 5, 14),
            cpf='123.456.789-01',
            email_verificado=True,
            tipo_usuario='comprador'
        )

        # Create seller
        self.seller = User.objects.create_user(username='felipe@lojadech.com', email='felipe@lojadech.com', password='senha1234')
        self.seller_profile = UserProfile.objects.create(
            user=self.seller,
            nome='Felipe',
            nome_loja='Tech Store',
            data_nascimento=datetime.date(1990, 10, 20),
            cpf='987.654.321-00',
            cnpj='12.345.678/0001-90',
            tem_cnpj=True,
            email_verificado=True,
            tipo_usuario='vendedor'
        )

        # Create mediator
        self.mediator = User.objects.create_user(username='mediador@avad.com', email='mediador@avad.com', password='senha1234')
        self.mediator_profile = UserProfile.objects.create(
            user=self.mediator,
            nome='Ana Mediadora',
            data_nascimento=datetime.date(1985, 7, 8),
            cpf='111.222.333-44',
            email_verificado=True,
            is_mediador=True,
            tipo_usuario='mediador'
        )

        # Create product
        self.product = Product.objects.create(
            vendedor=self.seller,
            titulo='Smartphone Pro 5G',
            categoria='tecnologia',
            descricao='Excelente aparelho moderno.',
            preco=Decimal('2000.00'),
            estoque=10,
            frete_gratis=True,
            ativo=True
        )

    def entrar_como(self, username, tipo):
        """Faz login e define o tipo de usuário escolhido (como a tela de login faz)."""
        self.client.login(username=username, password='senha1234')
        sessao = self.client.session
        sessao['tipo_usuario'] = tipo
        sessao.save()

    def test_pro001_register_validation_and_flow(self):
        # Empty fields
        res = self.client.post('/accounts/register/', {})
        self.assertContains(res, 'Preencha todos os campos obrigatórios')

        # Successful registration initiation
        res = self.client.post('/accounts/register/', {
            'nome': 'Carlos',
            'data_nascimento': '12/10/1992',
            'email': 'carlos@teste.com',
            'senha': 'senha12345',
            'cpf': '333.444.555-66',
        })
        self.assertContains(res, 'Aguardando confirmação. Verifique seu email para finalizar o cadastro')

        # Verification token link
        token = self.client.session.get('pending_registration', {}).get('token')
        self.assertIsNotNone(token)

        res = self.client.get(f'/accounts/verify/{token}/')
        self.assertContains(res, 'Verificação concluída! Sua conta foi criada com sucesso. Clique aqui para fazer seu login')

    def test_pro002_login_flows(self):
        # Missing fields
        res = self.client.post('/accounts/login/', {})
        self.assertContains(res, 'Preencha todos os campos obrigatórios')

        # Email not registered
        res = self.client.post('/accounts/login/', {
            'email': 'inexistente@avad.com',
            'senha': 'qualquersenha',
            'tipo_usuario': 'comprador'
        })
        self.assertContains(res, 'Seu email não está registrado, para registrar')

        # Wrong password
        res = self.client.post('/accounts/login/', {
            'email': 'marina@avad.com',
            'senha': 'senhaerrada',
            'tipo_usuario': 'comprador'
        })
        self.assertContains(res, 'Senha incorreta. Caso deseje trocar sua senha')

        # Valid login
        res = self.client.post('/accounts/login/', {
            'email': 'marina@avad.com',
            'senha': 'senha1234',
            'tipo_usuario': 'comprador'
        })
        self.assertEqual(res.status_code, 302)

    def test_pro003_password_change(self):
        res = self.client.post('/accounts/password-change/', {
            'email': 'marina@avad.com',
            'nova_senha': 'novasenha1234'
        })
        self.assertContains(res, 'Aguardando confirmação. Verifique seu email para finalizar a mudança de senha')

        token = self.client.session.get('pending_password_change', {}).get('token')
        res = self.client.get(f'/accounts/verify-password/{token}/')
        self.assertContains(res, 'Verificação concluída! Sua senha foi alterada com sucesso. Clique aqui para fazer seu login')

    def test_pro004_create_product(self):
        self.entrar_como('felipe@lojadech.com', 'vendedor')
        res = self.client.post('/catalog/product/new/', {
            'titulo': 'Tablet Pro 11',
            'categoria': 'tecnologia',
            'preco': '1500.00',
            'estoque': '5',
            'descricao': 'Tablet profissional com caneta ativa.',
            'aceito_termos': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Product.objects.filter(titulo='Tablet Pro 11').exists())

    def test_pro005_and_pro006_checkout_split_escrow(self):
        self.entrar_como('marina@avad.com', 'comprador')

        # Checkout test with rejected simulation
        res = self.client.post(f'/orders/checkout/{self.product.id}/', {
            'quantidade': 1,
            'cep': '01310-100',
            'rua': 'Av Paulista, 100',
            'bairro': 'Bela Vista',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'metodo_frete': 'pac',
            'forma_pagamento': 'cartao',
            'simulacao_gateway': 'negar',
        })
        self.assertContains(res, 'Transação negada')

        # Checkout test with timeout simulation
        res = self.client.post(f'/orders/checkout/{self.product.id}/', {
            'quantidade': 1,
            'cep': '01310-100',
            'rua': 'Av Paulista, 100',
            'bairro': 'Bela Vista',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'metodo_frete': 'pac',
            'forma_pagamento': 'cartao',
            'simulacao_gateway': 'timeout',
        })
        self.assertContains(res, 'Tempo limite de resposta excedido')

        # Checkout test with approval
        res = self.client.post(f'/orders/checkout/{self.product.id}/', {
            'quantidade': 1,
            'cep': '01310-100',
            'rua': 'Av Paulista, 100',
            'bairro': 'Bela Vista',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'metodo_frete': 'pac',
            'forma_pagamento': 'cartao',
            'simulacao_gateway': 'aprovar',
        })
        self.assertEqual(res.status_code, 302)

        order = Order.objects.filter(comprador=self.buyer).first()
        self.assertIsNotNone(order)
        self.assertTrue(order.codigo.startswith('#AV-2026-'))

        # Check PRO006 Split
        self.assertTrue(hasattr(order, 'split'))
        split = order.split
        self.assertEqual(split.comissao_marketplace, round(self.product.preco * Decimal('0.065'), 2))

    def test_pro007_mediation_panel_and_decision(self):
        # Create an in-transit order
        order = Order.objects.create(
            comprador=self.buyer,
            vendedor=self.seller,
            produto=self.product,
            quantidade=1,
            preco_unitario=self.product.preco,
            valor_frete=Decimal('20.00'),
            valor_total=Decimal('2020.00'),
            status='a_caminho'
        )
        PaymentSplit.objects.create(
            pedido=order,
            total_pago=order.valor_total,
            comissao_marketplace=Decimal('130.00'),
            valor_frete_logistica=Decimal('20.00'),
            valor_liquido_vendedor=Decimal('1870.00'),
            status_repasse='programado'
        )

        # Buyer opens dispute
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.post(f'/disputes/open/{order.id}/', {
            'motivo': 'Produto não entregue',
            'descricao': 'O prazo estourou e não recebi nada.',
        })
        self.assertEqual(res.status_code, 302)

        dispute = Dispute.objects.filter(pedido=order).first()
        self.assertIsNotNone(dispute)
        self.assertEqual(dispute.status, 'em_analise')

        # Verify Escrow freeze
        order.split.refresh_from_db()
        self.assertEqual(order.split.status_repasse, 'retido')

        # Mediator accesses 3-column panel and decides for buyer
        self.entrar_como('mediador@avad.com', 'mediador')
        res = self.client.get(f'/disputes/mediation/{dispute.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Partes envolvidas')
        self.assertContains(res, 'Histórico consolidado')
        self.assertContains(res, 'Decisão do Mediador')

        # Mediator issues decision
        res = self.client.post(f'/disputes/mediation/{dispute.id}/', {
            'action_type': 'decision',
            'fundamentacao': 'Comprovado atraso excessivo sem envio.',
            'decisao': 'comprador',
        })
        self.assertEqual(res.status_code, 302)

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, 'decidida_comprador')
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelado')
        order.split.refresh_from_db()
        self.assertEqual(order.split.status_repasse, 'estornado')

    def test_pro008_tracking_and_status_advance(self):
        order = Order.objects.create(
            comprador=self.buyer,
            vendedor=self.seller,
            produto=self.product,
            quantidade=1,
            preco_unitario=self.product.preco,
            valor_frete=Decimal('0.00'),
            valor_total=self.product.preco,
            status='aguardando_confirmacao'
        )
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.get(f'/orders/tracking/{order.id}/')
        self.assertContains(res, 'Confirmação vendedor')

        # Seller advances status
        self.entrar_como('felipe@lojadech.com', 'vendedor')
        res = self.client.get(f'/orders/advance-status/{order.id}/')
        order.refresh_from_db()
        self.assertEqual(order.status, 'preparando')

    def test_pro009_review(self):
        order = Order.objects.create(
            comprador=self.buyer,
            vendedor=self.seller,
            produto=self.product,
            quantidade=1,
            preco_unitario=self.product.preco,
            valor_frete=Decimal('0.00'),
            valor_total=self.product.preco,
            status='entregue',
            recebimento_confirmado=True
        )
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.post(f'/orders/review/{order.id}/', {
            'nota_vendedor': 5,
            'comentario_vendedor': 'Ótimo atendimento!',
            'nota_transporte': 4,
            'comentario_transporte': 'Chegou bem.',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Review.objects.filter(pedido=order).exists())

    def test_pro010_refund(self):
        order = Order.objects.create(
            comprador=self.buyer,
            vendedor=self.seller,
            produto=self.product,
            quantidade=1,
            preco_unitario=self.product.preco,
            valor_frete=Decimal('10.00'),
            valor_total=Decimal('2010.00'),
            status='entregue',
        )
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.post(f'/orders/refund/{order.id}/', {
            'motivo': 'insatisfeito',
            'comentario': 'Não atendeu às minhas expectativas.',
        })
        self.assertEqual(res.status_code, 302)
        ref = RefundRequest.objects.filter(pedido=order).first()
        self.assertIsNotNone(ref)
        self.assertTrue(ref.protocolo.startswith('REE-2026-'))

    def test_pro011_seller_profile(self):
        res = self.client.get(f'/accounts/seller-profile/{self.seller.id}/')
        self.assertContains(res, 'Estatísticas do vendedor')
        self.assertContains(res, 'Avaliações e comentários')

    def test_pro012_seller_dashboard(self):
        self.entrar_como('felipe@lojadech.com', 'vendedor')
        res = self.client.get('/dashboard/')
        self.assertContains(res, 'Vendas no ano')
        self.assertContains(res, 'Evolução das vendas')
        self.assertContains(res, 'Mais vendidos')
        self.assertContains(res, 'Insights rápidos')

    def test_pro013_tipos_de_usuario_independentes(self):
        # Vendedor não acessa telas de comprador nem de mediador
        self.entrar_como('felipe@lojadech.com', 'vendedor')
        for url in ['/orders/my-orders/', '/orders/cart/', '/disputes/mediation/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, url)
            self.assertTrue(res.url.startswith('/dashboard/'), url)
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)

        # Comprador não acessa o painel do vendedor, o financeiro nem a criação de anúncios
        self.entrar_como('marina@avad.com', 'comprador')
        for url in ['/dashboard/', '/finance/', '/catalog/product/new/', '/orders/seller-orders/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, url)
            self.assertEqual(res.url, '/', url)
        self.assertEqual(self.client.get('/orders/my-orders/').status_code, 200)

        # Mediador não acessa telas de comprador nem de vendedor
        self.entrar_como('mediador@avad.com', 'mediador')
        for url in ['/orders/my-orders/', '/orders/cart/', '/dashboard/', '/finance/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, url)
            self.assertTrue(res.url.startswith('/disputes/mediation/'), url)
        self.assertEqual(self.client.get('/disputes/mediation/').status_code, 200)

    def test_pro014_nao_troca_de_tipo_sem_sair(self):
        self.entrar_como('marina@avad.com', 'comprador')
        res = self.client.post('/accounts/login/', {
            'email': 'marina@avad.com',
            'senha': 'senha1234',
            'tipo_usuario': 'vendedor',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.client.session['tipo_usuario'], 'comprador')
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)

        # Saindo da conta, pode entrar com outro tipo
        self.client.get('/accounts/logout/')
        res = self.client.post('/accounts/login/', {
            'email': 'marina@avad.com',
            'senha': 'senha1234',
            'tipo_usuario': 'vendedor',
        })
        self.assertEqual(self.client.session['tipo_usuario'], 'vendedor')
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)