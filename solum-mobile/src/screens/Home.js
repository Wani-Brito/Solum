import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { api } from '../api';
import { Aviso, Avatar, Bar, Big, Btn, Card, Chip, Estado, Field, Link, List, MiniBars, Money, Opcoes, Row, Screen, Seg, Small, Title, Top, Txt, Vazio, useCarga, useTheme } from '../ui';
import { MESES, brl, dataBr, hojeBr, isoDeBr, mesAno, pct, valorDe } from '../util';

const hoje = () => new Date();

export function Home({ go, usuario }) {
  const carga = useCarga(() => Promise.all([api('/dashboard'), api('/notificacoes')]));
  return (
    <Screen>
      <Estado carga={carga}>{([d, notifs]) => {
        const naoLidas = notifs.filter((n) => !n.lida).length;
        const sal = d.salario_sintetico;
        const t = d.teto;
        return (
          <>
            <Top left={<View><Small>Olá, {usuario.nome.split(' ')[0]}</Small><Title>{MESES[hoje().getMonth()]}</Title></View>}
                 right={<Pressable onPress={() => go('notificacoes')} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>{naoLidas > 0 ? <Chip tone="t">🔔 {naoLidas}</Chip> : <Chip>🔔</Chip>}<Avatar nome={usuario.nome} /></Pressable>} />
            <Card hero>
              <Small color="#fff">Salário sintético deste mês</Small>
              <Big color="#fff">{brl(sal.valor != null ? sal.valor : sal.desejado)}</Big>
              <Small color="#fff">{sal.status === 'REALIZADA' ? 'Fechado' : sal.status === 'PLANEJADA' ? 'Planejado' : 'Defina na aba Salário'} · Reserva de estabilização: {brl(d.reserva_estabilizacao)}</Small>
            </Card>
            {t ? (
              <Card>
                <Row><Txt bold>Teto anual MEI</Txt><Chip tone={t.nivel === 'NORMAL' ? 'g' : 't'}>{t.nivel === 'NORMAL' ? 'Normal' : 'Atenção'} {pct(t.percentual)}</Chip></Row>
                <Bar pct={Math.min(100, t.percentual)} warn={t.nivel !== 'NORMAL'} />
                <Small>Faturado no ano: {brl(t.acumulado)} de {brl(t.teto)}</Small>
              </Card>
            ) : <Card><Small>Cadastre os dados do MEI para acompanhar o teto.</Small><Btn outline onPress={() => go('mei')}>Dados do MEI</Btn></Card>}
            <Card>
              <Row><Txt bold>Fluxo do mês</Txt><Small>saldo final {brl(d.fluxo_mes.saldo_final)}</Small></Row>
              <Row style={{ marginTop: 4 }}><Money>+ {brl(d.fluxo_mes.entradas)}</Money><Money neg>− {brl(d.fluxo_mes.saidas)}</Money></Row>
              {d.serie_resultado.length > 0 ? <MiniBars data={(() => { const max = Math.max(...d.serie_resultado.map((x) => Math.abs(x.resultado)), 1); return d.serie_resultado.map((x) => [Math.max(8, (Math.abs(x.resultado) / max) * 100), x.resultado < 0 ? 1 : 0]); })()} /> : null}
            </Card>
            <Card>
              {d.proximo_das ? (<><Row><Txt bold>Próximo DAS</Txt><Txt>{brl(d.proximo_das.valor)}</Txt></Row>
                <Small>vence {dataBr(d.proximo_das.vencimento)} · {d.proximo_das.status === 'ATRASADO' ? 'atrasado' : 'reservado ✔'}</Small></>)
                : <Small>Nenhuma obrigação de imposto pendente.</Small>}
            </Card>
          </>
        );
      }}</Estado>
    </Screen>
  );
}

