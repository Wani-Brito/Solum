import React, { useState } from 'react';
import { api } from '../api';
import { Aviso, Bar, Big, Btn, Card, Chip, Estado, Field, List, Opcoes, Row, Screen, Small, Title, Top, Txt, Vazio, useCarga } from '../ui';
import { brl, dataBr, diasAte, pct, valorDe } from '../util';

export function Impostos({ go }) {
  const carga = useCarga(() => Promise.all([api('/impostos/das'), api('/impostos/cota-mensal', { method: 'POST' }), api('/teto'), api('/impostos/obrigacoes')]));
  const [msg, setMsg] = useState(null);
  const pagar = async (o) => { try { await api(`/impostos/obrigacoes/${o.id_obrigacao}/pagar`, { method: 'PATCH' }); carga.recarregar(); } catch (e) { setMsg(e.message); } };
  const semMei = carga.erro && /dados do MEI/.test(carga.erro.message);
  return (
    <Screen>
      <Top left={<Title>Impostos</Title>} />
      {semMei ? <Card><Txt bold>Falta cadastrar seu MEI</Txt><Small style={{ marginVertical: 4 }}>O DAS depende do tipo de atividade e da categoria.</Small><Btn onPress={() => go('mei')}>Cadastrar dados do MEI</Btn></Card> : (
        <Estado carga={carga}>{([das, cota, teto, obrig]) => {
          const pendentes = obrig.filter((o) => o.status !== 'PAGO').slice(0, 3);
          return (
            <>
              <Row style={{ marginBottom: 8 }}><Small>Atividade: {das.tipo_atividade === 'AMBOS' ? 'Comércio e serviço' : das.tipo_atividade === 'SERVICO' ? 'Serviço' : 'Comércio'}</Small><Chip tone="g">{das.categoria === 'PADRAO' ? 'Padrão' : 'Caminhoneiro'}</Chip></Row>
              <Card>
                <Row><Txt bold>DAS mensal</Txt><Txt bold>{brl(das.total)}</Txt></Row>
                <List items={[{ title: 'INSS', sub: 'Federal', right: brl(das.esferas.federal.valor) }, ...(das.esferas.estadual.valor > 0 ? [{ title: 'ICMS', sub: 'Estadual', right: brl(das.esferas.estadual.valor) }] : []), ...(das.esferas.municipal.valor > 0 ? [{ title: 'ISS', sub: 'Municipal', right: brl(das.esferas.municipal.valor) }] : [])]} />
              </Card>
              <Card>
                <Row><Txt bold>Reserva do imposto</Txt><Chip tone="g">Ativa</Chip></Row>
                <Big size={20}>{brl(cota.valor_reservado)}</Big>
                <Small>Valor fixo separado para o próximo DAS, independe do faturamento.</Small>
                <Small style={{ marginTop: 6 }}>Faturamento do mês: {brl(cota.faturamento_mes)} · líquido do DAS: {brl(cota.faturamento_liquido)} · {pct(cota.percentual_comprometido)} comprometido</Small>
              </Card>
              <Card>
                <Row><Txt bold>Teto de faturamento</Txt><Txt bold>{pct(teto.percentual)}</Txt></Row>
                <Bar pct={Math.min(100, teto.percentual)} warn={teto.nivel !== 'NORMAL'} />
                <Small>{teto.mensagem} Restam {brl(teto.restante)} · alerta em {pct(teto.percentual_alerta)}.</Small>
              </Card>
              <Card>
                <Txt bold>Lembretes</Txt>
                {pendentes.length ? <List items={pendentes.map((o) => { const d = diasAte(o.data_vencimento); return { title: o.descricao, sub: `Vence ${dataBr(o.data_vencimento)}${o.valor > 0 ? ' · ' + brl(o.valor) : ''}`, chip: d < 0 ? 'Atrasado' : d === 0 ? 'Hoje' : `${d} dias`, tone: d < 0 ? 't' : undefined, onPress: () => pagar(o) }; })} /> : <Vazio>Nenhuma obrigação pendente.</Vazio>}
                <Small style={{ marginTop: 4 }}>Toque em um lembrete para marcar como pago.</Small>
              </Card>
              <Aviso>{msg}</Aviso>
            </>
          );
        }}</Estado>
      )}
    </Screen>
  );
}

