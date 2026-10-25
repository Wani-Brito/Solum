import React, { useState } from 'react';
import { Pressable } from 'react-native';
import { api } from '../api';
import { Aviso, Btn, Card, Chip, Estado, Field, Link, Opcoes, Row, Screen, Seg, Small, Title, Top, Txt, Vazio, useCarga, useTheme } from '../ui';
import { brl, dataBr, hojeBr, isoDeBr, valorDe } from '../util';

const FILTROS = { Todas: null, Pendentes: 'PENDENTE', Atrasadas: 'ATRASADA', Pagas: 'PAGA' };

export function Faturas({ go, back }) {
  const [filtro, setFiltro] = useState('Todas');
  const carga = useCarga(() => Promise.all([api('/faturas'), api('/clientes')]));
  const [erro, setErro] = useState(null);
  const agir = async (caminho, corpo) => { try { await api(caminho, { method: 'PATCH', corpo }); carga.recarregar(); } catch (e) { setErro(e.message); } };
  return (
    <Screen>
      <Top left={<Title>Faturas</Title>} right={<Chip tone="g" onPress={() => go('nova-fatura')}>+ Nova</Chip>} />
      <Seg items={Object.keys(FILTROS)} onChange={setFiltro} />
      <Estado carga={carga}>{([faturas, clientes]) => {
        const nome = Object.fromEntries(clientes.map((c) => [c.id_cliente, c]));
        const lista = faturas.filter((f) => !FILTROS[filtro] || f.status === FILTROS[filtro]);
        const total = lista.reduce((s, f) => s + Number(f.valor), 0);
        return (
          <>
            <Card sand><Row><Small>{lista.length} fatura(s)</Small><Txt bold>{brl(total)}</Txt></Row></Card>
            {lista.length === 0 ? <Card><Vazio>Nenhuma fatura aqui. Toque em “+ Nova”.</Vazio></Card> : lista.map((f) => (
              <Card key={f.id_fatura}>
                <Row><Txt bold>{f.descricao}</Txt><Chip tone={f.status === 'PAGA' ? 'g' : f.status === 'ATRASADA' ? 't' : undefined}>{f.status === 'PAGA' ? 'Paga' : f.status === 'ATRASADA' ? 'Atrasada' : 'Pendente'}</Chip></Row>
                <Small>{nome[f.id_cliente] ? nome[f.id_cliente].nome : 'Cliente'}{nome[f.id_cliente] && nome[f.id_cliente].bloqueado ? ' · bloqueado' : ''} · vence {dataBr(f.data_vencimento)}</Small>
                <Row style={{ marginTop: 6 }}><Txt bold>{brl(f.valor)}</Txt>
                  <Row>{f.nota_obrigatoria && !f.nota_emitida ? <Chip tone="t" onPress={() => agir(`/faturas/${f.id_fatura}/nota`)}>Emitir NF</Chip> : f.nota_emitida ? <Chip>NF emitida</Chip> : null}
                    {f.status !== 'PAGA' ? <Chip tone="g" onPress={() => agir(`/faturas/${f.id_fatura}/pagar`, {})}>Marcar paga</Chip> : null}</Row></Row>
              </Card>
            ))}
            <Aviso>{erro}</Aviso>
          </>
        );
      }}</Estado>
    </Screen>
  );
}

export function NovaFatura({ back }) {
  const carga = useCarga(() => api('/clientes'));
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Nova fatura</Txt>} right={<Pressable><Small> </Small></Pressable>} />
      <Estado carga={carga}>{(clientes) => <Form clientes={clientes} back={back} recarregar={carga.recarregar} />}</Estado>
    </Screen>
  );
}

