// Gráfico de evolução das vendas em SVG. Passar o mouse (ou o dedo) mostra os valores do ponto.
// Linha: período atual (verde) x anterior (cinza tracejado). Sem série anterior: barras por ano.
import { useEffect, useRef, useState } from 'react';
import { dinheiro, dinheiroCurto } from '../format';

const ALTURA = 260;
const M = { esq: 74, dir: 16, topo: 22, base: 30 };

function passoRedondo(alvo) {
  const exp = Math.pow(10, Math.floor(Math.log10(alvo)));
  const f = alvo / exp;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * exp;
}

export default function SalesChart({ grafico }) {
  const caixa = useRef(null);
  const [largura, setLargura] = useState(640);
  const [foco, setFoco] = useState(null);

  useEffect(() => {
    if (!caixa.current) return undefined;
    const ro = new ResizeObserver(([e]) => setLargura(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(caixa.current);
    return () => ro.disconnect();
  }, []);

  const { labels, atual, anterior } = grafico;
  const barras = !anterior;
  const n = labels.length;
  const w = largura - M.esq - M.dir;
  const h = ALTURA - M.topo - M.base;

  const valores = [...atual, ...(anterior || [])].filter((v) => v !== null && v !== undefined);
  const max = Math.max(0, ...valores);
  const passo = max > 0 ? passoRedondo(max / 4) : 25;
  const linhas = max > 0 ? Math.max(1, Math.ceil(max / passo - 1e-9)) : 4;
  const topo = passo * linhas;

  const faixa = w / Math.max(n, 1);
  const x = (i) => (barras ? M.esq + faixa * (i + 0.5) : M.esq + (n > 1 ? (w / (n - 1)) * i : w / 2));
  const y = (v) => M.topo + h - (v / topo) * h;

  const caminho = (serie) => {
    let d = '';
    let aberto = false;
    serie.forEach((v, i) => {
      if (v === null || v === undefined) { aberto = false; return; }
      d += `${aberto ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      aberto = true;
    });
    return d;
  };

  const cadaRotulo = Math.ceil(n / Math.max(2, Math.floor(w / 44)));

  const aoMover = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - r.left;
    const i = barras ? Math.floor((px - M.esq) / faixa) : Math.round(((px - M.esq) / w) * (n - 1));
    setFoco(i >= 0 && i < n ? i : null);
  };

  const fmt = (v) => (v === null || v === undefined ? '—' : dinheiro(v));
  const descricao = `Gráfico: ${grafico.subtitulo}.`;

  return (
    <div ref={caixa} className="sales-chart" style={{ position: 'relative', height: ALTURA }}>
      <svg width={largura} height={ALTURA} role="img" aria-label={descricao}
        onMouseMove={aoMover} onMouseLeave={() => setFoco(null)} onTouchStart={(e) => aoMover(e.touches[0] ? { currentTarget: e.currentTarget, clientX: e.touches[0].clientX } : e)}>
        {Array.from({ length: linhas + 1 }, (_, k) => {
          const v = passo * (linhas - k);
          return (
            <g key={k}>
              <line x1={M.esq} x2={largura - M.dir} y1={y(v)} y2={y(v)} stroke="#E5E7EB" />
              <text x={M.esq - 10} y={y(v) + 4} textAnchor="end" fontSize="11" fill="#9CA3AF">{dinheiroCurto(v)}</text>
            </g>
          );
        })}
        {labels.map((l, i) => (i % cadaRotulo === 0 || i === n - 1) && (
          <text key={l + i} x={x(i)} y={ALTURA - 10} textAnchor="middle" fontSize="11" fill="#9CA3AF">{l}</text>
        ))}

        {foco !== null && !barras && <line x1={x(foco)} x2={x(foco)} y1={M.topo} y2={M.topo + h} stroke="#CBD5E1" strokeDasharray="3 3" />}

        {barras ? atual.map((v, i) => v !== null && (
          <g key={i}>
            <rect x={x(i) - Math.min(56, faixa * 0.6) / 2} y={y(v)} width={Math.min(56, faixa * 0.6)} height={M.topo + h - y(v)}
              rx="4" fill={foco === i ? '#059669' : '#10B981'} />
            <text x={x(i)} y={y(v) - 6} textAnchor="middle" fontSize="11" fontWeight="600" fill="#374151">{dinheiroCurto(v)}</text>
          </g>
        )) : (
          <>
            {anterior && <path d={caminho(anterior)} fill="none" stroke="#94A3B8" strokeWidth="2.5" strokeDasharray="5 5" />}
            <path d={caminho(atual)} fill="none" stroke="#10B981" strokeWidth="2.5" />
            {[[anterior, '#94A3B8'], [atual, '#10B981']].map(([serie, cor]) => serie && serie.map((v, i) => v !== null && (n <= 31) && (
              <circle key={cor + i} cx={x(i)} cy={y(v)} r={foco === i ? 5 : n > 20 ? 2.5 : 3.5} fill={cor} stroke="#fff" strokeWidth="1.5" />
            )))}
          </>
        )}
      </svg>

      {foco !== null && (
        <div className="chart-tooltip" style={{ left: Math.min(Math.max(x(foco) - 80, 0), largura - 170), top: 0 }}>
          <div className="chart-tooltip-title">{labels[foco]}</div>
          <div><span className="dot dot-atual" />{grafico.legenda_atual}: <strong>{fmt(atual[foco])}</strong></div>
          {anterior && <div><span className="dot dot-anterior" />{grafico.legenda_anterior}: <strong>{fmt(anterior[foco])}</strong></div>}
        </div>
      )}
    </div>
  );
}
