// Cliente da API REST do AVaD (/api/...). Usa a sessão do site; em POST/PATCH/DELETE manda o token CSRF.

function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content) return meta.content;
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

export class ApiError extends Error {
  constructor(status, dados) {
    super((dados && dados.erro) || `Erro ${status}`);
    this.status = status;
    this.dados = dados || {};
  }
}

export async function api(url, { method = 'GET', json, form } = {}) {
  const opcoes = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (method !== 'GET') opcoes.headers['X-CSRFToken'] = csrfToken();
  if (json !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(json);
  } else if (form !== undefined) {
    opcoes.body = form; // FormData (multipart): o navegador define o Content-Type
  }
  const resp = await fetch(url, opcoes);
  let dados = null;
  try { dados = await resp.json(); } catch (e) { dados = null; }
  if (!resp.ok) throw new ApiError(resp.status, dados);
  return dados;
}