export function Caixa({ go }) {
  const [ref, setRef] = useState({ ano: hoje().getFullYear(), mes: hoje().getMonth() + 1 });
  const [filtro, setFiltro] = useState('Tudo');
  const carga = useCarga(() => Promise.all([api(`/fluxo-caixa/${ref.ano}/${ref.mes}`), api(`/transacoes?ano=${ref.ano}&mes=${ref.mes}`), api('/contas'), api('/categorias')]), [ref.ano, ref.mes]);
  const mover = (d) => { let mes = ref.mes + d, ano = ref.ano; if (mes < 1) { mes = 12; ano -= 1; } if (mes > 12) { mes = 1; ano += 1; } setRef({ ano, mes }); };
  return (
    <Screen>
      <Top left={<Title>Fluxo de caixa</Title>} right={<Chip tone="g" onPress={() => go('nova')}>+ Nova</Chip>} />
      <Row style={{ marginBottom: 8 }}><Link onPress={() => mover(-1)}>‹ Anterior</Link><Txt bold>{mesAno(ref.mes, ref.ano)}</Txt><Link onPress={() => mover(1)}>Próximo ›</Link></Row>
      <Seg items={['Tudo', 'Entradas', 'Saídas']} onChange={setFiltro} />
      <Estado carga={carga}>{([fluxo, trs, contas, cats]) => {
        const conta = Object.fromEntries(contas.map((c) => [c.id_conta, c.nome]));
        const cat = Object.fromEntries(cats.map((c) => [c.id_categoria, c.nome]));
        const itens = trs.filter((t) => filtro === 'Tudo' || (filtro === 'Entradas' ? t.tipo === 'ENTRADA' : t.tipo === 'SAIDA'))
          .map((t) => ({ title: t.descricao, sub: `${cat[t.id_categoria]} · ${conta[t.id_conta]} · ${dataBr(t.data).slice(0, 5)}`, right: `${t.tipo === 'ENTRADA' ? '+' : '−'} ${brl(t.valor).replace('R$ ', '')}`, rightColor: t.tipo === 'ENTRADA' ? 'pos' : 'neg' }));
        return (
          <>
            <Card>
              <Row><Small>Saldo inicial</Small><Txt bold>{brl(fluxo.saldo_inicial)}</Txt></Row>
              <Row><Small>Entradas / Saídas</Small><Txt><Money>{brl(fluxo.total_entradas).replace('R$ ', '')}</Money> / <Money neg>{brl(fluxo.total_saidas).replace('R$ ', '')}</Money></Txt></Row>
              <Row><Small>Saldo final</Small><Txt bold>{brl(fluxo.saldo_final)}</Txt></Row>
            </Card>
            <Card>{itens.length ? <List items={itens} /> : <Vazio>Nenhuma transação neste mês. Toque em “+ Nova” ou lance por mensagem.</Vazio>}</Card>
            <View style={{ alignItems: 'center', gap: 6 }}>
              <Small>Contas: {contas.length ? contas.map((c) => c.nome).join(' · ') : 'nenhuma cadastrada'}</Small>
              <Link onPress={() => go('chatbot')}>💬 Lançar por mensagem</Link>
            </View>
          </>
        );
      }}</Estado>
    </Screen>
  );
}

export function NovaTransacao({ back, go }) {
  const carga = useCarga(() => Promise.all([api('/contas'), api('/categorias')]));
  return (
    <Screen>
      <Top left={<Title>Nova transação</Title>} right={<Pressable onPress={back}><Small>✕</Small></Pressable>} />
      <Estado carga={carga}>{([contas, cats]) => <FormTransacao contas={contas} cats={cats} back={back} go={go} />}</Estado>
    </Screen>
  );
}

