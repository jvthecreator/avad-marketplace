// Painel do vendedor: o seletor de período troca os indicadores, o gráfico e os mais vendidos
// sem recarregar a página. Um único componente desenha em várias partes da página (portais).
import { useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api';
import { dinheiro, pct } from '../format';
import SalesChart from './SalesChart';

const SLOTS = ['dash-periodo', 'dash-kpis', 'dash-grafico', 'dash-mais-vendidos', 'dash-melhor-momento'];

function Variacao({ comparacao, textos, pctValor, diff, unidade = '' }) {
  if (!comparacao) return <div className="kpi-badge" style={{ color: 'var(--text-muted)' }}>Todo o histórico da loja</div>;
  if (diff !== undefined) {
    if (diff > 0) return <div className="kpi-badge positive">↑ +{diff}{unidade} {textos.comparacao}</div>;
    if (diff < 0) return <div className="kpi-badge negative">↓ {diff}{unidade} {textos.comparacao}</div>;
    return <div className="kpi-badge" style={{ color: 'var(--text-muted)' }}>= igual {textos.comparacao}</div>;
  }
  if (pctValor === null || pctValor === undefined) return <div className="kpi-badge" style={{ color: 'var(--text-muted)' }}>Sem vendas no período anterior</div>;
  if (pctValor > 0) return <div className="kpi-badge positive">↑ +{pct(pctValor)}% {textos.comparacao}</div>;
  if (pctValor < 0) return <div className="kpi-badge negative">↓ {pct(pctValor)}% {textos.comparacao}</div>;
  return <div className="kpi-badge" style={{ color: 'var(--text-muted)' }}>= 0% {textos.comparacao}</div>;
}

export default function SellerDashboard({ inicial }) {
  const [dados, setDados] = useState(inicial);
  const [carregando, setCarregando] = useState(false);
  const [slots] = useState(() => Object.fromEntries(SLOTS.map((id) => {
    const el = document.getElementById(id);
    if (el) el.replaceChildren();
    return [id, el];
  })));

  const trocarPeriodo = (periodo) => {
    setCarregando(true);
    const url = new URL(window.location.href);
    url.searchParams.set('periodo', periodo);
    window.history.replaceState(null, '', url);
    api('/api/vendedor/estatisticas/?periodo=' + periodo)
      .then(setDados)
      .catch(() => {})
      .finally(() => setCarregando(false));
  };

  const { kpi, comparacao: c, textos, grafico } = dados;
  const portal = (id, conteudo) => (slots[id] ? createPortal(conteudo, slots[id]) : null);

  return (
    <>
      {portal('dash-periodo', (
        <select className="form-select" style={{ width: 'auto', padding: '8px 14px', fontSize: 13 }}
          value={dados.periodo} onChange={(e) => trocarPeriodo(e.target.value)} aria-label="Período das estatísticas">
          {dados.periodos.map((p) => <option key={p.valor} value={p.valor}>{p.nome}</option>)}
        </select>
      ))}

      {portal('dash-kpis', (
        <div className={carregando ? 'is-loading' : ''}>
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <div className="kpi-card">
              <div className="kpi-title">{textos.vendas}</div>
              <div className="kpi-val">{dinheiro(kpi.bruto)}</div>
              <Variacao comparacao={c} textos={textos} pctValor={c && c.bruto} />
            </div>
            <div className="kpi-card">
              <div className="kpi-title">Receita líquida</div>
              <div className="kpi-val" style={{ color: '#059669' }}>{dinheiro(kpi.liquido)}</div>
              <div className="kpi-badge" style={{ color: 'var(--text-muted)' }}>
                {kpi.pct_liquido !== null ? `${pct(kpi.pct_liquido)}% do valor vendido, após o split` : 'Sem vendas no período'}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-title">Pedidos</div>
              <div className="kpi-val">{kpi.pedidos}</div>
              <Variacao comparacao={c} textos={textos} diff={c ? c.pedidos_diff : undefined} />
            </div>
            <div className="kpi-card">
              <div className="kpi-title">Unidades vendidas</div>
              <div className="kpi-val">{kpi.unidades}</div>
              <Variacao comparacao={c} textos={textos} diff={c ? c.unidades_diff : undefined} />
            </div>
            <div className="kpi-card">
              <div className="kpi-title">Ticket médio</div>
              <div className="kpi-val">{dinheiro(kpi.ticket_medio)}</div>
              <Variacao comparacao={c} textos={textos} pctValor={c && c.ticket_medio} />
            </div>
          </div>
          {c && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', margin: '-14px 0 24px' }}>
              Período: <strong>{dados.periodo_label}</strong>. As comparações usam o mesmo trecho do período anterior até este momento. A semana vai de domingo a sábado.
            </div>
          )}
        </div>
      ))}

      {portal('dash-grafico', (
        <>
          <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
            <div>
              <h3 className="card-title">Evolução das vendas</h3>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{grafico.subtitulo} · passe o mouse para ver os valores</div>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 3, background: '#10B981', display: 'inline-block' }} /> {grafico.legenda_atual}
              </span>
              {grafico.legenda_anterior && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 12, height: 0, borderTop: '2px dashed #94A3B8', display: 'inline-block' }} /> {grafico.legenda_anterior}
                </span>
              )}
            </div>
          </div>
          <div className={carregando ? 'is-loading' : ''}><SalesChart grafico={grafico} /></div>
        </>
      ))}

      {portal('dash-mais-vendidos', (
        <>
          <div className="card-header">
            <h3 className="card-title">Mais vendidos ({dados.periodo_label.toLowerCase()})</h3>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Top 5</span>
          </div>
          {dados.mais_vendidos.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {dados.mais_vendidos.map((item, i) => (
                <div key={item.produto_id} className="top-item">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ width: 20, fontWeight: 700, color: 'var(--text-muted)' }}>#{i + 1}</span>
                    <strong className="top-item-title">{item.titulo}</strong>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div><strong>{item.quantidade} un.</strong></div>
                    <div style={{ fontSize: 11, color: '#10B981' }}>{dinheiro(item.valor)}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 24 }}>Nenhuma venda registrada neste período.</div>
          )}
        </>
      ))}

      {portal('dash-melhor-momento', (
        <>
          <span style={{ color: 'var(--text-muted)' }}>
            {(dados.melhor_momento && dados.melhor_momento.rotulo) || 'Melhor dia de vendas'} ({dados.periodo_label.toLowerCase()}):
          </span>
          <strong>{(dados.melhor_momento && dados.melhor_momento.valor) || '—'}</strong>
        </>
      ))}
    </>
  );
}
