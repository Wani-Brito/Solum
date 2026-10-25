import { API_URL } from './config';

let token = null;
let aoExpirar = null;
export const definirToken = (t) => { token = t; };
export const aoSessaoExpirar = (fn) => { aoExpirar = fn; };

function mensagem(corpo, status) {
  const d = corpo && corpo.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length) return `${d[0].loc ? d[0].loc[d[0].loc.length - 1] : 'campo'}: ${d[0].msg}`;
  return `Erro ${status}`;
}

export async function api(caminho, { method = 'GET', corpo } = {}) {
  let resp;
  try {
    resp = await fetch(API_URL + caminho, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
  } catch (e) {
    throw new Error('Não foi possível conectar ao servidor. Confira a internet e o endereço da API.');
  }
  if (resp.status === 204) return null;
  let json = null;
  try { json = await resp.json(); } catch (e) { json = null; }
  if (!resp.ok) {
    if (resp.status === 401 && token && aoExpirar) aoExpirar();
    const erro = new Error(mensagem(json, resp.status));
    erro.status = resp.status;
    throw erro;
  }
  return json;
}
