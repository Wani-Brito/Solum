import { useState } from 'react'
import { api } from './api'
import { Barras, Estado, brl, dataBr, dataHora, mesCurto, num, pct, useCarga } from './util'

const Chip = ({ tom, children }) => <span className={`chip ${tom || ''}`}>{children}</span>

/* ------------------------------------------------------------- Controle administrativo */
export function Dashboard() {
  const carga = useCarga(() => api('/admin/dashboard'))
  return (
    <>
      <h2>Controle administrativo</h2>
      <p className="sub">Visão geral do sistema</p>
      <Estado carga={carga}>
        {(d) => (
          <>
            <div className="kpis">
              <div className="card kpi h"><small>Usuários</small><b>{num(d.usuarios)}</b></div>
              <div className="card kpi"><small>Novos no mês</small><b>{num(d.novos_no_mes)}</b></div>
              <div className="card kpi"><small>Transações no mês</small><b>{num(d.transacoes_no_mes)}</b></div>
              <div className="card kpi"><small>Perto do teto (80% ou mais)</small><b style={{ color: 'var(--terra)' }}>{num(d.perto_do_teto)}</b></div>
              <div className="card kpi"><small>Obrigações em atraso</small><b style={{ color: 'var(--terra)' }}>{num(d.obrigacoes_em_atraso)}</b></div>
            </div>
            <div className="two">
              <div className="card"><b>Cadastros por mês</b>
                <Barras itens={d.cadastros_por_mes.map((x, i, a) => ({ valor: x.total, rotulo: mesCurto(x.mes), destaque: i === a.length - 1 }))} />
              </div>
              <div className="card"><b>Perfis</b>
                {Object.entries(d.perfis).map(([p, n]) => <div className="row" key={p}><span>{p[0] + p.slice(1).toLowerCase()}</span><span>{n}</span></div>)}
              </div>
            </div>
            <div className="two">
              <div className="card"><b>Volume lançado por mês</b><small style={{ display: 'block', color: 'var(--mut)' }}>Soma das transações</small>
                <Barras itens={d.volume_por_mes.map((x) => ({ valor: x.total, rotulo: mesCurto(x.mes) }))} />
              </div>
              <div className="card"><b>Saúde do sistema</b>
                <div className="row"><span>API</span><Chip tom="g">{d.saude.api === 'online' ? 'Online' : d.saude.api}</Chip></div>
                <div className="row"><span>Versão</span><Chip>{d.saude.versao}</Chip></div>
                <div className="row"><span>Última verificação</span><Chip>{dataHora(d.saude.verificado_em)}</Chip></div>
              </div>
            </div>
            <div className="card wr"><b>Usuários que pedem atenção</b>
              {d.atencao.length === 0 ? <div className="vazio">Nenhum usuário pede atenção agora.</div> : (
                <table><tbody>
                  <tr><th>Usuário</th><th>Motivo</th><th>Detalhe</th></tr>
                  {d.atencao.map((a, i) => <tr key={i}><td>{a.usuario}</td><td><Chip tom={a.motivo === 'Reserva zerada' ? '' : 't'}>{a.motivo}</Chip></td><td>{a.detalhe}</td></tr>)}
                </tbody></table>
              )}
            </div>
            <div className="two">
              <div className="card"><b>Pendências administrativas</b>
                {d.pendencias.map((p, i) => (
                  <div className="row" key={i}><span>{p.texto}</span>
                    {p.nivel === 'ATENCAO' ? <Chip tom="t">Atenção</Chip> : p.quantidade !== undefined ? <Chip>{p.quantidade}</Chip> : <Chip tom="g">{dataBr(p.data)}</Chip>}
                  </div>
                ))}
              </div>
              <div className="card"><b>Atividade recente</b>
                {d.atividade_recente.length === 0 ? <div className="vazio">Sem atividade ainda.</div> :
                  d.atividade_recente.map((a, i) => <div className="row" key={i}><span>{a.acao}</span><small>{dataHora(a.data_hora)}</small></div>)}
              </div>
            </div>
          </>
        )}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Usuários */
export function Usuarios({ euId }) {
  const [busca, setBusca] = useState('')
  const [perfil, setPerfil] = useState('')
  const [novo, setNovo] = useState(false)
  const [form, setForm] = useState({ nome: '', email: '', senha: '', perfil: 'NORMAL' })
  const [msg, setMsg] = useState(null)
  const carga = useCarga(() => api(`/admin/usuarios?busca=${encodeURIComponent(busca)}&perfil=${perfil}`), [busca, perfil])

  const alterar = async (id, corpo) => {
    setMsg(null)
    try { await api(`/admin/usuarios/${id}`, { method: 'PATCH', corpo }); carga.recarregar() } catch (e) { setMsg({ erro: e.message }) }
  }
  const criar = async (ev) => {
    ev.preventDefault(); setMsg(null)
    try {
      await api('/admin/usuarios', { method: 'POST', corpo: form })
      setForm({ nome: '', email: '', senha: '', perfil: 'NORMAL' }); setNovo(false); setMsg({ ok: 'Usuário criado.' }); carga.recarregar()
    } catch (e) { setMsg({ erro: e.message }) }
  }
  return (
    <>
      <h2>Usuários</h2><p className="sub">Gestão de contas cadastradas</p>
      <div className="tools">
        <input placeholder="Buscar por nome ou e-mail" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <select value={perfil} onChange={(e) => setPerfil(e.target.value)}>
          <option value="">Todos os perfis</option><option value="NORMAL">Normal</option><option value="PREMIUM">Premium</option><option value="ADMIN">Admin</option>
        </select>
        <button className="btn" onClick={() => setNovo(!novo)}>{novo ? 'Cancelar' : '+ Novo usuário'}</button>
      </div>
      {msg?.erro && <div className="erro">{msg.erro}</div>}{msg?.ok && <div className="ok">{msg.ok}</div>}
      {novo && (
        <form className="card form" onSubmit={criar}>
          <label className="f"><small>Nome</small><input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label className="f"><small>E-mail</small><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label className="f"><small>Senha (mín. 6)</small><input required type="password" minLength={6} value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} /></label>
          <label className="f"><small>Perfil</small>
            <select value={form.perfil} onChange={(e) => setForm({ ...form, perfil: e.target.value })}><option value="NORMAL">Normal</option><option value="PREMIUM">Premium</option><option value="ADMIN">Admin</option></select></label>
          <div style={{ alignSelf: 'end' }}><button className="btn" type="submit">Criar usuário</button></div>
        </form>
      )}
      <Estado carga={carga}>
        {(lista) => (
          <div className="card wr">
            {lista.length === 0 ? <div className="vazio">Nenhum usuário encontrado.</div> : (
              <table><tbody>
                <tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Cadastro</th><th>Status</th></tr>
                {lista.map((u) => (
                  <tr key={u.id_usuario}>
                    <td>{u.nome}</td><td>{u.email}</td>
                    <td><select style={{ width: 'auto' }} value={u.perfil} disabled={u.id_usuario === euId} onChange={(e) => alterar(u.id_usuario, { perfil: e.target.value })}>
                      <option value="NORMAL">Normal</option><option value="PREMIUM">Premium</option><option value="ADMIN">Admin</option></select></td>
                    <td>{dataBr(u.data_cadastro)}</td>
                    <td>{u.id_usuario === euId ? <Chip tom="g">Você</Chip> : <button className={`btn s ${u.ativo ? 'o' : ''}`} onClick={() => alterar(u.id_usuario, { ativo: !u.ativo })}>{u.ativo ? 'Desativar' : 'Reativar'}</button>}</td>
                  </tr>
                ))}
              </tbody></table>
            )}
          </div>
        )}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Vendas (plano Premium) */
export function Vendas() {
  const carga = useCarga(() => api('/admin/vendas'))
  const [msg, setMsg] = useState(null)
  const cobrar = async () => {
    try { const r = await api('/admin/assinaturas/cobrar', { method: 'POST' }); setMsg({ ok: `Cobrança simulada: ${r.pagamentos_criados} pagamento(s) gerado(s).` }); carga.recarregar() } catch (e) { setMsg({ erro: e.message }) }
  }
  const tom = { ATIVA: 'g', CANCELADA: 't', PENDENTE: '' }
  return (
    <>
      <h2>Vendas</h2><p className="sub">Vendas do plano Premium · pagamentos simulados</p>
      <Estado carga={carga}>
        {(v) => {
          const f = v.funil, topo = Math.max(f.cadastrados, 1)
          return (
            <>
              <div className="kpis">
                <div className="card kpi h"><small>Receita do mês</small><b>{brl(v.receita_mes)}</b></div>
                <div className="card kpi"><small>Assinantes Premium</small><b>{v.assinantes_premium}</b></div>
                <div className="card kpi"><small>Conversão Normal para Premium</small><b>{pct(v.conversao_percentual)}</b></div>
                <div className="card kpi"><small>Cancelamentos no mês</small><b style={{ color: 'var(--terra)' }}>{v.cancelamentos_mes}</b></div>
              </div>
              <div className="two">
                <div className="card"><b>Receita por mês</b><small style={{ display: 'block', color: 'var(--mut)' }}>R$</small>
                  <Barras itens={v.receita_por_mes.map((x, i, a) => ({ valor: x.total, rotulo: mesCurto(x.mes), destaque: i === a.length - 1 }))} /></div>
                <div className="card"><b>Funil de conversão</b>
                  {[['Cadastrados', f.cadastrados], ['Cadastraram o MEI', f.cadastraram_mei], ['Usaram o app no mês', f.usaram_no_mes], ['Assinaram o Premium', f.assinaram_premium]].map(([t, n], i) => (
                    <div key={t} style={{ marginTop: 10 }}>
                      <div className="row" style={{ border: 0, padding: '2px 0' }}><small>{t}</small><small>{n}</small></div>
                      <div className="bar"><b style={{ width: `${(n / topo) * 100}%`, ...(i === 3 ? { background: 'var(--terra)' } : {}) }} /></div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card wr"><b>Últimas assinaturas</b>
                {v.ultimas_assinaturas.length === 0 ? <div className="vazio">Nenhuma assinatura ainda.</div> : (
                  <table><tbody>
                    <tr><th>Usuário</th><th>Plano</th><th>Valor</th><th>Início</th><th>Status</th></tr>
                    {v.ultimas_assinaturas.map((a, i) => <tr key={i}><td>{a.usuario}</td><td>{a.plano}</td><td>{brl(a.valor)}</td><td>{dataBr(a.data)}</td><td><Chip tom={tom[a.status]}>{a.status[0] + a.status.slice(1).toLowerCase()}</Chip></td></tr>)}
                  </tbody></table>
                )}
              </div>
              {msg?.erro && <div className="erro">{msg.erro}</div>}{msg?.ok && <div className="ok">{msg.ok}</div>}
              <button className="btn o" onClick={cobrar}>Rodar cobrança mensal simulada</button>
              <div className="note" style={{ marginTop: 14 }}>Os pagamentos são simulados (não há cobrança real). Valores vêm das tabelas planos, assinaturas e pagamentos.</div>
            </>
          )
        }}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Tabela DAS */
const CAMPOS_DAS = [['salario_minimo', 'Salário mínimo (R$)'], ['perc_inss', 'INSS padrão (%)'], ['perc_inss_caminhoneiro', 'INSS caminhoneiro (%)'], ['valor_icms', 'ICMS (R$)'], ['valor_iss', 'ISS (R$)'], ['teto_anual', 'Teto anual (R$)'], ['teto_caminhoneiro', 'Teto caminhoneiro (R$)']]

export function TabelaDAS() {
  const carga = useCarga(() => api('/admin/tabela-das'))
  const [ano, setAno] = useState(null)
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState(null)

  const escolher = (tabelas, a) => {
    setAno(a); setMsg(null)
    const t = tabelas.find((x) => x.ano === a)
    setForm(t ? { ...Object.fromEntries(CAMPOS_DAS.map(([k]) => [k, String(t[k])])), fonte: t.fonte } : { ...Object.fromEntries(CAMPOS_DAS.map(([k]) => [k, ''])), fonte: '' })
  }
  const salvar = async (ev) => {
    ev.preventDefault(); setMsg(null)
    try {
      await api(`/admin/tabela-das/${ano}`, { method: 'PUT', corpo: { ...Object.fromEntries(CAMPOS_DAS.map(([k]) => [k, form[k]])), fonte: form.fonte } })
      setMsg({ ok: `Tabela DAS ${ano} salva.` }); carga.recarregar()
    } catch (e) { setMsg({ erro: e.message }) }
  }
  return (
    <>
      <h2>Tabela DAS</h2><p className="sub">Valores por atividade e esfera · fonte da verdade do imposto</p>
      <Estado carga={carga}>
        {(tabelas) => {
          const atual = tabelas.find((t) => t.ano === ano) || tabelas[0]
          if (ano === null && atual) setTimeout(() => escolher(tabelas, atual.ano), 0)
          const inss = (t, cam) => (Number(t.salario_minimo) * Number(cam ? t.perc_inss_caminhoneiro : t.perc_inss)) / 100
          const linhas = atual ? [['Comércio / indústria', false, 'c'], ['Serviço', false, 's'], ['Comércio e serviço', false, 'a'], ['Caminhoneiro (comércio)', true, 'c'], ['Caminhoneiro (serviço)', true, 's']].map(([nome, cam, tp]) => {
            const icms = tp !== 's' ? Number(atual.valor_icms) : 0, iss = tp !== 'c' ? Number(atual.valor_iss) : 0
            return [nome, inss(atual, cam), icms, iss, inss(atual, cam) + icms + iss]
          }) : []
          return (
            <>
              <div className="tools">
                <select value={ano ?? ''} onChange={(e) => escolher(tabelas, Number(e.target.value))}>
                  {tabelas.map((t) => <option key={t.ano} value={t.ano}>Ano: {t.ano}</option>)}
                  {ano && !tabelas.find((t) => t.ano === ano) && <option value={ano}>Ano: {ano} (novo)</option>}
                </select>
                <button className="btn" onClick={() => { const n = Math.max(...tabelas.map((t) => t.ano)) + 1; escolher(tabelas, n) }}>+ Nova vigência</button>
              </div>
              {atual && tabelas.find((t) => t.ano === atual.ano) && (
                <div className="card wr"><table><tbody>
                  <tr><th>Atividade</th><th>INSS (federal)</th><th>ICMS (estadual)</th><th>ISS (municipal)</th><th>Total DAS</th></tr>
                  {linhas.map((l) => <tr key={l[0]}><td>{l[0]}</td><td>{brl(l[1])}</td><td>{l[2] ? brl(l[2]) : '—'}</td><td>{l[3] ? brl(l[3]) : '—'}</td><td><b>{brl(l[4])}</b></td></tr>)}
                </tbody></table></div>
              )}
              {form && (
                <form className="card" onSubmit={salvar}>
                  <b>Vigência {ano}</b>
                  <div className="form" style={{ marginTop: 10 }}>
                    {CAMPOS_DAS.map(([k, rot]) => <label className="f" key={k}><small>{rot}</small><input required type="number" step="0.01" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></label>)}
                    <label className="f" style={{ gridColumn: '1 / -1' }}><small>Fonte documentada</small><input required value={form.fonte} onChange={(e) => setForm({ ...form, fonte: e.target.value })} /></label>
                  </div>
                  {msg?.erro && <div className="erro">{msg.erro}</div>}{msg?.ok && <div className="ok">{msg.ok}</div>}
                  <button className="btn" type="submit" style={{ marginTop: 10 }}>Salvar tabela</button>
                  {atual && <div className="legenda">Última atualização: {dataHora(atual.data_atualizacao)}</div>}
                </form>
              )}
              <div className="note">Confira os valores no Portal do Empreendedor antes de cadastrar cada ano. Os cálculos do app leem esta tabela.</div>
            </>
          )
        }}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Configurações */
export function Configuracoes() {
  const carga = useCarga(() => api('/admin/configuracoes'))
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState(null)
  const [cnaes, setCnaes] = useState('')
  const [msgCnae, setMsgCnae] = useState(null)
  const salvar = async (ev) => {
    ev.preventDefault(); setMsg(null)
    try { await api('/admin/configuracoes', { method: 'PUT', corpo: { percentual_alerta_padrao: form.percentual_alerta_padrao, dias_aviso_das: Number(form.dias_aviso_das), dias_aviso_dasn: Number(form.dias_aviso_dasn) } }); setMsg({ ok: 'Configurações salvas.' }) } catch (e) { setMsg({ erro: e.message }) }
  }
  const importar = async () => {
    setMsgCnae(null)
    try {
      const itens = cnaes.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => { const [cnae, descricao, tipo] = l.split(';').map((x) => x.trim()); return { cnae, descricao: descricao || 'Atividade permitida ao MEI', tipo_atividade: (tipo || 'SERVICO').toUpperCase() } })
      const r = await api('/admin/cnaes', { method: 'POST', corpo: itens }); setMsgCnae({ ok: `${r.importados} CNAE(s) importado(s).` }); setCnaes('')
    } catch (e) { setMsgCnae({ erro: e.message }) }
  }
  return (
    <>
      <h2>Configurações gerais</h2><p className="sub">Parâmetros padrão do sistema</p>
      <Estado carga={carga}>
        {(c) => {
          const f = form || c
          if (!form) setTimeout(() => setForm(c), 0)
          return (
            <>
              <form className="card" onSubmit={salvar}>
                <b>Alertas e avisos</b>
                <div className="form" style={{ marginTop: 10 }}>
                  <label className="f"><small>Percentual de alerta do teto (padrão)</small><input type="number" min="1" max="100" step="1" value={f.percentual_alerta_padrao} onChange={(e) => setForm({ ...f, percentual_alerta_padrao: e.target.value })} /></label>
                  <label className="f"><small>Avisar o vencimento do DAS (dias antes)</small><input type="number" min="1" max="30" value={f.dias_aviso_das} onChange={(e) => setForm({ ...f, dias_aviso_das: e.target.value })} /></label>
                  <label className="f"><small>Avisar a DASN-SIMEI (dias antes)</small><input type="number" min="1" max="90" value={f.dias_aviso_dasn} onChange={(e) => setForm({ ...f, dias_aviso_dasn: e.target.value })} /></label>
                </div>
                {msg?.erro && <div className="erro">{msg.erro}</div>}{msg?.ok && <div className="ok">{msg.ok}</div>}
                <button className="btn" type="submit" style={{ marginTop: 10 }}>Salvar alterações</button>
              </form>
              <div className="card">
                <b>CNAEs permitidos ao MEI</b>
                <div className="legenda" style={{ marginBottom: 8 }}>Uma linha por atividade: <code>código;descrição;COMERCIO, SERVICO ou AMBOS</code>. Quando a lista existe, o cadastro do MEI só aceita CNAEs dela. Use a lista oficial do Portal do Empreendedor.</div>
                <textarea placeholder="4781400;Comércio varejista de roupas;COMERCIO" value={cnaes} onChange={(e) => setCnaes(e.target.value)} />
                {msgCnae?.erro && <div className="erro">{msgCnae.erro}</div>}{msgCnae?.ok && <div className="ok">{msgCnae.ok}</div>}
                <button className="btn o" style={{ marginTop: 10 }} onClick={importar} disabled={!cnaes.trim()}>Importar CNAEs</button>
              </div>
              <div className="note">O Solum abre sempre no modo escuro; cada usuário pode trocar nas Preferências do app.</div>
            </>
          )
        }}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Meu perfil */
export function MeuPerfil() {
  const carga = useCarga(() => api('/usuarios/me'))
  const [nome, setNome] = useState(null)
  const [tel, setTel] = useState(null)
  const [senha, setSenha] = useState({ senha_atual: '', nova_senha: '' })
  const [m1, setM1] = useState(null)
  const [m2, setM2] = useState(null)
  const salvar = async (ev, u) => {
    ev.preventDefault(); setM1(null)
    try { await api('/usuarios/me', { method: 'PUT', corpo: { nome: nome ?? u.nome, telefone: tel ?? u.telefone } }); setM1({ ok: 'Perfil atualizado.' }) } catch (e) { setM1({ erro: e.message }) }
  }
  const trocar = async (ev) => {
    ev.preventDefault(); setM2(null)
    try { await api('/usuarios/me/senha', { method: 'PUT', corpo: senha }); setSenha({ senha_atual: '', nova_senha: '' }); setM2({ ok: 'Senha alterada.' }) } catch (e) { setM2({ erro: e.message }) }
  }
  return (
    <>
      <h2>Meu perfil</h2><p className="sub">Seus dados de acesso como administrador</p>
      <Estado carga={carga}>
        {(u) => (
          <div className="two">
            <form className="card" onSubmit={(e) => salvar(e, u)}>
              <b>Dados pessoais</b>
              <div className="form" style={{ marginTop: 10 }}>
                <label className="f"><small>Nome</small><input value={nome ?? u.nome} onChange={(e) => setNome(e.target.value)} /></label>
                <label className="f"><small>E-mail</small><input value={u.email} disabled /></label>
                <label className="f"><small>Telefone</small><input value={tel ?? (u.telefone || '')} onChange={(e) => setTel(e.target.value)} /></label>
                <label className="f"><small>Perfil</small><input value={u.perfil} disabled /></label>
              </div>
              {m1?.erro && <div className="erro">{m1.erro}</div>}{m1?.ok && <div className="ok">{m1.ok}</div>}
              <button className="btn" type="submit" style={{ marginTop: 10 }}>Salvar</button>
            </form>
            <form className="card" onSubmit={trocar}>
              <b>Alterar senha</b>
              <label className="f" style={{ marginTop: 10 }}><small>Senha atual</small><input type="password" required value={senha.senha_atual} onChange={(e) => setSenha({ ...senha, senha_atual: e.target.value })} /></label>
              <label className="f" style={{ marginTop: 8 }}><small>Nova senha (mín. 6)</small><input type="password" required minLength={6} value={senha.nova_senha} onChange={(e) => setSenha({ ...senha, nova_senha: e.target.value })} /></label>
              {m2?.erro && <div className="erro">{m2.erro}</div>}{m2?.ok && <div className="ok">{m2.ok}</div>}
              <button className="btn o" type="submit" style={{ marginTop: 10 }}>Atualizar senha</button>
            </form>
          </div>
        )}
      </Estado>
    </>
  )
}

/* ------------------------------------------------------------- Login */
export function Login({ onEntrar }) {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const entrar = async (ev) => {
    ev.preventDefault(); setErro(null); setEnviando(true)
    try { await onEntrar(email, senha) } catch (e) { setErro(e.message) } finally { setEnviando(false) }
  }
  return (
    <div id="login">
      <form className="lg" onSubmit={entrar}>
        <div className="logo">SOLUM<span>.</span></div>
        <p>Painel administrativo</p>
        <label className="f"><small>E-mail</small><input type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label className="f"><small>Senha</small><input type="password" required value={senha} onChange={(e) => setSenha(e.target.value)} /></label>
        {erro && <div className="erro">{erro}</div>}
        <button className="btn" type="submit" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        <p style={{ margin: '14px 0 0', fontSize: 11 }}>Acesso restrito a administradores do Solum.</p>
      </form>
    </div>
  )
}
