// Sininho do topo: mostra quantas notificações não foram lidas, atualiza sozinho e abre uma lista.
import { useCallback, useRef, useState } from 'react';
import { api } from '../api';
import { useAtualizacaoPeriodica, useFecharAoClicarFora } from '../hooks';

const INTERVALO_MS = 20000;

export default function NotificationBell({ inicial }) {
  const [dados, setDados] = useState(inicial);
  const [aberto, setAberto] = useState(false);
  const caixa = useRef(null);

  const atualizar = useCallback(() => api('/api/notificacoes/').then(setDados).catch(() => {}), []);
  useAtualizacaoPeriodica(atualizar, INTERVALO_MS);
  const fechar = useCallback(() => setAberto(false), []);
  useFecharAoClicarFora(caixa, aberto, fechar);

  const alternar = () => {
    if (!aberto) atualizar();
    setAberto(!aberto);
  };
  const marcarTodas = () => api('/api/notificacoes/marcar-todas/', { method: 'POST' }).then(setDados).catch(() => {});

  const n = dados.nao_lidas;
  return (
    <div className="notif-bell" ref={caixa}>
      <button
        type="button"
        className="nav-link cart-link notif-bell-btn"
        onClick={alternar}
        aria-haspopup="true"
        aria-expanded={aberto}
        aria-label={n ? `Notificações: ${n} não lida${n > 1 ? 's' : ''}` : 'Notificações'}
        title="Notificações"
      >
        🔔{n > 0 && <span className="cart-badge notif-badge">{n > 9 ? '9+' : n}</span>}
      </button>

      {aberto && (
        <div className="notif-dropdown" role="menu">
          <div className="notif-dropdown-head">
            <strong>Notificações</strong>
            {n > 0 && <button type="button" className="link-btn" onClick={marcarTodas}>Marcar todas como lidas</button>}
          </div>
          {dados.notificacoes.length === 0 ? (
            <div className="notif-empty">Nenhuma notificação por enquanto.</div>
          ) : (
            <ul className="notif-list">
              {dados.notificacoes.map((item) => (
                <li key={item.id}>
                  <a href={item.abrir_url} className={'notif-item' + (item.lida ? '' : ' unread')} role="menuitem">
                    {!item.lida && <span className="notif-dot" aria-label="não lida" />}
                    <span className="notif-title">{item.titulo}</span>
                    <span className="notif-msg">{item.mensagem}</span>
                    <span className="notif-time">{item.quando}</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
          <a href={dados.ver_todas_url} className="notif-all">Ver todas as notificações</a>
        </div>
      )}
    </div>
  );
}