function Form({ clientes, back, recarregar }) {
  const { c } = useTheme();
  const [cli, setCli] = useState(clientes[0] ? clientes[0].id_cliente : null);
  const [f, setF] = useState({ descricao: '', valor: '', emissao: hojeBr(), venc: '' });
  const [nota, setNota] = useState(false);
  const [novo, setNovo] = useState({ aberto: false, nome: '', tipo: 'PF' });
  const [erro, setErro] = useState(null);
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const criarCliente = async () => {
    setErro(null);
    try { const r = await api('/clientes', { method: 'POST', corpo: { nome: novo.nome.trim(), tipo_pessoa: novo.tipo } }); setNovo({ aberto: false, nome: '', tipo: 'PF' }); setCli(r.id_cliente); recarregar(); }
    catch (e) { setErro(e.message); }
  };
  const salvar = async () => {
    setErro(null);
    const valor = valorDe(f.valor), emissao = isoDeBr(f.emissao), venc = isoDeBr(f.venc);
    if (!cli) return setErro('Escolha ou cadastre um cliente.');
    if (!(valor > 0)) return setErro('O valor deve ser maior que zero.');
    if (!emissao || !venc) return setErro('Informe emissão e vencimento no formato dd/mm/aaaa.');
    try { await api('/faturas', { method: 'POST', corpo: { id_cliente: cli, descricao: f.descricao.trim() || 'Serviço', valor, data_emissao: emissao, data_vencimento: venc, nota_solicitada: nota } }); back(); }
    catch (e) { setErro(e.message); }
  };
  return (
    <>
      {clientes.length ? <Opcoes rotulo="Cliente" itens={clientes.map((x) => ({ id: x.id_cliente, rotulo: `${x.nome} (${x.tipo_pessoa})${x.bloqueado ? ' 🔒' : ''}` }))} valor={cli} onChange={setCli} /> : <Small style={{ marginBottom: 8 }}>Nenhum cliente ainda. Cadastre o primeiro abaixo.</Small>}
      {novo.aberto ? (
        <Card><Field label="Nome do cliente" value={novo.nome} onChangeText={(v) => setNovo({ ...novo, nome: v })} />
          <Opcoes rotulo="Tipo" itens={[{ id: 'PF', rotulo: 'Pessoa física' }, { id: 'PJ', rotulo: 'Pessoa jurídica (NF obrigatória)' }]} valor={novo.tipo} onChange={(v) => setNovo({ ...novo, tipo: v })} />
          <Btn onPress={criarCliente}>Salvar cliente</Btn></Card>
      ) : <Link onPress={() => setNovo({ ...novo, aberto: true })} color={c.sage}>+ Novo cliente</Link>}
      <Field label="Descrição" value={f.descricao} onChangeText={set('descricao')} placeholder="Ex.: Projeto site" />
      <Field label="Valor" value={f.valor} onChangeText={set('valor')} placeholder="R$ 0,00" keyboardType="decimal-pad" />
      <Field label="Emissão" value={f.emissao} onChangeText={set('emissao')} placeholder="dd/mm/aaaa" />
      <Field label="Vencimento" value={f.venc} onChangeText={set('venc')} placeholder="dd/mm/aaaa" />
      <Card sand><Link onPress={() => setNota(!nota)} color={c.ink}>{nota ? '☑' : '☐'} O cliente pediu nota fiscal (para pessoa física)</Link></Card>
      <Aviso>{erro}</Aviso>
      <Btn onPress={salvar}>Criar fatura</Btn>
    </>
  );
}

export function Notificacoes({ back }) {
  const carga = useCarga(async () => { await api('/notificacoes/gerar', { method: 'POST' }); return api('/notificacoes'); });
  const [lidas, setLidas] = useState({});
  const marcar = async (n) => { try { await api(`/notificacoes/${n.id_notificacao}/lida`, { method: 'PATCH' }); setLidas({ ...lidas, [n.id_notificacao]: true }); } catch (e) { /* ignora */ } };
  const icone = { DAS: '🧾', DASN_SIMEI: '📄', SALDO_BAIXO: '💸', TETO: '📈', FATURA_ATRASADA: '⏰' };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Notificações</Txt>} right={<Pressable><Small> </Small></Pressable>} />
      <Estado carga={carga}>{(lista) => lista.length === 0 ? <Card><Vazio>Tudo em dia! Nenhuma notificação.</Vazio></Card> : (
        <Card>{lista.map((n, i) => {
          const lida = n.lida || lidas[n.id_notificacao];
          return (
            <Pressable key={n.id_notificacao} onPress={() => marcar(n)} style={{ paddingVertical: 9, borderBottomWidth: i === lista.length - 1 ? 0 : 1, borderBottomColor: 'rgba(128,128,128,0.25)', opacity: lida ? 0.55 : 1 }}>
              <Txt>{icone[n.tipo] || '🔔'} {n.mensagem}</Txt>
              <Small>{dataBr(n.data_criacao)}{lida ? ' · lida' : ' · toque para marcar como lida'}</Small>
            </Pressable>
          );
        })}</Card>
      )}</Estado>
    </Screen>
  );
}
