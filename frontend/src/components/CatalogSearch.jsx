// Catálogo com busca ao vivo: os resultados mudam enquanto a pessoa digita ou mexe nos filtros,
// sem recarregar a página. A URL acompanha os filtros, então o link pode ser compartilhado.
import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { dinheiro } from '../format';

const ESPERA_DIGITACAO_MS = 300;

function lerFiltrosDaUrl() {
  const p = new URLSearchParams(window.location.search);
  return {
    q: p.get('q') || '',
    categoria: p.get('categoria') || '',
    preco_min: p.get('preco_min') || '',
    preco_max: p.get('preco_max') || '',
    sort: p.get('sort') || 'relevancia',
    page: Number(p.get('page') || 1),
  };
}

function paraQuery(f) {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => {
    if (v === '' || v === null || (k === 'sort' && v === 'relevancia') || (k === 'page' && v === 1)) return;
    p.set(k, v);
  });
  const s = p.toString();
  return s ? '?' + s : '';
}

function CartaoProduto({ p }) {
  return (
    <div className="product-card">
      <div className="product-img-wrap">
        <span className={'badge product-badge-float ' + (p.frete_gratis ? 'badge-success' : 'badge-info')}>
          {p.frete_gratis ? 'FRETE GRÁTIS' : 'NOVO'}
        </span>
        {p.imagem
          ? <img src={p.imagem} alt={p.titulo} className="product-img" loading="lazy" />
          : <div className="product-img-empty">Sem imagem</div>}
      </div>
      <div className="product-info">
        <div className="product-seller">
          Por <a href={p.vendedor.url} style={{ textDecoration: 'underline' }}>{p.vendedor.nome}</a>
        </div>
        <h3 className="product-title"><a href={p.url}>{p.titulo}</a></h3>
        <div className="product-rating">
          <span>★ {p.nota_media.toLocaleString('pt-BR')}</span>
          <span style={{ color: 'var(--text-muted)' }}> ({p.total_avaliacoes})</span>
        </div>
        <div className="product-price">{dinheiro(p.preco)}</div>
        {p.parcelas && <div className="product-installments">{p.parcelas}</div>}
        <a href={p.url} className="btn btn-outline btn-block" style={{ marginTop: 8 }}>Ver anúncio</a>
      </div>
    </div>
  );
}

