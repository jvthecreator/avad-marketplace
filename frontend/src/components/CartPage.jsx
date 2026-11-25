// Carrinho: muda quantidades e remove itens na hora, com o total sempre atualizado.
import { useState } from 'react';
import { api } from '../api';
import { dinheiro } from '../format';

function atualizarIconeDoTopo(unidades) {
  const link = document.querySelector('a.cart-link[aria-label="Carrinho"]');
  if (!link) return;
  let badge = link.querySelector('.cart-badge');
  if (!unidades) { if (badge) badge.remove(); return; }
  if (!badge) { badge = document.createElement('span'); badge.className = 'cart-badge'; link.appendChild(badge); }
  badge.textContent = unidades;
}

export default function CartPage({ inicial }) {
  const [dados, setDados] = useState(inicial);
  const [ocupado, setOcupado] = useState(null); // produto_id sendo alterado
  const [aviso, setAviso] = useState('');

  const aplicar = (promessa, produtoId) => {
    setOcupado(produtoId);
    promessa
      .then((d) => { setDados(d); setAviso(d.aviso || ''); atualizarIconeDoTopo(d.unidades); })
      .catch((e) => setAviso(e.message))
      .finally(() => setOcupado(null));
  };
  const mudarQtd = (item, qtd) => aplicar(api(`/api/carrinho/${item.produto_id}/`, { method: 'PATCH', json: { quantidade: qtd } }), item.produto_id);
  const remover = (item) => aplicar(api(`/api/carrinho/${item.produto_id}/`, { method: 'DELETE' }), item.produto_id);

  if (!dados.itens.length) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '48px 16px' }}>
        <div style={{ fontSize: 40, marginBottom: 8 }}>🛒</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>Seu carrinho está vazio</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>Explore o catálogo e adicione produtos.</p>
        <a href="/catalog/" className="btn btn-primary">Ver catálogo</a>
      </div>
    );
  }

  return (
    <>
      {aviso && <div className="alert alert-warning" style={{ marginBottom: 16 }} role="status">{aviso}</div>}
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ flex: '1 1 560px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {dados.itens.map((item) => (
            <div key={item.produto_id} className={'card cart-item' + (ocupado === item.produto_id ? ' is-loading' : '')}>
              <div className="cart-thumb">
                {item.imagem ? <img src={item.imagem} alt={item.titulo} /> : <span>Sem foto</span>}
              </div>
              <div style={{ flex: '1 1 200px', minWidth: 160 }}>
                <a href={item.url} style={{ fontWeight: 600, fontSize: 14 }}>{item.titulo}</a>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>{dinheiro(item.preco)} cada</div>
                {item.disponivel
                  ? <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Estoque: {item.estoque} unid.</div>
                  : <div style={{ fontSize: 12, color: '#B91C1C', fontWeight: 600 }}>Produto esgotado</div>}
              </div>

              {item.disponivel && (
                <>
                  <div className="qty-stepper" aria-label={`Quantidade de ${item.titulo}`}>
                    <button type="button" onClick={() => mudarQtd(item, item.quantidade - 1)} disabled={ocupado !== null}
                      aria-label={item.quantidade === 1 ? 'Remover item' : 'Diminuir quantidade'}>−</button>
                    <input type="number" min="1" max={item.estoque} value={item.quantidade} aria-label="Quantidade"
                      onChange={(e) => { const v = parseInt(e.target.value, 10); if (v >= 1) mudarQtd(item, v); }} />
                    <button type="button" onClick={() => mudarQtd(item, item.quantidade + 1)}
                      disabled={ocupado !== null || item.quantidade >= item.estoque} aria-label="Aumentar quantidade">+</button>
                  </div>
                  <div style={{ minWidth: 110, textAlign: 'right' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Subtotal</div>
                    <strong>{dinheiro(item.subtotal)}</strong>
                  </div>
                </>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {item.disponivel && <a href={item.comprar_url} className="btn btn-primary btn-sm">Comprar</a>}
                <button type="button" className="btn btn-outline btn-sm btn-block" onClick={() => remover(item)} disabled={ocupado !== null}>Remover</button>
              </div>
            </div>
          ))}
        </div>

        <div className="card" style={{ flex: '0 0 320px' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Resumo</h2>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
            <span>Unidades</span><strong>{dados.unidades}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
            <span>Subtotal</span><strong aria-live="polite">{dinheiro(dados.subtotal)}</strong>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '12px 0' }}>
            O frete é calculado na finalização. Use “Finalizar compra” para pagar todos os itens de uma vez ou “Comprar” para pagar só um deles.
          </p>
          <a href="/catalog/" className="btn btn-outline btn-block">Continuar comprando</a>
          {dados.subtotal > 0 && <a href={dados.finalizar_url} className="btn btn-primary btn-block" style={{ marginTop: 10 }}>Finalizar compra</a>}
        </div>
      </div>
    </>
  );
}