function FormTransacao({ contas, cats, back, go }) {
  const [tipo, setTipo] = useState('ENTRADA');
  const [f, setF] = useState({ valor: '', descricao: '', data: hojeBr(), conta: contas[0] ? contas[0].id_conta : null, categoria: null });
  const [ligada, setLigada] = useState(true);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const { c } = useTheme();
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const doTipo = cats.filter((x) => x.tipo === tipo);
  const categoria = doTipo.find((x) => x.id_categoria === f.categoria) ? f.categoria : (doTipo[0] ? doTipo[0].id_categoria : null);
  if (!contas.length || !doTipo.length) {
    return <Card><Small>{!contas.length ? 'Cadastre uma conta antes de lançar.' : 'Cadastre uma categoria deste tipo antes de lançar.'}</Small><Btn outline onPress={() => go('contas')}>Contas e categorias</Btn></Card>;
  }
  const salvar = async () => {
    setErro(null);
    const valor = valorDe(f.valor), data = isoDeBr(f.data);
    if (!(valor > 0)) return setErro('O valor deve ser maior que zero.');
    if (!data) return setErro('Informe a data no formato dd/mm/aaaa.');
    if (!f.descricao.trim()) return setErro('Informe uma descrição.');
    setEnviando(true);
    try { await api('/transacoes', { method: 'POST', corpo: { id_conta: f.conta, id_categoria: categoria, descricao: f.descricao.trim(), valor, data, tipo, ligada_atividade: ligada } }); back(); }
    catch (e) { setErro(e.message); setEnviando(false); }
  };
  return (
    <>
      <Seg items={['Entrada', 'Saída']} onChange={(t, i) => setTipo(i === 0 ? 'ENTRADA' : 'SAIDA')} />
      <Field label="Valor" value={f.valor} onChangeText={set('valor')} placeholder="R$ 0,00" big keyboardType="decimal-pad" />
      <Field label="Descrição" value={f.descricao} onChangeText={set('descricao')} placeholder="Ex.: Projeto site" />
      <Field label="Data" value={f.data} onChangeText={set('data')} placeholder="dd/mm/aaaa" />
      <Opcoes rotulo="Conta" itens={contas.map((x) => ({ id: x.id_conta, rotulo: x.nome }))} valor={f.conta} onChange={set('conta')} />
      <Opcoes rotulo="Categoria" itens={doTipo.map((x) => ({ id: x.id_categoria, rotulo: x.nome }))} valor={categoria} onChange={set('categoria')} />
      {tipo === 'ENTRADA' ? <Card sand><Link onPress={() => setLigada(!ligada)} color={c.ink}>{ligada ? '☑' : '☐'} Entrada ligada à atividade do MEI (conta para o teto anual)</Link></Card> : null}
      <Card sand><Small>Regra: o valor precisa ser maior que zero. Pix pessoal sem relação com o negócio não deve entrar no teto.</Small></Card>
      <Aviso>{erro}</Aviso>
      <Btn onPress={enviando ? undefined : salvar}>{enviando ? 'Salvando…' : 'Salvar'}</Btn>
    </>
  );
}

export function Chatbot({ back }) {
  const { c } = useTheme();
  const [texto, setTexto] = useState('');
  const [msgs, setMsgs] = useState([{ de: 'bot', t: 'Oi! Me diga o que aconteceu, por exemplo: “Gastei 150 com internet” ou “Recebi 2.500,00 do cliente”.' }]);
  const [enviando, setEnviando] = useState(false);
  const enviar = async () => {
    const t = texto.trim();
    if (!t || enviando) return;
    setMsgs((m) => [...m, { de: 'eu', t }]); setTexto(''); setEnviando(true);
    try {
      const r = await api('/chatbot/registrar-transacao', { method: 'POST', corpo: { mensagem: t } });
      setMsgs((m) => [...m, { de: 'bot', t: `Registrei ${r.tipo === 'ENTRADA' ? 'uma entrada' : 'uma saída'} de ${brl(r.valor)}: “${r.descricao}”.` }]);
    } catch (e) { setMsgs((m) => [...m, { de: 'bot', t: e.message, erro: true }]); }
    setEnviando(false);
  };
  return (
    <Screen>
      <Top left={<Link onPress={back}>← Voltar</Link>} title={<Txt bold>Lançar por mensagem</Txt>} right={<View style={{ width: 40 }} />} />
      {msgs.map((m, i) => (
        <View key={i} style={{ alignSelf: m.de === 'eu' ? 'flex-end' : 'flex-start', maxWidth: '85%', marginBottom: 8, padding: 10, borderRadius: 14, backgroundColor: m.de === 'eu' ? c.sage : m.erro ? c.terra + '30' : c.card, borderWidth: m.de === 'eu' ? 0 : 1, borderColor: c.line }}>
          <Txt color={m.de === 'eu' ? '#fff' : m.erro ? c.terra : c.ink}>{m.t}</Txt>
        </View>
      ))}
      <Field label="Mensagem" value={texto} onChangeText={setTexto} placeholder="Gastei 150 com internet" />
      <Btn onPress={enviar}>{enviando ? 'Enviando…' : 'Enviar'}</Btn>
    </Screen>
  );
}

