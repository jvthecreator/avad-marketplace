// Rastreio do pedido: a barra de etapas e o histórico se atualizam sozinhos quando o vendedor
// avança o pedido. Desenha em três partes da página (selo, barra e histórico).
import { useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api';
import { useAtualizacaoPeriodica } from '../hooks';

const INTERVALO_MS = 15000;
const SLOTS = ['rastreio-selo', 'rastreio-etapas', 'rastreio-historico'];

function Etapas({ pedido, etapas }) {
  const atual = pedido.etapa;
  const ultima = etapas.length - 1;
  const progresso = atual <= 0 ? 0 : (Math.min(atual, ultima) / ultima) * 100;
  return (
    <div className="stepper-horizontal" role="list" aria-label="Etapas do pedido">
      <div className="stepper-track"><div className="stepper-track-fill" style={{ width: `${progresso}%` }} /></div>
      {etapas.map((nome, i) => {
        const estado = pedido.cancelado ? '' : i <= atual ? 'completed' : i === atual + 1 ? 'active' : '';
        return (
          <div key={nome} className={'stepper-step ' + estado} role="listitem" aria-current={i === atual ? 'step' : undefined}>
            <div className="step-circle">{i + 1}</div>
            <div className="step-label">{nome}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function TrackingLive({ inicial, dataset }) {
  const [dados, setDados] = useState(inicial);
  const [slots] = useState(() => Object.fromEntries(SLOTS.map((id) => {
    const el = document.getElementById(id);
    if (el) el.replaceChildren();
    return [id, el];
  })));

  const finalizado = ['entregue', 'cancelado'].includes(dados.pedido.status);
  useAtualizacaoPeriodica(
    () => api(`/api/pedidos/${dataset.pedido}/rastreio/`).then(setDados).catch(() => {}),
    INTERVALO_MS,
    !finalizado,
  );

  const portal = (id, conteudo) => (slots[id] ? createPortal(conteudo, slots[id]) : null);
  const { pedido } = dados;

  return (
    <>
      {portal('rastreio-selo', (
        <span className={`badge badge-${pedido.status_cor}`} style={{ fontSize: 13, padding: '6px 12px' }}>{pedido.status_texto}</span>
      ))}
      {portal('rastreio-etapas', <Etapas pedido={pedido} etapas={dados.etapas} />)}
      {portal('rastreio-historico', (
        <>
          <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
            <h2 className="card-title">Histórico de Rastreamento</h2>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {finalizado ? 'Atualizado pelo Parceiro Logístico AVaD' : <span className="live-dot">ao vivo</span>}
            </span>
          </div>
          <div className="timeline-vertical" style={{ marginTop: 16 }}>
            {dados.eventos.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Aguardando os primeiros eventos de transporte.</div>}
            {dados.eventos.map((e) => (
              <div key={e.id} className="timeline-item">
                <div className="timeline-bullet" />
                <div className="timeline-time">{e.data_hora_texto}{e.local && ` • ${e.local}`}</div>
                <div className="timeline-title">{e.titulo}</div>
                {e.descricao && <div className="timeline-desc">{e.descricao}</div>}
              </div>
            ))}
          </div>
        </>
      ))}
    </>
  );
}
