import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { api } from '../api';
import { Aviso, Avatar, Bar, Btn, Card, Chip, Estado, Field, Link, List, Opcoes, Row, Screen, Seg, Small, Title, Top, Txt, Vazio, useCarga, useTheme } from '../ui';
import { brl, pct, valorDe } from '../util';

export function Mais({ go, sair, usuario }) {
  const { c } = useTheme();
  return (
    <Screen>
      <Top left={<Title>Mais</Title>} />
      <Card>
        <Row style={{ gap: 12 }}>
          <Avatar size={46} nome={usuario.nome} />
          <View style={{ flex: 1 }}><Txt bold>{usuario.nome}</Txt><Small>{usuario.email}</Small></View>
          <Chip tone="g">{usuario.perfil === 'NORMAL' ? 'Normal' : usuario.perfil === 'PREMIUM' ? 'Premium' : 'Admin'}</Chip>
        </Row>
      </Card>
      <Card>
        <List items={[
          { title: 'Editar perfil', right: '›', onPress: () => go('perfil') },
          { title: 'Dados do MEI', right: '›', onPress: () => go('mei') },
          { title: 'Preferências', right: '›', onPress: () => go('prefs') },
          { title: 'Contas e categorias', right: '›', onPress: () => go('contas') },
          { title: 'Faturas e clientes', right: '›', onPress: () => go('faturas') },
          { title: 'Notificações', right: '›', onPress: () => go('notificacoes') },
          { title: 'Metas financeiras', right: '›', onPress: () => go('metas') },
          { title: 'Precificação', right: '›', onPress: () => go('precificacao') },
          { title: 'Lançar por mensagem', right: '›', onPress: () => go('chatbot') },
          { title: 'Investimentos (Premium)', right: '›', onPress: () => go('invest') },
        ]} />
      </Card>
      <Btn outline color={c.terra} onPress={sair}>Sair</Btn>
    </Screen>
  );
}

export function Perfil({ back, usuario, atualizarUsuario }) {
  const { c } = useTheme();
  const [f, setF] = useState({ nome: usuario.nome, telefone: usuario.telefone || '' });
  const [s, setS] = useState({ atual: '', nova: '' });
  const [m1, setM1] = useState(null);
  const [m2, setM2] = useState(null);
  const salvar = async () => {
    setM1(null);
    try { const u = await api('/usuarios/me', { method: 'PUT', corpo: { nome: f.nome.trim(), telefone: f.telefone || null } }); atualizarUsuario({ ...usuario, ...u }); back(); } catch (e) { setM1(e.message); }
  };
  const trocar = async () => {
    setM2(null);
    try { await api('/usuarios/me/senha', { method: 'PUT', corpo: { senha_atual: s.atual, nova_senha: s.nova } }); setS({ atual: '', nova: '' }); setM2({ ok: 'Senha alterada.' }); } catch (e) { setM2({ erro: e.message }); }
  };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Cancelar</Link>} title={<Txt bold>Editar perfil</Txt>} right={<Link onPress={salvar} color={c.sage} bold>Salvar</Link>} />
      <View style={{ alignItems: 'center', marginTop: 6, marginBottom: 12 }}><Avatar size={64} nome={usuario.nome} /></View>
      <Field label="Nome" value={f.nome} onChangeText={(v) => setF({ ...f, nome: v })} />
      <Field label="E-mail" value={usuario.email} editable={false} />
      <Field label="Telefone" value={f.telefone} onChangeText={(v) => setF({ ...f, telefone: v })} keyboardType="phone-pad" />
      <Aviso>{m1}</Aviso>
      <Card style={{ marginTop: 12 }}>
        <Txt bold>Segurança</Txt>
        <View style={{ marginTop: 8 }}>
          <Field label="Senha atual" value={s.atual} onChangeText={(v) => setS({ ...s, atual: v })} secure />
          <Field label="Nova senha (mín. 6)" value={s.nova} onChangeText={(v) => setS({ ...s, nova: v })} secure />
        </View>
        <Btn outline onPress={trocar}>Alterar senha</Btn>
        <Aviso tipo={m2 && m2.ok ? 'ok' : 'erro'}>{m2 && (m2.ok || m2.erro)}</Aviso>
      </Card>
    </Screen>
  );
}

const TEMAS = ['Claro', 'Escuro', 'Sistema'];
export function Prefs({ back }) {
  const { mode, setMode } = useTheme();
  const carga = useCarga(() => api('/usuarios/me/preferencias'));
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Preferências</Txt>} right={<View style={{ width: 40 }} />} />
      <Estado carga={carga}>{(p) => <FormPrefs p={p} mode={mode} setMode={setMode} back={back} />}</Estado>
    </Screen>
  );
}

