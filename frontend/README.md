# Front-end React do AVaD

Componentes React que consomem a API REST do Django (`/api/`). O site **não precisa de Node
para rodar**: o resultado já compilado fica em `static/js/avad-react.js` e é carregado pelos
templates `base.html` e `dashboard/base_seller.html`.

## Componentes

| Componente | Onde aparece | Endpoints usados |
|---|---|---|
| `NotificationBell` | sininho no topo do site | `GET /api/notificacoes/`, `POST /api/notificacoes/<id>/lida/`, `POST /api/notificacoes/marcar-todas/` |
| `CatalogSearch` | Catálogo (busca ao vivo) | `GET /api/produtos/` |
| `SellerDashboard` + `SalesChart` | Painel do vendedor › Visão geral | `GET /api/vendedor/estatisticas/?periodo=` |
| `CartPage` | Carrinho | `GET/POST /api/carrinho/`, `PATCH/DELETE /api/carrinho/<produto_id>/` |
| `DisputeChat` | Disputa (comprador/vendedor) e painel do mediador | `GET/POST /api/disputas/<id>/mensagens/` |
| `TrackingLive` | Acompanhar entrega | `GET /api/pedidos/<id>/rastreio/` |

Cada página marca onde o React entra com `data-react="<nome>"` (veja `src/main.jsx`). O HTML
que o Django já renderizou continua na página até os dados da API chegarem; se o JavaScript
falhar, a página funciona normalmente sem o React.

## Como alterar e recompilar

Requer Node.js 18 ou mais novo.

```bash
cd frontend
npm install
npm run build      # gera ../static/js/avad-react.js (minificado)
npm run watch      # recompila a cada alteração, durante o desenvolvimento
```

Depois de recompilar, faça commit do `static/js/avad-react.js` junto com o código-fonte.
