const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
let token = sessionStorage.getItem('solum_token')

export function guardarToken(t) {
  token = t
  if (t) sessionStorage.setItem('solum_token', t)
  else sessionStorage.removeItem('solum_token')
}
export const temToken = () => !!token

function mensagemDeErro(corpo, status) {
  const d = corpo && corpo.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) return `${d[0].loc?.slice(-1)[0] ?? 'campo'}: ${d[0].msg}`
  return `Erro ${status}`
}

export async function api(caminho, { method = 'GET', corpo } = {}) {
  let resp
  try {
    resp = await fetch(BASE + caminho, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: corpo ? JSON.stringify(corpo) : undefined,
    })
  } catch {
    throw new Error('Não foi possível conectar à API. Confira se o backend está rodando.')
  }
  if (resp.status === 204) return null
  const json = await resp.json().catch(() => null)
  if (!resp.ok) {
    if (resp.status === 401 && token) window.dispatchEvent(new Event('solum-sessao-expirada'))
    throw new Error(mensagemDeErro(json, resp.status))
  }
  return json
}