function FormPrefs({ p, mode, setMode, back }) {
  const [f, setF] = useState({ ...p, saldo_minimo: String(p.saldo_minimo), percentual_alerta: Number(p.percentual_alerta) });
  const [erro, setErro] = useState(null);
  const alt = (k) => setF({ ...f, [k]: !f[k] });
  const salvar = async () => {
    setErro(null);
    try {
      await api('/usuarios/me/preferencias', { method: 'PUT', corpo: { tema: mode.toUpperCase(), notif_das: f.notif_das, notif_dasn: f.notif_dasn, notif_saldo: f.notif_saldo, notif_teto: f.notif_teto, notif_fatura: f.notif_fatura, saldo_minimo: valorDe(f.saldo_minimo), percentual_alerta: f.percentual_alerta } });
      back();
    } catch (e) { setErro(e.message); }
  };
  const itens = [['notif_das', 'Vencimento do DAS'], ['notif_dasn', 'DASN-SIMEI'], ['notif_saldo', 'Saldo baixo'], ['notif_teto', 'Proximidade do teto'], ['notif_fatura', 'Fatura atrasada']];
  return (
    <>
      <Card>
        <Txt bold>Teto do MEI</Txt>
        <Opcoes rotulo="Alertar quando chegar em" itens={[70, 80, 90].map((v) => ({ id: v, rotulo: `${v}%` }))} valor={f.percentual_alerta} onChange={(v) => setF({ ...f, percentual_alerta: v })} />
        <Bar pct={f.percentual_alerta} />
      </Card>
      <Card>
        <Txt bold>Notificações</Txt>
        <List items={itens.map(([k, t]) => ({ title: t, chip: f[k] ? 'Ligado' : 'Desligado', tone: f[k] ? 'g' : undefined, onPress: () => alt(k) }))} />
        <Field label="Avisar quando o saldo ficar abaixo de (R$)" value={f.saldo_minimo} onChangeText={(v) => setF({ ...f, saldo_minimo: v })} keyboardType="decimal-pad" />
      </Card>
      <Card>
        <Txt bold>Aparência</Txt>
        <Seg items={TEMAS} initial={TEMAS.indexOf(mode)} onChange={setMode} style={{ marginTop: 8, marginBottom: 0 }} />
        <Small style={{ marginTop: 6 }}>O Solum abre sempre no modo escuro, a não ser que você troque aqui.</Small>
      </Card>
      <Aviso>{erro}</Aviso>
      <Btn onPress={salvar}>Salvar preferências</Btn>
    </>
  );
}

export function Contas({ back }) {
  const carga = useCarga(() => Promise.all([api('/contas'), api('/categorias')]));
  const [c, setC] = useState({ nome: '', banco: '', saldo: '0' });
  const [k, setK] = useState({ nome: '', tipo: 'SAIDA' });
  const [erro, setErro] = useState(null);
  const addConta = async () => { setErro(null); try { await api('/contas', { method: 'POST', corpo: { nome: c.nome.trim(), banco: c.banco || null, saldo: valorDe(c.saldo) || 0 } }); setC({ nome: '', banco: '', saldo: '0' }); carga.recarregar(); } catch (e) { setErro(e.message); } };
  const addCat = async () => { setErro(null); try { await api('/categorias', { method: 'POST', corpo: { nome: k.nome.trim(), tipo: k.tipo } }); setK({ ...k, nome: '' }); carga.recarregar(); } catch (e) { setErro(e.message); } };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Contas e categorias</Txt>} right={<View style={{ width: 40 }} />} />
      <Estado carga={carga}>{([contas, cats]) => (
        <>
          <Card>
            <Txt bold>Contas</Txt>
            {contas.length ? <List items={contas.map((x) => ({ title: x.nome, sub: x.banco || '', right: brl(x.saldo) }))} /> : <Vazio>Nenhuma conta ainda.</Vazio>}
            <Field label="Nome da conta" value={c.nome} onChangeText={(v) => setC({ ...c, nome: v })} placeholder="Ex.: Nubank" />
            <Field label="Banco (opcional)" value={c.banco} onChangeText={(v) => setC({ ...c, banco: v })} />
            <Field label="Saldo inicial (R$)" value={c.saldo} onChangeText={(v) => setC({ ...c, saldo: v })} keyboardType="decimal-pad" />
            <Btn outline onPress={addConta}>Adicionar conta</Btn>
          </Card>
          <Card>
            <Txt bold>Categorias</Txt>
            {cats.length ? <List items={cats.map((x) => ({ title: x.nome, chip: x.tipo === 'ENTRADA' ? 'Entrada' : 'Saída', tone: x.tipo === 'ENTRADA' ? 'g' : undefined }))} /> : <Vazio>Nenhuma categoria ainda.</Vazio>}
            <Field label="Nome da categoria" value={k.nome} onChangeText={(v) => setK({ ...k, nome: v })} placeholder="Ex.: Serviços" />
            <Opcoes itens={[{ id: 'ENTRADA', rotulo: 'Entrada' }, { id: 'SAIDA', rotulo: 'Saída' }]} valor={k.tipo} onChange={(v) => setK({ ...k, tipo: v })} />
            <Btn outline onPress={addCat}>Adicionar categoria</Btn>
          </Card>
          <Aviso>{erro}</Aviso>
        </>
      )}</Estado>
    </Screen>
  );
}
