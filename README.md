# AVaD — Assurance, Value and Dealing Marketplace

Sistema completo de marketplace com garantia de valor, custódia preventiva (*escrow*), split automático de pagamentos, rastreamento logístico integrado e câmara arbitral para mediação de conflitos.

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Django](https://img.shields.io/badge/Django-6.1-green.svg)
![Database](https://img.shields.io/badge/SQLite-db.sqlite3-orange.svg)
![Frontend](https://img.shields.io/badge/Vanilla_JS-HTML5_CSS3-yellow.svg)

---

## 🏛️ Visão Geral e Arquitetura

O **AVaD** resolve a desconfiança em transações eletrônicas através de um ecossistema seguro:
1. **Comprador**: Catálogo completo, cálculo de frete por CEP, compra protegida, acompanhamento em 5 estados, confirmação de recebimento, avaliação em 2 blocos (vendedor e transportadora), solicitação de reembolso e abertura de disputas.
2. **Vendedor**: Cadastro de anúncios (produtos e serviços), gestão do ciclo de pedidos, visualização do split com alerta de retenção em custódia (*escrow*), desbloqueio de conta bancária e Dashboard analítico com KPIs e gráfico Canvas.
3. **Suporte de Vendas (Mediador)**: Painel operacional consolidado em 3 colunas com auditoria de dados, histórico em abas (mensagens, logística, financeiro, evidências), rastreio e emissão de decisão arbitral vinculante.
4. **Simulador Bancário Integrado**: Simulação de gateway de pagamento com cenários de **Aprovação**, **Transação Negada** e **Timeout (> 40s)**.
5. **Simulador Logístico Integrado**: Cálculo em tempo real para `PAC` e `SEDEX`, geração de etiquetas de rastreio (`BRXXXXXXXXXAV`) e timeline de movimentações.

---

## 👤 Contas de Demonstração Pré-Cadastradas (`seed_data`)

| Ator | E-mail | Senha | Destaques |
| :--- | :--- | :--- | :--- |
| **Comprador** | `marina@avad.com` | `senha1234` | Compras realizadas, rastreio em andamento e cartão salvo. |
| **Vendedor 1 (Oficial)** | `felipe@lojadech.com` | `senha1234` | Loja *Tech Store Oficial* (CNPJ ativo, conta regularizada, produtos e vendas). |
| **Vendedor 2 (Escrow Retido)** | `loja2@avad.com` | `senha1234` | Loja *Casa & Conforto Mobiliário* com conta bancária bloqueada para teste do split retido em *escrow*. |
| **Mediador (Suporte)** | `mediador@avad.com` | `senha1234` | Acesso ao Painel de Mediação com o caso **`#PRO007`** em análise. |

---

## 📋 Casos de Uso Implementados (`PRO001` a `PRO012`)

- **`PRO001`**: Cadastro de usuário com validação de campos obrigatórios em negrito, maioridade (>18), unicidade e simulação de ativação por e-mail.
- **`PRO002`**: Login multi-perfil (Comprador, Vendedor, Mediador) com fluxos alternativos e links diretos para e-mail não registrado e senha incorreta.
- **`PRO003`**: Redefinição de senha com validação de 8 caracteres mínimos e confirmação por e-mail.
- **`PRO004`**: Cadastro e publicação de novos anúncios com validação de imagem e aceite de T&Cs.
- **`PRO005`**: Catálogo com busca e filtros, página do produto com frete dinâmico e checkout em 3 etapas com seletor de simulação de gateway bancário.
- **`PRO006`**: Split de pagamentos automático (6,5% AVaD, frete para transportadora e líquido para o vendedor) e retenção em custódia (*escrow*), além de exportação de extrato em CSV.
- **`PRO007`**: Abertura de disputa, bloqueio de repasse ao vendedor, câmara arbitral em 3 colunas e emissão de decisão final pelo mediador.
- **`PRO008`**: Stepper horizontal de 5 estados e timeline vertical para rastreamento de entregas, com avanço de status pelo vendedor.
- **`PRO009`**: Modal de confirmação de recebimento e avaliação dupla interativa de 0 a 5 estrelas.
- **`PRO010`**: Solicitação de reembolso com protocolo `REE-2026-XXXXX` e stepper vertical de estorno.
- **`PRO011`**: Perfil público do vendedor com selos, nota média, distribuição de estrelas 5★ a 1★ e avaliações com selo de compra verificada.
- **`PRO012`**: Dashboard do vendedor com layout `#142621`, 5 KPIs comparativos, gráfico de linha mensal em Canvas, mais vendidos e insights rápidos.

---

## 🚀 Como Executar Localmente

```bash
# 1. Clone o repositório
git clone https://github.com/jvthecreator/avad-marketplace.git
cd avad-marketplace

# 2. Crie e ative um ambiente virtual (opcional)
python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Aplique as migrações e popule o banco de dados
python manage.py migrate
python manage.py seed_data

# 5. Inicie o servidor de desenvolvimento
python manage.py runserver
```

Acesse em seu navegador: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## ☁️ Hospedagem na Nuvem (Render / Railway / Fly)

O projeto já inclui:
- `Procfile` configurado para execução com `gunicorn`.
- `render.yaml` pronto para deploy com build automático (`migrate`, `collectstatic`, `seed_data`).
- `whitenoise` configurado para servir arquivos estáticos em produção.