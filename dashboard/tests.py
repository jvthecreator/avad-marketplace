import datetime
import json
from decimal import Decimal
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from catalog.models import Product
from finance.models import PaymentSplit
from orders.models import Order
from dashboard.stats import estatisticas_painel, limites_periodo

SP = ZoneInfo('America/Sao_Paulo')
# "Agora" fixo: quarta-feira, 25/11/2026 12:00 (horário de Brasília)
AGORA = datetime.datetime(2026, 11, 25, 12, 0, tzinfo=SP)


def dt(*args):
    return datetime.datetime(*args, tzinfo=SP)


class PainelVendedorTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='v@avad.com', password='senha1234')
        UserProfile.objects.create(user=self.seller, nome='Vend', data_nascimento=datetime.date(1990, 1, 1),
                                   cpf='000.000.000-00', email_verificado=True, tipo_usuario='vendedor')
        self.buyer = User.objects.create_user(username='c@avad.com', password='senha1234')
        self.product = Product.objects.create(vendedor=self.seller, titulo='Caneca', categoria='outros',
                                              descricao='x', preco=Decimal('10.00'), estoque=50)

    def pedido(self, quando, valor, qtd=1, status='entregue', liquido=None):
        o = Order.objects.create(comprador=self.buyer, vendedor=self.seller, produto=self.product,
                                 quantidade=qtd, preco_unitario=Decimal(valor) / qtd,
                                 valor_total=Decimal(valor), status=status)
        Order.objects.filter(pk=o.pk).update(criado_em=quando)  # criado_em é auto_now_add
        PaymentSplit.objects.create(pedido=o, total_pago=Decimal(valor), comissao_marketplace=0,
                                    valor_frete_logistica=0,
                                    valor_liquido_vendedor=Decimal(liquido if liquido is not None else valor),
                                    status_repasse='estornado' if status == 'cancelado' else 'programado')
        return o

    def painel(self, periodo):
        with mock.patch('django.utils.timezone.now', return_value=AGORA):
            return estatisticas_painel(self.seller, periodo)

    def test_limites_semana_comeca_no_domingo(self):
        inicio, inicio_ant, fim_eq, fim_ant = limites_periodo('semanal', AGORA)
        self.assertEqual(inicio, dt(2026, 11, 22))        # domingo
        self.assertEqual(inicio_ant, dt(2026, 11, 15))
        self.assertEqual(fim_eq, dt(2026, 11, 18, 12))     # quarta anterior, mesma hora
        self.assertEqual(fim_ant, inicio)

    def test_limites_mes_anterior_mais_curto(self):
        agora = dt(2026, 3, 31, 10)
        inicio, inicio_ant, fim_eq, _ = limites_periodo('mensal', agora)
        self.assertEqual(inicio, dt(2026, 3, 1))
        self.assertEqual(inicio_ant, dt(2026, 2, 1))
        self.assertEqual(fim_eq, dt(2026, 2, 28, 10))

    def test_semanal_conta_vendas_de_domingo_e_compara(self):
        self.pedido(dt(2026, 11, 22, 11), '20.00', qtd=2, liquido='18.70')  # domingo desta semana
        self.pedido(dt(2026, 11, 24, 9), '10.00')                           # terça desta semana
        self.pedido(dt(2026, 11, 16, 9), '15.00')                           # semana passada (antes de qua 12h)
        self.pedido(dt(2026, 11, 20, 9), '99.00')                           # semana passada, depois do mesmo ponto
        self.pedido(dt(2026, 11, 23, 9), '50.00', status='cancelado')       # não conta
        self.pedido(dt(2026, 11, 23, 9), '50.00', status='aguardando_pagamento')  # não conta

        p = self.painel('semanal')
        self.assertEqual(p['kpi']['bruto'], Decimal('30.00'))
        self.assertEqual(p['kpi']['liquido'], Decimal('28.70'))
        self.assertEqual(p['kpi']['pedidos'], 2)
        self.assertEqual(p['kpi']['unidades'], 3)
        self.assertEqual(p['comparacao']['bruto'], 100.0)      # 30 vs 15
        self.assertEqual(p['comparacao']['pedidos_diff'], 1)
        g = p['grafico']
        self.assertEqual(g['labels'][0], 'Dom')
        self.assertEqual(g['atual'][:4], [20.0, 0.0, 10.0, 0.0])
        self.assertIsNone(g['atual'][4])                       # quinta ainda não chegou
        self.assertEqual(g['anterior'], [0.0, 15.0, 0.0, 0.0, 0.0, 99.0, 0.0])  # gráfico mostra a semana inteira

    def test_anual_diario_e_total(self):
        self.pedido(dt(2025, 3, 10, 9), '40.00')
        self.pedido(dt(2026, 11, 25, 9), '12.00')
        self.pedido(dt(2026, 11, 24, 9), '8.00')

        anual = self.painel('anual')
        self.assertEqual(anual['kpi']['bruto'], Decimal('20.00'))
        self.assertEqual(anual['comparacao']['bruto'], -50.0)  # 20 vs 40
        self.assertEqual(anual['grafico']['anterior'][2], 40.0)
        self.assertEqual(anual['grafico']['atual'][10], 20.0)
        self.assertIsNone(anual['grafico']['atual'][11])

        diario = self.painel('diario')
        self.assertEqual(diario['kpi']['bruto'], Decimal('12.00'))
        self.assertEqual(diario['grafico']['atual'][9], 12.0)
        self.assertEqual(diario['grafico']['anterior'][9], 8.0)
        self.assertEqual(diario['melhor_momento']['valor'], '9h às 10h')

        total = self.painel('total')
        self.assertEqual(total['kpi']['bruto'], Decimal('60.00'))
        self.assertIsNone(total['comparacao'])
        self.assertEqual(total['grafico']['labels'], ['2025', '2026'])
        self.assertEqual(total['grafico']['atual'], [40.0, 20.0])

    def test_pagina_do_painel_em_todos_os_periodos(self):
        self.pedido(dt(2026, 11, 22, 11), '20.00')
        self.client.login(username='v@avad.com', password='senha1234')
        s = self.client.session
        s['tipo_usuario'] = 'vendedor'
        s.save()
        for periodo, titulo in [('total', 'Vendas desde o começo'), ('anual', 'Vendas no ano'),
                                ('mensal', 'Vendas no mês'), ('semanal', 'Vendas na semana'),
                                ('diario', 'Vendas hoje'), ('invalido', 'Vendas no mês')]:
            with mock.patch('django.utils.timezone.now', return_value=AGORA):
                res = self.client.get(f'/dashboard/?periodo={periodo}')
            self.assertContains(res, titulo)
            self.assertContains(res, 'id="sales-chart-data"')
        # semana de domingo: a venda de domingo aparece em "Vendas na semana"
        with mock.patch('django.utils.timezone.now', return_value=AGORA):
            res = self.client.get('/dashboard/?periodo=semanal')
        self.assertContains(res, 'R$ 20,00')
        self.assertContains(res, 'selected>Semanal')