export function Salario({ go }) {
  const a = hoje().getFullYear(), m = hoje().getMonth() + 1;
  const carga = useCarga(() => Promise.all([api('/dashboard'), api('/reserva'), api('/retiradas')]));
  const [editando, setEditando] = useState(false);
  const [valor, setValor] = useState('3000');
  const [msg, setMsg] = useState(null);
  const [resultado, setResultado] = useState(null);
  const { c } = useTheme();
  const planejar = async () => {
    setMsg(null);
    const v = valorDe(valor);
    if (!(v >= 0)) return setMsg({ erro: 'Informe um valor válido.' });
    try { await api('/retiradas/planejar', { method: 'PUT', corpo: { ano: a, mes: m, valor_desejado: v } }); setEditando(false); carga.recarregar(); } catch (e) { setMsg({ erro: e.message }); }
  };
  const fechar = async (desejado) => {
    setMsg(null);
    if (desejado == null) return setMsg({ erro: 'Defina o salário sintético do mês antes de fechar.' });
    try { setResultado(await api('/suavizacao/fechar-mes', { method: 'POST', corpo: { ano: a, mes: m, salario_desejado: desejado } })); carga.recarregar(); }
    catch (e) { setMsg({ erro: e.message }); }
  };
  return (
    <Screen>
      <Top left={<Title>Salário sintético</Title>} />
      <Estado carga={carga}>{([d, reserva, retiradas]) => {
        const sal = d.salario_sintetico;
        const atual = retiradas.find((r) => r.ano === a && r.mes === m);
        const historico = retiradas.filter((r) => r.status === 'REALIZADA').slice(-6).reverse();
        return (
          <>
            <Card hero>
              <Small color="#fff">Retirada deste mês</Small>
              <Big color="#fff">{brl(atual ? (atual.status === 'REALIZADA' ? atual.valor : atual.valor_desejado) : 0)}</Big>
              <Small color="#fff">Status: {atual ? (atual.status === 'REALIZADA' ? 'Realizada' : 'Planejada') : 'Não definida'}</Small>
            </Card>
            {resultado ? <Card sand><Txt bold>Mês fechado</Txt><Small style={{ marginTop: 4 }}>{resultado.mensagem}</Small></Card> : null}
            <Card>
              <Txt bold>Reserva de estabilização</Txt>
              <Big color={c.sage}>{brl(reserva.saldo)}</Big>
              <Small>Sobra do mês vai pra reserva; déficit sai dela.</Small>
            </Card>
            <Card>
              <Txt bold>Histórico de retiradas</Txt>
              {historico.length ? <List items={historico.map((r) => {
                const faltou = Number(r.valor_desejado) - Number(r.valor);
                return faltou > 0.004 ? { title: mesAno(r.mes, r.ano), sub: `Faltou ${brl(faltou)} · recebeu ${brl(r.valor)}`, chip: 'Reserva zerada', tone: 't' } : { title: mesAno(r.mes, r.ano), sub: 'Salário completo', right: brl(r.valor), rightColor: 'pos' };
              })} /> : <Vazio>Nenhum mês fechado ainda.</Vazio>}
            </Card>
            <Card>
              <Txt bold>Movimentos da reserva</Txt>
              {reserva.movimentos.length ? <List items={reserva.movimentos.slice(0, 5).map((x) => ({ title: x.descricao, sub: `Saldo após: ${brl(x.saldo_apos)}`, right: `${x.tipo === 'APORTE' ? '+' : '−'} ${brl(x.valor).replace('R$ ', '')}`, rightColor: x.tipo === 'APORTE' ? 'pos' : 'neg' }))} /> : <Vazio>Sem movimentos ainda.</Vazio>}
            </Card>
            {editando ? (
              <Card><Field label="Salário sintético desejado (R$)" value={valor} onChangeText={setValor} keyboardType="decimal-pad" /><Btn onPress={planejar}>Salvar salário</Btn></Card>
            ) : <Btn onPress={() => setEditando(true)}>Ajustar salário sintético</Btn>}
            <Btn outline onPress={() => fechar(atual && atual.status !== 'REALIZADA' ? Number(atual.valor_desejado) : null)}>Fechar o mês</Btn>
            <Aviso>{msg && msg.erro}</Aviso>
          </>
        );
      }}</Estado>
    </Screen>
  );
}
