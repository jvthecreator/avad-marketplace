import { useEffect, useRef } from 'react';

// Chama fn a cada `ms` milissegundos enquanto a aba está visível, e também ao voltar para a aba.
export function useAtualizacaoPeriodica(fn, ms, ativo = true) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!ativo) return undefined;
    const tick = () => { if (document.visibilityState === 'visible') ref.current(); };
    const id = setInterval(tick, ms);
    document.addEventListener('visibilitychange', tick);
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', tick); };
  }, [ms, ativo]);
}

// Fecha um menu ao clicar fora dele ou apertar Esc.
export function useFecharAoClicarFora(ref, aberto, fechar) {
  useEffect(() => {
    if (!aberto) return undefined;
    const clique = (e) => { if (ref.current && !ref.current.contains(e.target)) fechar(); };
    const tecla = (e) => { if (e.key === 'Escape') fechar(); };
    document.addEventListener('mousedown', clique);
    document.addEventListener('keydown', tecla);
    return () => { document.removeEventListener('mousedown', clique); document.removeEventListener('keydown', tecla); };
  }, [aberto, fechar, ref]);
}
