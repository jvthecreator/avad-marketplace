// Formatação no padrão brasileiro.
const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const num1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const dinheiro = (v) => brl.format(v || 0); // "R$" e o número ficam sempre na mesma linha
export const pct = (v) => num1.format(v);

export function dinheiroCurto(v) {
  if (Math.abs(v) >= 1000) {
    return 'R$ ' + new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(v / 1000) + ' mil';
  }
  return 'R$ ' + new Intl.NumberFormat('pt-BR', { maximumFractionDigits: v < 10 ? 2 : 0 }).format(v);
}
