export const brl = (v) => {
  const n = Number(v || 0);
  const [i, d] = Math.abs(n).toFixed(2).split('.');
  return `${n < 0 ? '-' : ''}R$ ${i.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${d}`;
};
export const pct = (v) => `${Number(v || 0).toFixed(1).replace('.', ',').replace(',0', '')}%`;
export const dataBr = (iso) => { if (!iso) return '—'; const [a, m, d] = String(iso).slice(0, 10).split('-'); return `${d}/${m}/${a}`; };
export const isoDeBr = (txt) => {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec((txt || '').trim());
  if (!m) return null;
  return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
};
export const hojeBr = () => { const h = new Date(); return `${String(h.getDate()).padStart(2, '0')}/${String(h.getMonth() + 1).padStart(2, '0')}/${h.getFullYear()}`; };
export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
export const mesAno = (m, a) => `${MESES[m - 1]}/${a}`;
export const valorDe = (txt) => {
  let t = String(txt || '').trim().replace(/[R$\s]/g, '');
  if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.');
  const n = Number(t);
  return Number.isFinite(n) ? n : NaN;
};
export const diasAte = (iso) => Math.round((new Date(iso + 'T00:00:00') - new Date(new Date().toDateString())) / 86400000);
