from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from pathlib import Path
import datetime
from decimal import Decimal

from accounts.models import UserProfile, SavedCard
from catalog.models import Product
from orders.models import Order, TrackingEvent, Review, RefundRequest
from finance.models import PaymentSplit
from disputes.models import Dispute, DisputeMessage, DisputeEvidence


def create_svg_placeholder(title, bg_color="#1F2937", text_color="#FFFFFF"):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="450" viewBox="0 0 600 450">
  <rect width="600" height="450" fill="{bg_color}"/>
  <circle cx="300" cy="180" r="70" fill="rgba(255,255,255,0.08)"/>
  <text x="300" y="195" font-family="system-ui, -apple-system, sans-serif" font-size="48" fill="{text_color}" text-anchor="middle" font-weight="bold">AVaD</text>
  <text x="300" y="300" font-family="system-ui, -apple-system, sans-serif" font-size="20" fill="{text_color}" text-anchor="middle" font-weight="600">{title}</text>
  <text x="300" y="330" font-family="system-ui, -apple-system, sans-serif" font-size="13" fill="rgba(255,255,255,0.6)" text-anchor="middle">Assurance, Value and Dealing &#8226; Produto Verificado</text>
</svg>'''
    return svg.encode('utf-8')


class Command(BaseCommand):
    help = 'Popula o banco de dados SQLite com usuários, catálogo, pedidos, splits e disputas de teste.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando seed do AVaD Marketplace...")

        # 1. Usuários de Teste
        # Comprador
        user_comprador, _ = User.objects.get_or_create(
            username='marina@avad.com',
            email='marina@avad.com'
        )
        user_comprador.set_password('senha1234')
        user_comprador.save()
        UserProfile.objects.update_or_create(
            user=user_comprador,
            defaults={
                'nome': 'Marina Silva',
                'data_nascimento': datetime.date(1995, 5, 14),
                'cpf': '123.456.789-01',
                'tem_cnpj': False,
                'email_verificado': True,
                'is_mediador': False,
                'tipo_usuario': 'comprador',
            }
        )

        # Cartão Salvo para Marina
        SavedCard.objects.get_or_create(
            usuario=user_comprador,
            ultimos_digitos='4242',
            defaults={
                'bandeira': 'Mastercard',
                'nome_impresso': 'MARINA SILVA',
                'validade': '11/29',
                'cpf_titular': '123.456.789-01'
            }
        )

        # Vendedor 1 (Felipe Tech - Conta Normal)
        user_vendedor1, _ = User.objects.get_or_create(
            username='felipe@lojadech.com',
            email='felipe@lojadech.com'
        )
        user_vendedor1.set_password('senha1234')
        user_vendedor1.save()
        UserProfile.objects.update_or_create(
            user=user_vendedor1,
            defaults={
                'nome': 'Felipe Santos',
                'nome_loja': 'Tech Store Oficial',
                'data_nascimento': datetime.date(1990, 10, 20),
                'cpf': '987.654.321-00',
                'cnpj': '12.345.678/0001-90',
                'tem_cnpj': True,
                'email_verificado': True,
                'is_mediador': False,
                'conta_bancaria_bloqueada': False,
                'tipo_usuario': 'vendedor',
            }
        )

        # Vendedor 2 (Carlos Móveis - Conta Bloqueada para Escrow)
        user_vendedor2, _ = User.objects.get_or_create(
            username='loja2@avad.com',
            email='loja2@avad.com'
        )
        user_vendedor2.set_password('senha1234')
        user_vendedor2.save()
        UserProfile.objects.update_or_create(
            user=user_vendedor2,
            defaults={
                'nome': 'Carlos Eduardo',
                'nome_loja': 'Casa &amp; Conforto Mobiliário',
                'data_nascimento': datetime.date(1988, 3, 15),
                'cpf': '555.444.333-22',
                'cnpj': '99.888.777/0001-11',
                'tem_cnpj': True,
                'email_verificado': True,
                'is_mediador': False,
                'conta_bancaria_bloqueada': True,  # Reter repasses em Escrow
                'tipo_usuario': 'vendedor',
            }
        )

        # Mediador (Suporte de Vendas)
        user_mediador, _ = User.objects.get_or_create(
            username='mediador@avad.com',
            email='mediador@avad.com'
        )
        user_mediador.set_password('senha1234')
        user_mediador.is_staff = True
        user_mediador.save()
        UserProfile.objects.update_or_create(
            user=user_mediador,
            defaults={
                'nome': 'Ana Mediadora',
                'data_nascimento': datetime.date(1985, 7, 8),
                'cpf': '111.222.333-44',
                'tem_cnpj': False,
                'email_verificado': True,
                'is_mediador': True,
                'tipo_usuario': 'mediador',
            }
        )

        self.stdout.write("Usuários criados com sucesso.")

        # 2. Catálogo de Produtos e Serviços (8 itens)
        produtos_dados = [
            {
                'vendedor': user_vendedor1,
                'titulo': 'Smartphone Ultra Pro Max 256GB 5G',
                'categoria': 'tecnologia',
                'descricao': 'Smartphone de última geração com processador neural de alto desempenho, câmera quádrupla de 108MP com estabilização óptica, tela OLED de 120Hz e bateria de 5000mAh para até 48 horas de uso contínuo.',
                'caracteristicas': 'Processador Octa-Core de 3.2GHz\n256GB Armazenamento UFS 4.0\n12GB Memória RAM LPDDR5X\nCarregamento Ultrarrápido 65W\nProteção contra água IP68',
                'preco': Decimal('4299.00'),
                'estoque': 18,
                'frete_gratis': True,
                'color': '#1E293B',
            },
            {
                'vendedor': user_vendedor1,
                'titulo': 'Headphone Bluetooth ANC Noise Cancelling',
                'categoria': 'audio',
                'descricao': 'Áudio de alta fidelidade com cancelamento ativo de ruído inteligente, drivers de titânio de 40mm e autonomia estendida para até 35 horas de reprodução contínua.',
                'caracteristicas': 'Cancelamento Ativo de Ruído Híbrido\nBluetooth 5.3 com codec LDAC\nMicrofones integrados com IA para chamadas\nAlmofadas viscoelásticas ultra confortáveis',
                'preco': Decimal('589.90'),
                'estoque': 25,
                'frete_gratis': True,
                'color': '#0F172A',
            },
            {
                'vendedor': user_vendedor1,
                'titulo': 'Smart TV 55 polegadas 4K Crystal UHD HDR10+',
                'categoria': 'eletronicos',
                'descricao': 'Experiência de cinema em casa com bordas infinitas, painel de contraste dinâmico, comando de voz integrado e sistema operacional veloz com suporte a todos os streamings.',
                'caracteristicas': 'Resolução 4K UHD 3840x2160\nHDR10+ e Áudio Dolby Atmos\nConexões Wi-Fi 5GHz e Bluetooth\n3 portas HDMI 2.1 e 2 portas USB',
                'preco': Decimal('2699.00'),
                'estoque': 8,
                'frete_gratis': False,
                'color': '#1E3A8A',
            },
            {
                'vendedor': user_vendedor1,
                'titulo': 'Drone 4K Profissional com Gimbal de 3 Eixos',
                'categoria': 'tecnologia',
                'descricao': 'Drone dobrável de alta precisão para filmagens cinematográficas com retorno automático GPS, sensores omnidirecionais anti-colisão e alcance de até 10km.',
                'caracteristicas': 'Câmera 4K 60fps com sensor 1/2 polegada\nGimbal mecânico estabilizado em 3 eixos\nTempo de voo de até 31 minutos por bateria\nModos inteligentes de rastreamento de objeto',
                'preco': Decimal('3499.00'),
                'estoque': 6,
                'frete_gratis': True,
                'color': '#047857',
            },
            {
                'vendedor': user_vendedor2,
                'titulo': 'Cadeira Ergonômica Presidente em Mesh Premium',
                'categoria': 'decoracao',
                'descricao': 'Design anatômico ergonômico certificado pela NR17 com suporte lombar dinâmico ajustável, apoio de braços 3D e mecanismo syncron de reclinação suave.',
                'caracteristicas': 'Estrutura reforçada suporta até 150kg\nTecido Mesh respirável de alta durabilidade\nApoio de cabeça com ajuste de altura e ângulo\nRodízios de PU anti-risco para piso de madeira',
                'preco': Decimal('1190.00'),
                'estoque': 3,  # Estoque baixo para gerar alerta no dashboard!
                'frete_gratis': False,
                'color': '#374151',
            },
            {
                'vendedor': user_vendedor2,
                'titulo': 'Cafeteira Espresso Automática com Moedor de Grãos',
                'categoria': 'eletrodomesticos',
                'descricao': 'Café espresso fresco do grão à xícara com pressão profissional de 19 bar, bico vaporizador de leite em aço inoxidável e 5 níveis de moagem personalizada.',
                'caracteristicas': 'Bomba italiana de 19 bar de pressão\nReservatório de água removível de 1.8L\nMoedor cônico de cerâmica integrado\nPainel digital touch com memória de receitas',
                'preco': Decimal('849.00'),
                'estoque': 12,
                'frete_gratis': False,
                'color': '#78350F',
            },
            {
                'vendedor': user_vendedor1,
                'titulo': 'Consultoria Especializada em Otimização Web e SEO',
                'categoria': 'servicos',
                'descricao': 'Pacote profissional de auditoria técnica de performance, arquitetura de software, otimização de banco de dados e estratégias de SEO para marketplaces e portais.',
                'caracteristicas': 'Auditoria de Core Web Vitals e renderização\nRevisão de infraestrutura de cache e consultas SQL\nRelatório executivo com roadmap de melhorias\n2 sessões de alinhamento com medição técnica',
                'preco': Decimal('1500.00'),
                'estoque': 50,
                'frete_gratis': True,
                'color': '#4338CA',
            },
            {
                'vendedor': user_vendedor1,
                'titulo': 'Caixa de Som Acústica Portátil Resistente à Água',
                'categoria': 'audio',
                'descricao': 'Potência sonora cristalina de 40W com radiadores passivos duplos para graves profundos, iluminação LED personalizável e certificação IPX7 à prova dágua.',
                'caracteristicas': 'Potência 40W RMS com Bass Boost\nBateria de 12 horas de duração\nCertificação IPX7 submersível\nEmparelhamento estéreo TWS com outra unidade',
                'preco': Decimal('320.00'),
                'estoque': 20,
                'frete_gratis': False,
                'color': '#B91C1C',
            },
        ]

        produtos_objs = []
        for pdata in produtos_dados:
            prod, created = Product.objects.get_or_create(
                titulo=pdata['titulo'],
                defaults={
                    'vendedor': pdata['vendedor'],
                    'categoria': pdata['categoria'],
                    'descricao': pdata['descricao'],
                    'caracteristicas': pdata['caracteristicas'],
                    'preco': pdata['preco'],
                    'estoque': pdata['estoque'],
                    'frete_gratis': pdata['frete_gratis'],
                    'ativo': True,
                }
            )
            # Gerar imagem SVG placeholder local se não houver
            if not prod.imagem:
                svg_content = create_svg_placeholder(prod.titulo[:24], bg_color=pdata['color'])
                filename = f"prod_{prod.id}_{prod.categoria}.svg"
                prod.imagem.save(filename, ContentFile(svg_content), save=True)
            produtos_objs.append(prod)

        self.stdout.write("8 produtos e imagens placeholders gerados.")

        # 3. Pedidos em Diferentes Estados & Splits Financeiros
        p1 = produtos_objs[0]  # Smartphone
        p2 = produtos_objs[1]  # Headphone
        p3 = produtos_objs[2]  # TV
        p5 = produtos_objs[4]  # Cadeira (Vendedor 2 - Escrow retido)
        p6 = produtos_objs[5]  # Cafeteira

        # Pedido 1: Entregue + Avaliado + Repasse Realizado
        order1, _ = Order.objects.get_or_create(
            codigo='#AV-2026-08856',
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'produto': p2,
                'quantidade': 1,
                'preco_unitario': p2.preco,
                'valor_frete': Decimal('0.00'),
                'metodo_frete': 'pac',
                'prazo_dias': 8,
                'valor_total': p2.preco,
                'forma_pagamento': 'cartao',
                'parcelas': 3,
                'cep_entrega': '01310-100',
                'endereco_entrega': 'Av. Paulista, 1000, Apto 42 - Bela Vista, São Paulo/SP',
                'codigo_rastreio': 'BR982341234AV',
                'status': 'entregue',
                'recebimento_confirmado': True,
                'criado_em': timezone.now() - datetime.timedelta(days=25),
            }
        )
        TrackingEvent.objects.get_or_create(
            pedido=order1,
            titulo='Item entregue com sucesso',
            defaults={'descricao': 'Entregue ao destinatário.', 'local': 'São Paulo/SP'}
        )
        PaymentSplit.objects.update_or_create(
            pedido=order1,
            defaults={
                'total_pago': order1.valor_total,
                'comissao_marketplace': round(order1.valor_total * Decimal('0.065'), 2),
                'valor_frete_logistica': order1.valor_frete,
                'valor_liquido_vendedor': order1.valor_total - round(order1.valor_total * Decimal('0.065'), 2),
                'status_repasse': 'realizado',
            }
        )
        Review.objects.update_or_create(
            pedido=order1,
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'nota_vendedor': 5,
                'comentario_vendedor': 'Excelente fone de ouvido, isolamento acústico impressionante e chegou bem antes do prazo!',
                'nota_transporte': 5,
                'comentario_transporte': 'Entrega muito rápida e embalagem reforçada.',
            }
        )

        # Pedido 2: Entregue + Repasse Programado
        order2, _ = Order.objects.get_or_create(
            codigo='#AV-2026-08890',
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'produto': p1,
                'quantidade': 1,
                'preco_unitario': p1.preco,
                'valor_frete': Decimal('0.00'),
                'metodo_frete': 'avad_express',
                'prazo_dias': 2,
                'valor_total': p1.preco,
                'forma_pagamento': 'pix',
                'parcelas': 1,
                'cep_entrega': '01310-100',
                'endereco_entrega': 'Av. Paulista, 1000 - São Paulo/SP',
                'codigo_rastreio': 'BR881234789AV',
                'status': 'entregue',
                'recebimento_confirmado': True,
                'criado_em': timezone.now() - datetime.timedelta(days=5),
            }
        )
        PaymentSplit.objects.update_or_create(
            pedido=order2,
            defaults={
                'total_pago': order2.valor_total,
                'comissao_marketplace': round(order2.valor_total * Decimal('0.065'), 2),
                'valor_frete_logistica': Decimal('0.00'),
                'valor_liquido_vendedor': order2.valor_total - round(order2.valor_total * Decimal('0.065'), 2),
                'status_repasse': 'programado',
            }
        )
        Review.objects.update_or_create(
            pedido=order2,
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'nota_vendedor': 5,
                'comentario_vendedor': 'Aparelho fantástico, acabamento premium e câmera surreal. Loja confiável!',
                'nota_transporte': 5,
                'comentario_transporte': 'AVAD Express entregou em 24 horas!',
            }
        )

        # Pedido 3: A Caminho (Status em andamento)
        order3, _ = Order.objects.get_or_create(
            codigo='#AV-2026-09120',
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'produto': p3,
                'quantidade': 1,
                'preco_unitario': p3.preco,
                'valor_frete': Decimal('45.90'),
                'metodo_frete': 'sedex',
                'prazo_dias': 3,
                'valor_total': p3.preco + Decimal('45.90'),
                'forma_pagamento': 'cartao',
                'parcelas': 6,
                'cep_entrega': '01310-100',
                'endereco_entrega': 'Av. Paulista, 1000 - São Paulo/SP',
                'codigo_rastreio': 'BR771234999AV',
                'status': 'a_caminho',
                'recebimento_confirmado': False,
                'criado_em': timezone.now() - datetime.timedelta(days=1),
            }
        )
        TrackingEvent.objects.get_or_create(
            pedido=order3,
            titulo='Objeto em trânsito para a unidade de distribuição',
            defaults={'descricao': 'Em rota entre o centro logístico e seu endereço.', 'local': 'Campinas/SP'}
        )
        PaymentSplit.objects.update_or_create(
            pedido=order3,
            defaults={
                'total_pago': order3.valor_total,
                'comissao_marketplace': round(p3.preco * Decimal('0.065'), 2),
                'valor_frete_logistica': Decimal('45.90'),
                'valor_liquido_vendedor': p3.preco - round(p3.preco * Decimal('0.065'), 2),
                'status_repasse': 'programado',
            }
        )

        # Pedido 4: Vendedor 2 com Conta Bloqueada (Escrow Retido)
        order4, _ = Order.objects.get_or_create(
            codigo='#AV-2026-09255',
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor2,
                'produto': p5,
                'quantidade': 1,
                'preco_unitario': p5.preco,
                'valor_frete': Decimal('58.00'),
                'metodo_frete': 'avad_express',
                'prazo_dias': 2,
                'valor_total': p5.preco + Decimal('58.00'),
                'forma_pagamento': 'cartao',
                'parcelas': 10,
                'cep_entrega': '01310-100',
                'endereco_entrega': 'Av. Paulista, 1000 - São Paulo/SP',
                'codigo_rastreio': 'BR665544332AV',
                'status': 'a_caminho',
                'recebimento_confirmado': False,
                'criado_em': timezone.now() - datetime.timedelta(hours=14),
            }
        )
        PaymentSplit.objects.update_or_create(
            pedido=order4,
            defaults={
                'total_pago': order4.valor_total,
                'comissao_marketplace': round(p5.preco * Decimal('0.065'), 2),
                'valor_frete_logistica': Decimal('58.00'),
                'valor_liquido_vendedor': p5.preco - round(p5.preco * Decimal('0.065'), 2),
                'status_repasse': 'retido',  # Demonstração de Escrow por conta bloqueada
            }
        )

        # 4. Caso de Conflito Aberto para PRO007: Disputa #PRO007
        order_dispute, _ = Order.objects.get_or_create(
            codigo='#AV-2026-07712',
            defaults={
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'produto': p6,
                'quantidade': 1,
                'preco_unitario': p6.preco,
                'valor_frete': Decimal('22.50'),
                'metodo_frete': 'pac',
                'prazo_dias': 8,
                'valor_total': p6.preco + Decimal('22.50'),
                'forma_pagamento': 'cartao',
                'parcelas': 4,
                'cep_entrega': '01310-100',
                'endereco_entrega': 'Av. Paulista, 1000 - São Paulo/SP',
                'codigo_rastreio': 'BR339911882AV',
                'status': 'a_caminho',
                'recebimento_confirmado': False,
                'criado_em': timezone.now() - datetime.timedelta(days=9),
            }
        )
        TrackingEvent.objects.get_or_create(
            pedido=order_dispute,
            titulo='Atraso reportado no trajeto logístico',
            defaults={'descricao': 'Objeto retido para conferência em posto fiscal.', 'local': 'Curitiba/PR'}
        )
        # Split com repasse retido em escrow preventivo
        PaymentSplit.objects.update_or_create(
            pedido=order_dispute,
            defaults={
                'total_pago': order_dispute.valor_total,
                'comissao_marketplace': round(p6.preco * Decimal('0.065'), 2),
                'valor_frete_logistica': Decimal('22.50'),
                'valor_liquido_vendedor': p6.preco - round(p6.preco * Decimal('0.065'), 2),
                'status_repasse': 'retido',
            }
        )

        # Criação da Disputa #PRO007
        dispute, _ = Dispute.objects.get_or_create(
            codigo='#PRO007',
            defaults={
                'pedido': order_dispute,
                'comprador': user_comprador,
                'vendedor': user_vendedor1,
                'motivo': 'Atraso crítico na entrega e pacote sem atualização',
                'descricao': 'O prazo limite de entrega de 8 dias úteis expirou e o rastreio informa que o produto está retido em posto fiscal sem prazo de liberação. Preciso do produto para meu trabalho ou do estorno imediato dos valores.',
                'status': 'em_analise',
                'sla_limite': timezone.now() + datetime.timedelta(hours=38),
            }
        )

        DisputeMessage.objects.get_or_create(
            disputa=dispute,
            papel='comprador',
            defaults={
                'autor': user_comprador,
                'mensagem': 'O prazo prometido no ato da compra venceu há 2 dias. Solicito providências do Suporte de Vendas da AVaD.',
                'criado_em': timezone.now() - datetime.timedelta(hours=10),
            }
        )

        DisputeMessage.objects.get_or_create(
            disputa=dispute,
            papel='vendedor',
            defaults={
                'autor': user_vendedor1,
                'mensagem': 'Prezada Marina e equipe AVaD, despachamos o pedido dentro de 24h. A retenção ocorreu por vistoria padrão da Sefaz. Já apresentamos a nota fiscal eletrônica Danfe 88291 para liberação prioritária.',
                'criado_em': timezone.now() - datetime.timedelta(hours=6),
            }
        )

        self.stdout.write(self.style.SUCCESS('Seed data concluído com sucesso no SQLite!'))
