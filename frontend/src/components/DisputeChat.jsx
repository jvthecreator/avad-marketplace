// Chat da disputa: mensagens entre comprador, vendedor e mediador aparecem sem recarregar.
// O envio aceita uma evidência (JPG, PNG ou MP4 até 10 MB), que precisa de um nome.
import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { useAtualizacaoPeriodica } from '../hooks';

const INTERVALO_MS = 8000;
const BADGE = { mediador: 'badge-primary', vendedor: 'badge-success', comprador: 'badge-secondary' };

export default function DisputeChat({ inicial, dataset }) {
  const [dados, setDados] = useState(inicial);
  const [texto, setTexto] = useState('');
  const [arquivo, setArquivo] = useState(null);
  const [nomeArquivo, setNomeArquivo] = useState('');
  const [erros, setErros] = useState({});
  const [enviando, setEnviando] = useState(false);
  const lista = useRef(null);
  const inputArquivo = useRef(null);
  const url = `/api/disputas/${dataset.disputa}/mensagens/`;
  const mediador = dados.papel === 'mediador';

  useAtualizacaoPeriodica(() => api(url).then(setDados).catch(() => {}), INTERVALO_MS);

  const total = dados.mensagens.length;
  useEffect(() => {
    if (lista.current) lista.current.scrollTop = lista.current.scrollHeight;
  }, [total]);

  const enviar = (e) => {
    e.preventDefault();
    const novos = {};
    if (!texto.trim()) novos.mensagem = ['Escreva uma mensagem.'];
    if (arquivo && !nomeArquivo.trim()) novos.nome_evidencia = ['Dê um nome para a evidência.'];
    if (!arquivo && nomeArquivo.trim()) novos.evidencia = ['Você deu um nome à evidência, mas não escolheu o arquivo.'];
    setErros(novos);
    if (Object.keys(novos).length) return;

    const form = new FormData();
    form.append('mensagem', texto);
    if (arquivo) { form.append('evidencia', arquivo); form.append('nome_evidencia', nomeArquivo); }
    setEnviando(true);
    api(url, { method: 'POST', form })
      .then((d) => {
        setDados(d); setTexto(''); setArquivo(null); setNomeArquivo(''); setErros({});
        if (inputArquivo.current) inputArquivo.current.value = '';
      })
      .catch((err) => setErros(err.dados.erros || { geral: [err.message] }))
      .finally(() => setEnviando(false));
  };

  const Erro = ({ campo }) => (erros[campo] ? <div className="field-error">{erros[campo][0]}</div> : null);

  return (
    <div className="dispute-chat">
      <div className="chat-head">
        {!mediador && <h3 className="card-title">Histórico de Mensagens e Manifestações</h3>}
        <span className="live-dot">ao vivo</span>
      </div>

      <div className="chat-list" ref={lista} aria-live="polite">
        {dados.mensagens.length === 0 && <div className="chat-empty">Nenhuma mensagem ainda.</div>}
        {dados.mensagens.map((m) => (
          <div key={m.id} className={`chat-msg chat-${m.papel}` + (m.minha ? ' mine' : '')}>
            <div className="chat-msg-head">
              <span className={'badge ' + (BADGE[m.papel] || 'badge-secondary')} style={{ fontSize: 10 }}>{m.papel_texto}</span>
              <strong>{m.autor}{m.minha && ' (você)'}</strong>
              <span className="chat-time">{m.criado_em_texto}</span>
            </div>
            <p>{m.texto}</p>
          </div>
        ))}
      </div>

      {dados.pode_enviar ? (
        <form className="chat-form" onSubmit={enviar} noValidate>
          <label className="form-label" htmlFor="chat-texto" style={mediador ? { fontWeight: 700, color: 'var(--accent-blue)' } : undefined}>
            {mediador ? 'Responder às partes como Mediador Oficial:' : 'Responder à mediação:'}
          </label>
          <textarea id="chat-texto" className="form-input" rows={3} value={texto} onChange={(e) => setTexto(e.target.value)}
            placeholder="Escreva sua mensagem..." onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) enviar(e); }} />
          <Erro campo="mensagem" />
          <div className="chat-attach">
            <div>
              <label className="form-label" style={{ fontSize: 12 }} htmlFor="chat-arquivo">📎 {mediador ? 'Anexo oficial' : 'Anexar documento/imagem'} (opcional)</label>
              <input id="chat-arquivo" ref={inputArquivo} type="file" className="form-input" accept=".jpg,.jpeg,.png,.mp4"
                onChange={(e) => setArquivo(e.target.files[0] || null)} />
              <Erro campo="evidencia" />
            </div>
            <div>
              <label className="form-label" style={{ fontSize: 12 }} htmlFor="chat-nome">Nome da evidência{arquivo && ' *'}</label>
              <input id="chat-nome" type="text" className="form-input" maxLength={100} placeholder="Ex.: Foto da caixa amassada"
                value={nomeArquivo} onChange={(e) => setNomeArquivo(e.target.value)} />
              <Erro campo="nome_evidencia" />
            </div>
          </div>
          <Erro campo="geral" />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Ctrl + Enter envia</span>
            <button type="submit" className="btn btn-primary" disabled={enviando}>
              {enviando ? 'Enviando…' : mediador ? 'Enviar Mensagem às Partes' : 'Enviar manifestação'}
            </button>
          </div>
        </form>
      ) : (
        <div className="chat-closed">Esta disputa já foi encerrada com a decisão final do Mediador.</div>
      )}
    </div>
  );
}
