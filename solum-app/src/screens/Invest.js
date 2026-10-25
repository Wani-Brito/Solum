import React, { useState } from 'react';
import { api } from '../api';
import { Aviso, Big, Btn, Card, Chip, Estado, Field, List, Opcoes, Row, Screen, Small, Title, Top, Txt, Vazio, useCarga } from '../ui';
import { brl, dataBr, valorDe } from '../util';

const TIPO = { RENDA_FIXA: 'Renda fixa', RENDA_VARIAVEL: 'Renda variável', FUNDOS: 'Fundos', TESOURO: 'Tesouro', OUTROS: 'Outros' };
const RISCOS = [{ id: 'CONSERVADOR', rotulo: 'Conservador' }, { id: 'MODERADO', rotulo: 'Moderado' }, { id: 'ARROJADO', rotulo: 'Arrojado' }];

export function Invest({ usuario, atualizarUsuario }) {
  const carga = useCarga(() => Promise.all([api('/investimentos/carteira'), api('/investimentos/propostas'), api('/investimentos/cotacoes')]));
  const [perfil, setPerfil] = useState('CONSERVADOR');
  const [valor, setValor] = useState('');
  const [erro, setErro] = useState(null);
  const premium = !(carga.erro && carga.erro.status === 403);
  const assinar = async () => {
    setErro(null);
    try { await api('/assinaturas', { method: 'POST', corpo: {} }); atualizarUsuario({ ...usuario, perfil: 'PREMIUM' }); carga.recarregar(); } catch (e) { setErro(e.message); }
  };
  const gerar = async () => {
    setErro(null);
    const v = valorDe(valor);
    if (!(v > 0)) return setErro('Informe o valor disponível para investir.');
    try { await api('/investimentos/recomendacao', { method: 'POST', corpo: { valor_disponivel: v, perfil_risco: perfil } }); setValor(''); carga.recarregar(); } catch (e) { setErro(e.message); }
  };
  const decidir = async (p, status) => { try { await api(`/investimentos/propostas/${p.id_proposta}`, { method: 'PATCH', corpo: { status } }); carga.recarregar(); } catch (e) { setErro(e.message); } };
  return (
    <Screen>
      <Top left={<Title>Investimentos</Title>} right={<Chip tone="t">Premium</Chip>} />
      {!premium ? (
        <Card>
          <Txt bold>Recurso do plano Premium</Txt>
          <Small style={{ marginVertical: 4 }}>Carteira, indicações de investimento e cotações públicas. Apenas informativo, sem compra real. O pagamento aqui é simulado.</Small>
          <Btn onPress={assinar}>Assinar Premium (simulado)</Btn>
          <Aviso>{erro}</Aviso>
        </Card>
      ) : (
        <Estado carga={carga}>{([cart, props, cot]) => (
          <>
            <Card hero>
              <Small color="#fff">Carteira</Small>
              <Big color="#fff">{brl(cart.total)}</Big>
              <Small color="#fff">Rentabilidade média: {Number(cart.rentabilidade_media).toFixed(2).replace('.', ',')}% a.a.</Small>
            </Card>
            <Card>
              <Txt bold>Aplicações</Txt>
              {cart.investimentos.length ? <List items={cart.investimentos.map((i) => ({ title: i.nome, sub: `${TIPO[i.tipo]}${i.prazo ? ' · ' + i.prazo : ''}`, right: brl(i.valor_atual) }))} /> : <Vazio>Nenhuma aplicação registrada.</Vazio>}
            </Card>
            <Card>
              <Txt bold>Simulador de sugestão</Txt>
              <Opcoes rotulo="Perfil de risco" itens={RISCOS} valor={perfil} onChange={setPerfil} />
              <Field label="Valor disponível (R$)" value={valor} onChangeText={setValor} placeholder="1.000,00" keyboardType="decimal-pad" />
              <Btn onPress={gerar}>Gerar sugestão</Btn>
              <Aviso>{erro}</Aviso>
            </Card>
            {props.map((p) => (
              <Card key={p.id_proposta}>
                <Row><Txt bold>{p.nome}</Txt><Chip tone={p.status === 'ACEITA' ? 'g' : undefined}>{p.status === 'DISPONIVEL' ? 'Disponível' : p.status === 'ACEITA' ? 'Aceita' : 'Recusada'}</Chip></Row>
                <Small>Risco {p.risco.toLowerCase()} · {p.rentabilidade_estimada != null ? `rentab. estimada ${Number(p.rentabilidade_estimada).toFixed(2).replace('.', ',')}% a.a.` : 'rentabilidade variável (não prometida)'} · {brl(p.valor_sugerido)}</Small>
                <Txt style={{ marginTop: 2 }}>{p.descricao}</Txt>
                {p.status === 'DISPONIVEL' ? <Row style={{ marginTop: 8 }}><Btn style={{ flex: 1, marginTop: 0 }} onPress={() => decidir(p, 'ACEITA')}>Aceitar</Btn><Btn outline style={{ flex: 1, marginTop: 0 }} onPress={() => decidir(p, 'RECUSADA')}>Recusar</Btn></Row> : null}
              </Card>
            ))}
            <Card sand>
              <Txt bold>Cotações públicas</Txt>
              {cot.cotacoes.map((c) => <Row key={c.simbolo}><Small>{c.descricao}</Small><Txt bold>{Number(c.valor).toFixed(2).replace('.', ',')}%</Txt></Row>)}
              <Small style={{ marginTop: 4 }}>Fonte: {cot.cotacoes[0] ? cot.cotacoes[0].fonte : '—'} · atualizado em {cot.cotacoes[0] ? dataBr(cot.cotacoes[0].atualizado_em) : '—'}</Small>
            </Card>
          </>
        )}</Estado>
      )}
    </Screen>
  );
}
