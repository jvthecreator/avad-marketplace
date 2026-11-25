// Ponto de entrada do React no AVaD.
// Cada tela marca onde o React entra com data-react="<nome>". O HTML que o Django já
// renderizou fica visível até os dados chegarem da API; se o JavaScript falhar, a página
// continua funcionando com esse HTML.
import { createRoot } from 'react-dom/client';
import { api } from './api';
import NotificationBell from './components/NotificationBell';
import CatalogSearch from './components/CatalogSearch';
import SellerDashboard from './components/SellerDashboard';
import CartPage from './components/CartPage';
import DisputeChat from './components/DisputeChat';
import TrackingLive from './components/TrackingLive';

// nome -> { componente, url dos dados iniciais (a partir dos data-* do elemento) }
const TELAS = {
  'notificacoes': { Componente: NotificationBell, url: () => '/api/notificacoes/' },
  'catalogo': { Componente: CatalogSearch, url: () => '/api/produtos/' + window.location.search },
  'painel-vendedor': {
    Componente: SellerDashboard,
    url: (el) => '/api/vendedor/estatisticas/?periodo=' + encodeURIComponent(el.dataset.periodo || 'mensal'),
  },
  'carrinho': { Componente: CartPage, url: () => '/api/carrinho/' },
  'chat-disputa': { Componente: DisputeChat, url: (el) => `/api/disputas/${el.dataset.disputa}/mensagens/` },
  'rastreio': { Componente: TrackingLive, url: (el) => `/api/pedidos/${el.dataset.pedido}/rastreio/` },
};

async function montar(el) {
  const tela = TELAS[el.dataset.react];
  if (!tela || el.dataset.reactMontado) return;
  el.dataset.reactMontado = '1';
  try {
    const inicial = await api(tela.url(el));
    // Elementos que só existem para quem está sem JavaScript (ex.: formulário antigo)
    const remover = el.dataset.reactRemove;
    if (remover) document.querySelectorAll(remover).forEach((n) => n.remove());
    el.replaceChildren();
    createRoot(el).render(<tela.Componente inicial={inicial} dataset={{ ...el.dataset }} />);
  } catch (e) {
    // Mantém o HTML do servidor (a página continua funcionando sem o React)
    console.warn('[AVaD] React não montado em', el.dataset.react, e);
  }
}

function iniciar() {
  document.querySelectorAll('[data-react]').forEach(montar);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
else iniciar();
