import { useEffect, useState } from 'react'
import { api, guardarToken, temToken } from './api'
import { Configuracoes, Dashboard, Login, MeuPerfil, TabelaDAS, Usuarios, Vendas } from './pages'

const NAV = [['dash', 'Dashboard'], ['users', 'Usuários'], ['sales', 'Vendas'], ['das', 'Tabela DAS'], ['cfg', 'Configurações'], ['me', 'Meu perfil']]

export default function App() {
  const [eu, setEu] = useState(null)
  const [tab, setTab] = useState('dash')
  const [verificando, setVerificando] = useState(temToken())

  const sair = () => { guardarToken(null); setEu(null); setTab('dash') }

  useEffect(() => {
    if (temToken()) api('/usuarios/me').then((u) => (u.perfil === 'ADMIN' ? setEu(u) : sair())).catch(sair).finally(() => setVerificando(false))
    window.addEventListener('solum-sessao-expirada', sair)
    return () => window.removeEventListener('solum-sessao-expirada', sair)
  }, [])

  const entrar = async (email, senha) => {
    const r = await api('/auth/login', { method: 'POST', corpo: { email, senha } })
    if (r.usuario.perfil !== 'ADMIN') throw new Error('Acesso restrito a administradores.')
    guardarToken(r.access_token); setEu(r.usuario)
  }

  if (verificando) return null
  if (!eu) return <Login onEntrar={entrar} />
  const pagina = { dash: <Dashboard />, users: <Usuarios euId={eu.id_usuario} />, sales: <Vendas />, das: <TabelaDAS />, cfg: <Configuracoes />, me: <MeuPerfil /> }[tab]
  return (
    <div className="app">
      <nav>
        <div className="logo">SOLUM<span>.</span></div>
        <small>Painel administrativo</small>
        {NAV.map(([k, rotulo]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => { setTab(k); window.scrollTo(0, 0) }}>{rotulo}</button>)}
        <button style={{ color: 'var(--terra)' }} onClick={sair}>Sair</button>
        <div className="me">{eu.nome}<br />{eu.email}</div>
      </nav>
      <main><section className="sec on" key={tab}>{pagina}</section></main>
    </div>
  )
}
