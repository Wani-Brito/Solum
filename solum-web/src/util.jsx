import { useCallback, useEffect, useState } from 'react'

export const brl = (v) => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
export const num = (v) => Number(v ?? 0).toLocaleString('pt-BR')
export const pct = (v) => `${Number(v ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
export const dataBr = (iso) => (iso ? new Date(iso).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : '—')
export const dataHora = (iso) => (iso ? new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—')
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
export const mesCurto = (m) => MESES[m - 1]

/** Carrega dados da API e mostra carregando / erro / conteúdo. */
export function useCarga(carregar, deps = []) {
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: true })
  const recarregar = useCallback(() => {
    setEstado((s) => ({ ...s, carregando: true, erro: null }))
    carregar()
      .then((dados) => setEstado({ dados, erro: null, carregando: false }))
      .catch((e) => setEstado({ dados: null, erro: e.message, carregando: false }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(recarregar, [recarregar])
  return { ...estado, recarregar }
}

export function Estado({ carga, children }) {
  if (carga.carregando && !carga.dados) return <div className="vazio">Carregando…</div>
  if (carga.erro) return <div className="erro">{carga.erro} <button className="link" onClick={carga.recarregar}>Tentar de novo</button></div>
  return children(carga.dados)
}

export function Barras({ itens, cor }) {
  const max = Math.max(...itens.map((i) => i.valor), 1)
  return (
    <div className="bars">
      {itens.map((i, k) => (
        <div key={k}>
          <i style={{ height: `${Math.max((i.valor / max) * 100, 3)}%`, ...(i.destaque ? { background: 'var(--terra)' } : cor ? { background: cor } : {}) }} />
          {i.rotulo}
        </div>
      ))}
    </div>
  )
}
