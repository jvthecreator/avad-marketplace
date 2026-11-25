import datetime
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
from orders.models import Order

MEDIA_TESTE = tempfile.mkdtemp()


def png(nome='foto.png'):
    return SimpleUploadedFile(nome, b'\x89PNG\r\n\x1a\n' + b'0' * 50, content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class NomeDaEvidenciaTests(TestCase):
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
        self.buyer = usuario('c@avad.com', 'Ze', '1')
        self.seller = usuario('v@avad.com', 'Fe', '2')
        self.mediator = usuario('m@avad.com', 'Ana', '3', is_mediador=True)
        product = Product.objects.create(vendedor=self.seller, titulo='Caneca', categoria='outros', descricao='x',
                                         preco=Decimal('10.00'), estoque=5)
        self.order = Order.objects.create(comprador=self.buyer, vendedor=self.seller, produto=product,
                                          preco_unitario=Decimal('10.00'), valor_total=Decimal('10.00'), status='entregue')
        PaymentSplit.objects.create(pedido=self.order, total_pago=Decimal('10.00'), comissao_marketplace=Decimal('0.65'),
                                    valor_frete_logistica=0, valor_liquido_vendedor=Decimal('9.35'))

    def entrar(self, email, tipo):
        self.client.login(username=email, password='senha1234')
        s = self.client.session
        s['tipo_usuario'] = tipo
        s.save()

    def abrir_disputa(self, **extra):
        self.entrar('c@avad.com', 'comprador')
        dados = {'motivo': 'Produto com defeito', 'descricao': 'Chegou quebrado.', **extra}
        return self.client.post(f'/disputes/open/{self.order.id}/', dados)

    def test_abrir_disputa_com_arquivo_exige_nome(self):
        res = self.abrir_disputa(evidencia=png())
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Dê um nome para a evidência')
        self.assertFalse(Dispute.objects.exists())

        res = self.abrir_disputa(evidencia=png(), nome_evidencia='  Foto da caneca quebrada ')
        self.assertEqual(res.status_code, 302)
        ev = DisputeEvidence.objects.get()
        self.assertEqual(ev.nome, 'Foto da caneca quebrada')
        self.assertEqual(ev.titulo, 'Foto da caneca quebrada')

    def test_nome_sem_arquivo_da_erro_e_disputa_sem_anexo_continua_funcionando(self):
        res = self.abrir_disputa(nome_evidencia='Foto')
        self.assertContains(res, 'não escolheu o arquivo')
        res = self.abrir_disputa()
        self.assertEqual(res.status_code, 302)
        self.assertFalse(DisputeEvidence.objects.exists())

    def test_mensagens_das_partes_e_do_mediador_com_nome(self):
        self.abrir_disputa()
        disputa = Dispute.objects.get()

        self.client.logout()
        self.entrar('v@avad.com', 'vendedor')
        res = self.client.post(f'/disputes/detail/{disputa.id}/', {'mensagem': 'Segue o comprovante.', 'evidencia': png()})
        self.assertContains(res, 'Dê um nome para a evidência')
        res = self.client.post(f'/disputes/detail/{disputa.id}/', {'mensagem': 'Segue o comprovante.', 'evidencia': png(),
                                                                   'nome_evidencia': 'Comprovante de envio'})
        self.assertEqual(res.status_code, 302)
        res = self.client.get(f'/disputes/detail/{disputa.id}/')
        self.assertContains(res, 'Comprovante de envio')

        self.client.logout()
        self.entrar('m@avad.com', 'mediador')
        res = self.client.post(f'/disputes/mediation/{disputa.id}/', {
            'action_type': 'message', 'mensagem': 'Laudo anexado.', 'evidencia': png('laudo.png'), 'nome_evidencia': 'Laudo técnico'})
        self.assertEqual(res.status_code, 302)
        res = self.client.get(f'/disputes/mediation/{disputa.id}/')
        self.assertContains(res, 'Comprovante de envio')
        self.assertContains(res, 'Laudo técnico')
        self.assertEqual(list(disputa.evidences.values_list('nome', flat=True)), ['Comprovante de envio', 'Laudo técnico'])

    def test_arquivo_invalido_na_mensagem_e_recusado(self):
        self.abrir_disputa()
        disputa = Dispute.objects.get()
        arquivo = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        res = self.client.post(f'/disputes/detail/{disputa.id}/', {'mensagem': 'x', 'evidencia': arquivo, 'nome_evidencia': 'X'})
        self.assertContains(res, 'Formato de arquivo inválido')
        self.assertFalse(DisputeEvidence.objects.exists())

    def test_evidencia_antiga_sem_nome_usa_descricao(self):
        self.abrir_disputa()
        ev = DisputeEvidence(disputa=Dispute.objects.get(), autor=self.buyer, descricao='Anexo enviado por Ze')
        self.assertEqual(ev.titulo, 'Anexo enviado por Ze')
