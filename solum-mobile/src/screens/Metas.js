import React, { useState } from 'react';
import { Pressable } from 'react-native';
import { api } from '../api';
import { Aviso, Bar, Btn, Card, Chip, Estado, Field, Link, Row, Screen, Small, Title, Top, Txt, Vazio, useCarga } from '../ui';
import { brl, dataBr, isoDeBr, valorDe } from '../util';

export function Metas({ go }) {
  const carga = useCarga(() => api('/metas'));
  return (
    <Screen>
      <Top left={<Title>Metas</Title>} right={<Chip tone="g" onPress={() => go('nova-meta')}>+ Nova</Chip>} />
      <Estado carga={carga}>{(metas) => metas.length === 0 ? <Card><Vazio>Você ainda não tem metas. Toque em “+ Nova”.</Vazio></Card> : metas.map((m) => {
        const p = Math.min(100, (Number(m.valor_atual) / Number(m.valor_objetivo)) * 100);
        return (
          <Card key={m.id_meta}>
            <Row><Txt bold>{m.nome}</Txt><Chip tone={m.status === 'ATIVA' ? 'g' : undefined}>{m.status === 'ATIVA' ? 'Ativa' : m.status === 'CONCLUIDA' ? 'Concluída' : 'Cancelada'}</Chip></Row>
            <Small>Prazo: {dataBr(m.prazo)}</Small>
            <Bar pct={p} />
            <Row><Small>{brl(m.valor_atual)} de {brl(m.valor_objetivo)}</Small><Small>{Math.round(p)}%</Small></Row>
            {m.status === 'ATIVA' ? <Btn outline onPress={() => go('aporte', { meta: m })}>Aportar</Btn> : null}
          </Card>
        );
      })}</Estado>
    </Screen>
  );
}

export function NovaMeta({ back }) {
  const [f, setF] = useState({ nome: '', objetivo: '', prazo: '' });
  const [erro, setErro] = useState(null);
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const salvar = async () => {
    setErro(null);
    const objetivo = valorDe(f.objetivo), prazo = isoDeBr(f.prazo);
    if (!f.nome.trim()) return setErro('Dê um nome para a meta.');
    if (!(objetivo > 0)) return setErro('O valor objetivo deve ser maior que zero.');
    if (!prazo) return setErro('Informe o prazo no formato dd/mm/aaaa.');
    try { await api('/metas', { method: 'POST', corpo: { nome: f.nome.trim(), valor_objetivo: objetivo, prazo } }); back(); } catch (e) { setErro(e.message); }
  };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Nova meta</Txt>} right={<Pressable><Small> </Small></Pressable>} />
      <Field label="Nome" value={f.nome} onChangeText={set('nome')} placeholder="Ex.: Notebook novo" />
      <Field label="Valor objetivo (R$)" value={f.objetivo} onChangeText={set('objetivo')} placeholder="6.000,00" keyboardType="decimal-pad" />
      <Field label="Prazo" value={f.prazo} onChangeText={set('prazo')} placeholder="dd/mm/aaaa" />
      <Aviso>{erro}</Aviso>
      <Btn onPress={salvar}>Criar meta</Btn>
    </Screen>
  );
}

export function Aporte({ back, params }) {
  const m = params.meta;
  const [valor, setValor] = useState('');
  const [erro, setErro] = useState(null);
  const salvar = async () => {
    setErro(null);
    const v = valorDe(valor);
    if (!(v > 0)) return setErro('O aporte deve ser maior que zero.');
    try { await api(`/metas/${m.id_meta}/aporte`, { method: 'POST', corpo: { valor: v } }); back(); } catch (e) { setErro(e.message); }
  };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Aportar</Txt>} right={<Pressable><Small> </Small></Pressable>} />
      <Card><Txt bold>{m.nome}</Txt><Small>{brl(m.valor_atual)} de {brl(m.valor_objetivo)}</Small></Card>
      <Field label="Valor do aporte (R$)" value={valor} onChangeText={setValor} placeholder="0,00" big keyboardType="decimal-pad" />
      <Aviso>{erro}</Aviso>
      <Btn onPress={salvar}>Confirmar aporte</Btn>
    </Screen>
  );
}