export default function CatalogSearch({ inicial }) {
  const [filtros, setFiltros] = useState(lerFiltrosDaUrl);
  const [dados, setDados] = useState(inicial);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const primeira = useRef(true);
  const pedidoAtual = useRef(0);

  const mudar = (campo, valor) => setFiltros((f) => ({ ...f, [campo]: valor, page: campo === 'page' ? valor : 1 }));

  // A barra de busca do topo do site passa a alimentar a busca ao vivo nesta página.
  useEffect(() => {
    const form = document.querySelector('.search-form');
    const input = form && form.querySelector('input[name="q"]');
    if (!input) return undefined;
    const aoDigitar = () => mudar('q', input.value);
    const aoEnviar = (e) => e.preventDefault();
    input.addEventListener('input', aoDigitar);
    form.addEventListener('submit', aoEnviar);
    return () => { input.removeEventListener('input', aoDigitar); form.removeEventListener('submit', aoEnviar); };
  }, []);

  useEffect(() => {
    if (primeira.current) { primeira.current = false; return undefined; }
    const query = paraQuery(filtros);
    window.history.replaceState(null, '', window.location.pathname + query);
    const id = ++pedidoAtual.current;
    setCarregando(true);
    const t = setTimeout(() => {
      api('/api/produtos/' + query)
        .then((d) => { if (id === pedidoAtual.current) { setDados(d); setErro(''); } })
        .catch(() => { if (id === pedidoAtual.current) setErro('Não foi possível buscar agora. Tente de novo.'); })
        .finally(() => { if (id === pedidoAtual.current) setCarregando(false); });
    }, ESPERA_DIGITACAO_MS);
    return () => clearTimeout(t);
  }, [filtros]);

  const temFiltro = filtros.q || filtros.categoria || filtros.preco_min || filtros.preco_max;
  const limpar = () => {
    const input = document.querySelector('.search-form input[name="q"]');
    if (input) input.value = '';
    setFiltros({ q: '', categoria: '', preco_min: '', preco_max: '', sort: 'relevancia', page: 1 });
  };

  return (
    <div className="catalog-layout">
      <aside>
        <div className="card">
          <h3 className="filter-title">Filtros</h3>

          <label className="filter-label" htmlFor="busca-ao-vivo">Buscar</label>
          <input
            id="busca-ao-vivo"
            type="search"
            className="form-input"
            placeholder="Nome, marca ou serviço"
            value={filtros.q}
            onChange={(e) => {
              mudar('q', e.target.value);
              const topo = document.querySelector('.search-form input[name="q"]');
              if (topo) topo.value = e.target.value;
            }}
            style={{ marginBottom: 20 }}
          />

          <div className="filter-label">Categorias</div>
          <div className="filter-cats">
            <button type="button" className={'filter-cat' + (filtros.categoria === '' ? ' active' : '')} onClick={() => mudar('categoria', '')}>
              Todas as categorias
            </button>
            {dados.categorias.map((c) => (
              <button
                type="button"
                key={c.valor}
                className={'filter-cat' + (filtros.categoria === c.valor ? ' active' : '')}
                onClick={() => mudar('categoria', c.valor)}
                aria-pressed={filtros.categoria === c.valor}
              >
                {c.nome}
              </button>
            ))}
          </div>

          <div className="filter-label">Faixa de preço (R$)</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input type="number" min="0" className="form-input filter-price" placeholder="Mín" aria-label="Preço mínimo"
              value={filtros.preco_min} onChange={(e) => mudar('preco_min', e.target.value)} />
            <input type="number" min="0" className="form-input filter-price" placeholder="Máx" aria-label="Preço máximo"
              value={filtros.preco_max} onChange={(e) => mudar('preco_max', e.target.value)} />
          </div>

          {temFiltro && <button type="button" className="btn btn-outline btn-sm btn-block" onClick={limpar}>Limpar filtros</button>}
        </div>
      </aside>

      <div>
        <div className="catalog-toolbar">
          <div style={{ fontSize: 14, color: 'var(--text-muted)' }} aria-live="polite">
            {carregando
              ? <span className="live-dot">Buscando…</span>
              : <>Mostrando <strong>{dados.total}</strong> resultado{dados.total === 1 ? '' : 's'}{filtros.q && <> para “<em>{filtros.q}</em>”</>}</>}
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            Ordenar por:
            <select className="form-select" style={{ padding: '6px 12px', fontSize: 13 }} value={filtros.sort}
              onChange={(e) => mudar('sort', e.target.value)}>
              <option value="relevancia">Relevância</option>
              <option value="menor_preco">Menor preço</option>
              <option value="maior_preco">Maior preço</option>
            </select>
          </label>
        </div>

        {erro && <div className="alert alert-error" style={{ marginBottom: 16 }}>{erro}</div>}

        <div className={'product-grid' + (carregando ? ' is-loading' : '')}>
          {dados.resultados.map((p) => <CartaoProduto key={p.id} p={p} />)}
          {dados.resultados.length === 0 && (
            <div style={{ gridColumn: '1 / -1', padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}>
              Nenhum anúncio encontrado para estes critérios.
            </div>
          )}
        </div>

        {dados.paginas > 1 && (
          <div className="pagination">
            {dados.pagina > 1 && <button type="button" className="btn btn-outline btn-sm" onClick={() => mudar('page', dados.pagina - 1)}>&larr; Anterior</button>}
            {Array.from({ length: dados.paginas }, (_, i) => i + 1).map((n) => (
              <button type="button" key={n} className={'btn btn-sm ' + (n === dados.pagina ? 'btn-primary' : 'btn-outline')}
                onClick={() => mudar('page', n)} aria-current={n === dados.pagina ? 'page' : undefined}>{n}</button>
            ))}
            {dados.pagina < dados.paginas && <button type="button" className="btn btn-outline btn-sm" onClick={() => mudar('page', dados.pagina + 1)}>Próxima &rarr;</button>}
          </div>
        )}
      </div>
    </div>
  );
}
