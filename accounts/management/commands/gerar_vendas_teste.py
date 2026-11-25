"""Gera vendas de TESTE para um vendedor, espalhadas no tempo, para testar o painel.

Uso:
    python manage.py gerar_vendas_teste --vendedor e@gmail.com
    python manage.py gerar_vendas_teste --vendedor e@gmail.com --pedidos 300 --dias 730 --disputas 10
    python manage.py gerar_vendas_teste --vendedor e@gmail.com --limpar      (apaga só os dados de teste)

Tudo o que este comando cria é marcado (pedidos com código "#TESTE-...", disputas "#TST...")
e comprado por um comprador fictício, então --limpar remove apenas esses dados, sem mexer
nos pedidos reais. O estoque dos produtos NÃO é alterado.
"""
import datetime
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from disputes.models import Dispute
from finance.models import PaymentSplit
from orders.models import Order, Review

PREFIXO_PEDIDO = '#TESTE-'
PREFIXO_DISPUTA = '#TST'
EMAIL_COMPRADOR = 'comprador.teste@avad.com'
COMISSAO = Decimal('0.065')  # mesma taxa do checkout (orders/views.py)


class Command(BaseCommand):
    help = 'Gera pedidos, splits, avaliações e disputas de teste para um vendedor (para testar o painel).'

    def add_arguments(self, parser):
        parser.add_argument('--vendedor', required=True, help='E-mail/usuário do vendedor')
        parser.add_argument('--pedidos', type=int, default=150, help='Quantidade de pedidos (padrão: 150)')
        parser.add_argument('--dias', type=int, default=500, help='Espalhar os pedidos pelos últimos N dias (padrão: 500)')
        parser.add_argument('--disputas', type=int, default=6, help='Quantidade de disputas (padrão: 6)')
        parser.add_argument('--limpar', action='store_true', help='Apaga os dados de teste deste vendedor e sai')
        parser.add_argument('--seed', type=int, default=None, help='Semente aleatória (para gerar sempre os mesmos dados)')

    def handle(self, *args, **opts):
        try:
            vendedor = User.objects.get(username=opts['vendedor'])
        except User.DoesNotExist:
            raise CommandError(f"Vendedor '{opts['vendedor']}' não encontrado.")

        if opts['limpar']:
            self.limpar(vendedor)
            return

        produtos = list(vendedor.products.filter(removido=False))
        if not produtos:
            raise CommandError('Este vendedor não tem produtos. Cadastre pelo menos um antes de gerar vendas.')

        rnd = random.Random(opts['seed'])
        comprador = self.comprador_teste()
        retido = bool(getattr(vendedor, 'profile', None) and vendedor.profile.conta_bancaria_bloqueada)
        agora = timezone.localtime()

        with transaction.atomic():
            datas = self.datas(rnd, agora, opts['pedidos'], opts['dias'])
            pedidos = [self.criar_pedido(rnd, vendedor, comprador, rnd.choice(produtos), quando, agora, retido)
                       for quando in datas]
            n_disputas = self.criar_disputas(rnd, vendedor, comprador, pedidos, opts['disputas'])

        vendas = [p for p in pedidos if p.status != 'cancelado']
        total = sum((p.valor_total for p in vendas), Decimal('0'))
        self.stdout.write(self.style.SUCCESS(
            f'{len(pedidos)} pedidos de teste criados ({len(pedidos) - len(vendas)} cancelados), '
            f'R$ {total:.2f} em vendas e {n_disputas} disputas, para {vendedor.username}.'
        ))
        self.stdout.write(f'Para apagar depois: python manage.py gerar_vendas_teste --vendedor {vendedor.username} --limpar')

    # ------------------------------------------------------------------ auxiliares

    def comprador_teste(self):
        user, criado = User.objects.get_or_create(username=EMAIL_COMPRADOR, defaults={'email': EMAIL_COMPRADOR})
        if criado:
            user.set_password('senha1234')
            user.save()
        UserProfile.objects.get_or_create(user=user, defaults={
            'nome': 'Comprador Teste', 'data_nascimento': datetime.date(1990, 1, 1),
            'cpf': '000.000.000-99', 'email_verificado': True,
        })
        return user

    def datas(self, rnd, agora, quantidade, dias):
        """Datas aleatórias nos últimos `dias`, garantindo pedidos hoje, ontem, nesta semana e na passada
        (para todos os modos do painel terem o que mostrar). Mais vendas nos meses recentes."""
        datas = []
        hoje_0h = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        horas_ate_agora = max(agora.hour, 1)
        # garantidos: 3 hoje (até agora), 3 ontem, alguns nos últimos 14 dias
        for _ in range(3):
            datas.append(hoje_0h + datetime.timedelta(hours=rnd.uniform(0, horas_ate_agora)))
            datas.append(hoje_0h - datetime.timedelta(days=1) + datetime.timedelta(hours=rnd.uniform(8, 22)))
        for _ in range(8):
            datas.append(agora - datetime.timedelta(days=rnd.uniform(1, 14)))
        while len(datas) < quantidade:
            # distribuição que favorece datas recentes
            dias_atras = dias * (rnd.random() ** 1.6)
            quando = agora - datetime.timedelta(days=dias_atras)
            quando = quando.replace(hour=rnd.choice(range(8, 23)), minute=rnd.randrange(60))
            if quando <= agora:
                datas.append(quando)
        return sorted(datas)  # se --pedidos for menor que 14, os 14 garantidos são criados mesmo assim

    def criar_pedido(self, rnd, vendedor, comprador, produto, quando, agora, retido):
        idade = agora - quando
        if rnd.random() < 0.06:
            status = 'cancelado'
        elif idade < datetime.timedelta(days=1):
            status = rnd.choice(['aguardando_confirmacao', 'preparando'])
        elif idade < datetime.timedelta(days=5):
            status = rnd.choice(['preparando', 'a_caminho', 'entregue'])
        else:
            status = 'entregue'

        qtd = rnd.choices([1, 2, 3], weights=[75, 20, 5])[0]
        frete = Decimal('0') if produto.frete_gratis else Decimal(rnd.choice(['18.90', '24.50', '32.00']))
        subtotal = produto.preco * qtd
        total = subtotal + frete

        while True:  # código único marcado como teste
            codigo = f'{PREFIXO_PEDIDO}{rnd.randrange(10**6):06d}'
            if not Order.objects.filter(codigo=codigo).exists():
                break

        pedido = Order.objects.create(
            codigo=codigo, comprador=comprador, vendedor=vendedor, produto=produto, quantidade=qtd,
            preco_unitario=produto.preco, valor_frete=frete, valor_total=total,
            metodo_frete=rnd.choice(['pac', 'sedex']), forma_pagamento=rnd.choice(['cartao', 'pix', 'boleto']),
            cep_entrega='01001-000', endereco_entrega='Endereço de teste', status=status,
            recebimento_confirmado=(status == 'entregue' and idade > datetime.timedelta(days=14)),
        )
        # criado_em/entregue_em são automáticos: ajusta para a data simulada
        entregue_em = quando + datetime.timedelta(days=rnd.randint(2, 7)) if status == 'entregue' else None
        if entregue_em and entregue_em > agora:
            entregue_em = agora
        Order.objects.filter(pk=pedido.pk).update(criado_em=quando, entregue_em=entregue_em)
        pedido.criado_em = quando

        comissao = round(subtotal * COMISSAO, 2)
        PaymentSplit.objects.create(
            pedido=pedido, total_pago=total, comissao_marketplace=comissao, valor_frete_logistica=frete,
            valor_liquido_vendedor=subtotal - comissao,
            status_repasse='estornado' if status == 'cancelado' else (
                'retido' if retido else ('realizado' if pedido.recebimento_confirmado else 'programado')),
        )

        if status == 'entregue' and rnd.random() < 0.35:
            Review.objects.create(
                pedido=pedido, comprador=comprador, vendedor=vendedor,
                nota_vendedor=rnd.choices([5, 4, 3, 2, 1], weights=[50, 28, 12, 6, 4])[0],
                nota_transporte=rnd.choice([3, 4, 5]),
                comentario_vendedor=rnd.choice(['', '', 'Chegou certinho, recomendo!', 'Bom produto.',
                                                'Demorou um pouco, mas veio tudo certo.']),
            )
        return pedido

    def criar_disputas(self, rnd, vendedor, comprador, pedidos, quantidade):
        candidatos = [p for p in pedidos if p.status == 'entregue']
        rnd.shuffle(candidatos)
        criadas = 0
        for pedido in candidatos[:quantidade]:
            while True:
                codigo = f'{PREFIXO_DISPUTA}{rnd.randrange(10**6):06d}'
                if not Dispute.objects.filter(codigo=codigo).exists():
                    break
            status = rnd.choices(['decidida_vendedor', 'decidida_comprador', 'em_analise'], weights=[55, 30, 15])[0]
            Dispute.objects.create(
                codigo=codigo, pedido=pedido, comprador=comprador, vendedor=vendedor,
                motivo=rnd.choice(['Produto com defeito', 'Produto diferente do anúncio', 'Não recebi o produto']),
                descricao='Disputa gerada para testes.', status=status,
                fundamentacao_mediador='' if status == 'em_analise' else 'Decisão gerada para testes.',
            )
            if status == 'decidida_comprador':  # como na mediação real: pedido estornado
                Order.objects.filter(pk=pedido.pk).update(status='cancelado')
                PaymentSplit.objects.filter(pedido=pedido).update(status_repasse='estornado')
            criadas += 1
        return criadas

    def limpar(self, vendedor):
        disputas = Dispute.objects.filter(vendedor=vendedor, codigo__startswith=PREFIXO_DISPUTA)
        pedidos = Order.objects.filter(vendedor=vendedor, codigo__startswith=PREFIXO_PEDIDO)
        n_d = disputas.count()
        n_p = pedidos.count()
        disputas.delete()
        pedidos.delete()  # splits, avaliações e eventos de rastreio vão junto (CASCADE)
        self.stdout.write(self.style.SUCCESS(f'Removidos {n_p} pedidos e {n_d} disputas de teste de {vendedor.username}.'))