export function Precificacao() {
  const carga = useCarga(() => api('/servicos'));
  const [f, setF] = useState({ nome: '', horas: '', materiais: '0', outros: '0' });
  const [p, setP] = useState({ id: null, hora: '40', margem: '30', qtd: '4' });
  const [res, setRes] = useState(null);
  const [erro, setErro] = useState(null);
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const criar = async () => {
    setErro(null);
    try { const s = await api('/servicos', { method: 'POST', corpo: { nome: f.nome.trim(), horas_trabalho: valorDe(f.horas), custo_materiais: valorDe(f.materiais) || 0, outros_custos: valorDe(f.outros) || 0 } }); setF({ nome: '', horas: '', materiais: '0', outros: '0' }); setP({ ...p, id: s.id_servico }); carga.recarregar(); }
    catch (e) { setErro(e.message); }
  };
  const calcular = async (id) => {
    setErro(null);
    try { setRes(await api('/precificacao/calcular', { method: 'POST', corpo: { id_servico: id, margem_lucro: valorDe(p.margem), custo_hora: valorDe(p.hora), servicos_por_mes: parseInt(p.qtd, 10) || 1 } })); }
    catch (e) { setErro(e.message); }
  };
  return (
    <Screen>
      <Top left={<Title>Precificação</Title>} />
      <Estado carga={carga}>{(servicos) => {
        const escolhido = p.id || (servicos[0] && servicos[0].id_servico);
        const s = servicos.find((x) => x.id_servico === escolhido);
        return (
          <>
            {servicos.length ? (
              <Card>
                <Opcoes rotulo="Serviço" itens={servicos.map((x) => ({ id: x.id_servico, rotulo: x.nome }))} valor={escolhido} onChange={(id) => { setP({ ...p, id }); setRes(null); }} />
                {s ? <Small>{s.horas_trabalho} h · materiais {brl(s.custo_materiais)} · outros {brl(s.outros_custos)}</Small> : null}
                <Field label="Valor da sua hora (R$)" value={p.hora} onChangeText={(v) => setP({ ...p, hora: v })} keyboardType="decimal-pad" />
                <Field label="Margem de lucro (%)" value={p.margem} onChangeText={(v) => setP({ ...p, margem: v })} keyboardType="decimal-pad" />
                <Field label="Serviços por mês (para ratear o DAS)" value={p.qtd} onChangeText={(v) => setP({ ...p, qtd: v })} keyboardType="number-pad" />
                <Btn onPress={() => calcular(escolhido)}>Calcular preço mínimo</Btn>
              </Card>
            ) : <Card><Small>Cadastre um serviço abaixo para calcular o preço mínimo.</Small></Card>}
            {res ? (
              <Card hero>
                <Small color="#fff">Preço mínimo sugerido</Small>
                <Big color="#fff">{brl(res.preco_minimo)}</Big>
                <Small color="#fff">Ponto de equilíbrio {brl(res.ponto_equilibrio)} · já embute custos e o DAS rateado ({brl(res.imposto_rateado)})</Small>
              </Card>
            ) : null}
            <Card>
              <Txt bold style={{ marginBottom: 6 }}>Novo serviço</Txt>
              <Field label="Nome" value={f.nome} onChangeText={set('nome')} placeholder="Ex.: Criação de site" />
              <Field label="Horas de trabalho" value={f.horas} onChangeText={set('horas')} placeholder="20" keyboardType="decimal-pad" />
              <Field label="Custo de materiais (R$)" value={f.materiais} onChangeText={set('materiais')} keyboardType="decimal-pad" />
              <Field label="Outros custos (R$)" value={f.outros} onChangeText={set('outros')} keyboardType="decimal-pad" />
              <Btn outline onPress={criar}>Salvar serviço</Btn>
            </Card>
            <Aviso>{erro}</Aviso>
          </>
        );
      }}</Estado>
    </Screen>
  );
}
