import datetime
import json
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import UserProfile
from catalog.models import Product
from disputes.models import Dispute, DisputeEvidence
from finance.models import PaymentSplit
from notifications.models import Notification
from orders.models import CartItem, Order, TrackingEvent

MEDIA_TESTE = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class ApiRestTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)

    def setUp(self):
        def usuario(email, nome, cpf, **extra):
            u = User.objects.create_user(username=email, email=email, password='senha1234')
            UserProfile.objects.create(user=u, nome=nome, data_nascimento=datetime.date(1990, 1, 1), cpf=cpf,
                                       email_verificado=True, **extra)
            return u
        self.comprador = usuario('c@avad.com', 'Ze', '1')
        self.vendedor = usuario('v@avad.com', 'Fe', '2', nome_loja='Loja da Fe')
        self.outro = usuario('o@avad.com', 'Outro', '3')
        self.mediador = usuario('m@avad.com', 'Ana', '4', is_mediador=True)
        self.caneca = Product.objects.create(vendedor=self.vendedor, titulo='Caneca azul', categoria='decoracao',
                                             descricao='x', preco=Decimal('30.00'), estoque=3)
        self.fone = Product.objects.create(vendedor=self.vendedor, titulo='Fone sem fio', categoria='audio',
                                           descricao='x', preco=Decimal('200.00'), estoque=10, frete_gratis=True)
        self.pedido = Order.objects.create(comprador=self.comprador, vendedor=self.vendedor, produto=self.fone,
                                           preco_unitario=Decimal('200.00'), valor_total=Decimal('200.00'), status='a_caminho')
        PaymentSplit.objects.create(pedido=self.pedido, total_pago=Decimal('200'), comissao_marketplace=Decimal('13'),
                                    valor_frete_logistica=0, valor_liquido_vendedor=Decimal('187'))
        TrackingEvent.objects.create(pedido=self.pedido, titulo='Objeto despachado', local='Curitiba/PR')

    def entrar(self, email, tipo):
        self.client.logout()
        self.client.login(username=email, password='senha1234')
        s = self.client.session
        s['tipo_usuario'] = tipo
        s.save()

    # ----------------------------------------------------------------- geral
    def test_indice_e_metodos(self):
        res = self.client.get('/api/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()['endpoints']) >= 8)
        self.assertEqual(self.client.post('/api/produtos/').status_code, 405)

    def test_sem_login_responde_401_em_json(self):
        for url in ['/api/carrinho/', '/api/notificacoes/', '/api/vendedor/estatisticas/',
                    f'/api/pedidos/{self.pedido.id}/rastreio/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 401, url)
            self.assertIn('erro', res.json())

    # ----------------------------------------------------------------- catálogo
    def test_busca_de_produtos_com_filtros(self):
        d = self.client.get('/api/produtos/?q=caneca').json()
        self.assertEqual(d['total'], 1)
        self.assertEqual(d['resultados'][0]['titulo'], 'Caneca azul')
        self.assertEqual(d['resultados'][0]['vendedor']['nome'], 'Loja da Fe')
        d = self.client.get('/api/produtos/?categoria=audio').json()
        self.assertEqual([p['titulo'] for p in d['resultados']], ['Fone sem fio'])
        d = self.client.get('/api/produtos/?preco_max=100&sort=menor_preco').json()
        self.assertEqual(d['total'], 1)
        d = self.client.get('/api/produtos/?sort=maior_preco').json()
        self.assertEqual(d['resultados'][0]['preco'], 200.0)

    # ----------------------------------------------------------------- painel
    def test_estatisticas_so_para_vendedor(self):
        self.entrar('c@avad.com', 'comprador')
        self.assertEqual(self.client.get('/api/vendedor/estatisticas/').status_code, 403)
        self.entrar('v@avad.com', 'vendedor')
        d = self.client.get('/api/vendedor/estatisticas/?periodo=total').json()
        self.assertEqual(d['periodo'], 'total')
        self.assertEqual(d['kpi']['bruto'], 200.0)
        self.assertEqual(d['kpi']['pedidos'], 1)
        self.assertEqual(d['mais_vendidos'][0]['titulo'], 'Fone sem fio')
        self.assertEqual(d['reputacao']['total_vendas'], 1)
        self.assertIsNone(d['grafico']['anterior'])
        d = self.client.get('/api/vendedor/estatisticas/?periodo=mensal').json()
        self.assertEqual(len(d['grafico']['atual']), len(d['grafico']['labels']))

    # ----------------------------------------------------------------- notificações
    def test_notificacoes_por_papel_e_marcar_lidas(self):
        Notification.objects.create(usuario=self.comprador, tipo_usuario='comprador', titulo='A', mensagem='a')
        Notification.objects.create(usuario=self.comprador, tipo_usuario='comprador', titulo='B', mensagem='b')
        Notification.objects.create(usuario=self.comprador, tipo_usuario='vendedor', titulo='C', mensagem='c')
        self.entrar('c@avad.com', 'comprador')
        d = self.client.get('/api/notificacoes/').json()
        self.assertEqual(d['nao_lidas'], 2)
        self.assertEqual({n['titulo'] for n in d['notificacoes']}, {'A', 'B'})
        self.assertEqual(d['notificacoes'][0]['quando'], 'agora mesmo')
        primeira = d['notificacoes'][0]['id']
        d = self.client.post(f'/api/notificacoes/{primeira}/lida/').json()
        self.assertEqual(d['nao_lidas'], 1)
        d = self.client.post('/api/notificacoes/marcar-todas/').json()
        self.assertEqual(d['nao_lidas'], 0)
        # a notificação do papel de vendedor continua não lida
        self.assertFalse(Notification.objects.get(titulo='C').lida)
        alheia = Notification.objects.create(usuario=self.outro, tipo_usuario='comprador', titulo='X', mensagem='x')
        self.assertEqual(self.client.post(f'/api/notificacoes/{alheia.id}/lida/').status_code, 404)

    # ----------------------------------------------------------------- carrinho
    def test_carrinho_completo(self):
        self.entrar('v@avad.com', 'vendedor')
        self.assertEqual(self.client.get('/api/carrinho/').status_code, 403)
        self.entrar('c@avad.com', 'comprador')
        post = lambda dados: self.client.post('/api/carrinho/', json.dumps(dados), content_type='application/json')

        res = post({'produto_id': self.caneca.id, 'quantidade': 2})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['subtotal'], 60.0)
        res = post({'produto_id': self.caneca.id, 'quantidade': 5})  # passa do estoque (3)
        self.assertEqual(res.json()['itens'][0]['quantidade'], 3)
        self.assertIn('ajustada', res.json()['aviso'])
        self.assertEqual(post({'produto_id': 9999}).status_code, 404)
        self.assertEqual(post({'produto_id': self.caneca.id, 'quantidade': 0}).status_code, 400)

        res = self.client.patch(f'/api/carrinho/{self.caneca.id}/', json.dumps({'quantidade': 1}), content_type='application/json')
        self.assertEqual(res.json()['unidades'], 1)
        res = self.client.patch(f'/api/carrinho/{self.caneca.id}/', json.dumps({'quantidade': 0}), content_type='application/json')
        self.assertEqual(res.json()['itens'], [])
        post({'produto_id': self.fone.id})
        res = self.client.delete(f'/api/carrinho/{self.fone.id}/')
        self.assertEqual(res.json()['itens'], [])
        self.assertFalse(CartItem.objects.exists())

    # ----------------------------------------------------------------- chat da disputa
    def test_chat_da_disputa(self):
        disputa = Dispute.objects.create(codigo='#T1', pedido=self.pedido, comprador=self.comprador,
                                         vendedor=self.vendedor, motivo='Defeito', descricao='x')
        url = f'/api/disputas/{disputa.id}/mensagens/'

        self.entrar('o@avad.com', 'comprador')
        self.assertEqual(self.client.get(url).status_code, 403)

        self.entrar('c@avad.com', 'comprador')
        self.assertEqual(self.client.post(url, {'mensagem': ''}).status_code, 400)
        foto = SimpleUploadedFile('f.png', b'\x89PNG\r\n\x1a\n' + b'0' * 20, content_type='image/png')
        res = self.client.post(url, {'mensagem': 'Veja a foto', 'evidencia': foto})
        self.assertEqual(res.status_code, 400)
        self.assertIn('nome_evidencia', res.json()['erros'])
        foto = SimpleUploadedFile('f.png', b'\x89PNG\r\n\x1a\n' + b'0' * 20, content_type='image/png')
        res = self.client.post(url, {'mensagem': 'Veja a foto', 'evidencia': foto, 'nome_evidencia': 'Foto do defeito'})
        self.assertEqual(res.status_code, 201)
        d = res.json()
        self.assertEqual(d['mensagens'][0]['papel'], 'comprador')
        self.assertTrue(d['mensagens'][0]['minha'])
        self.assertEqual(d['evidencias'][0]['titulo'], 'Foto do defeito')
        self.assertTrue(Notification.objects.filter(usuario=self.vendedor).exists())

        self.entrar('v@avad.com', 'vendedor')
        d = self.client.get(url).json()
        self.assertFalse(d['mensagens'][0]['minha'])
        self.entrar('m@avad.com', 'mediador')
        res = self.client.post(url, {'mensagem': 'Analisando'})
        self.assertEqual(res.json()['mensagens'][-1]['papel'], 'mediador')
        self.assertEqual(DisputeEvidence.objects.count(), 1)

        disputa.status = 'decidida_vendedor'
        disputa.save()
        self.assertEqual(self.client.post(url, {'mensagem': 'Depois'}).status_code, 409)
        self.assertFalse(self.client.get(url).json()['pode_enviar'])

    # ----------------------------------------------------------------- rastreio
    def test_rastreio(self):
        self.entrar('o@avad.com', 'comprador')
        self.assertEqual(self.client.get(f'/api/pedidos/{self.pedido.id}/rastreio/').status_code, 403)
        self.entrar('c@avad.com', 'comprador')
        d = self.client.get(f'/api/pedidos/{self.pedido.id}/rastreio/').json()
        self.assertEqual(d['pedido']['etapa'], 3)
        self.assertEqual(len(d['etapas']), 5)
        self.assertEqual(d['eventos'][0]['titulo'], 'Objeto despachado')
        self.entrar('v@avad.com', 'vendedor')
        self.assertEqual(self.client.get(f'/api/pedidos/{self.pedido.id}/rastreio/').status_code, 200)
        self.assertEqual(self.client.get('/api/pedidos/9999/rastreio/').status_code, 404)

    def test_paginas_tem_pontos_de_montagem_do_react(self):
        self.entrar('c@avad.com', 'comprador')
        self.assertContains(self.client.get('/catalog/'), 'data-react="catalogo"')
        self.assertContains(self.client.get('/orders/cart/'), 'data-react="carrinho"')
        res = self.client.get(f'/orders/tracking/{self.pedido.id}/')
        self.assertContains(res, 'data-react="rastreio"')
        self.assertContains(res, 'avad-react.js')
        self.assertContains(res, 'name="csrf-token"')
        self.assertContains(res, 'data-react="notificacoes"')
        self.entrar('v@avad.com', 'vendedor')
        self.assertContains(self.client.get('/dashboard/'), 'data-react="painel-vendedor"')
