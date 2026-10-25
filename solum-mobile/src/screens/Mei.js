import React, { useState } from 'react';
import { api } from '../api';
import { Aviso, Btn, Card, Estado, Field, Link, Opcoes, Screen, Small, Title, Top, Txt, useCarga } from '../ui';
import { dataBr, isoDeBr } from '../util';

const ATIVIDADES = [{ id: 'COMERCIO', rotulo: 'Comércio' }, { id: 'SERVICO', rotulo: 'Serviço' }, { id: 'AMBOS', rotulo: 'Comércio e serviço' }];
const CATEGORIAS = [{ id: 'PADRAO', rotulo: 'Padrão' }, { id: 'CAMINHONEIRO', rotulo: 'Caminhoneiro' }];

/** Cadastro dos dados do MEI (RF02). params.onboarding = true logo após criar a conta. */
export function Mei({ back, reset, params }) {
  const carga = useCarga(() => api('/mei').catch((e) => (e.status === 404 ? null : Promise.reject(e))));
  return (
    <Screen>
      <Top left={params && params.onboarding ? <Small>Passo 2 de 2</Small> : <Link onPress={back}>← Voltar</Link>} />
      <Title>Dados do MEI</Title>
      <Small style={{ marginBottom: 10 }}>O DAS depende da atividade. Preencha uma vez; você pode editar depois.</Small>
      <Estado carga={carga}>{(mei) => <Formulario mei={mei} onboarding={params && params.onboarding} back={back} reset={reset} />}</Estado>
    </Screen>
  );
}

function Formulario({ mei, onboarding, back, reset }) {
  const [f, setF] = useState({
    tipo_atividade: mei ? mei.tipo_atividade : 'SERVICO', categoria: mei ? mei.categoria : 'PADRAO', cnae: mei ? mei.cnae : '',
    abertura: mei ? dataBr(mei.data_abertura) : '', cnpj: (mei && mei.cnpj) || '', nome_fantasia: (mei && mei.nome_fantasia) || '',
    cidade: (mei && mei.cidade) || '', uf: (mei && mei.uf) || '',
  });
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const salvar = async () => {
    setErro(null);
    const iso = isoDeBr(f.abertura);
    if (!iso) return setErro('Informe a data de abertura no formato dd/mm/aaaa.');
    setEnviando(true);
    try {
      await api('/mei', { method: 'PUT', corpo: { tipo_atividade: f.tipo_atividade, categoria: f.categoria, cnae: f.cnae, data_abertura: iso, cnpj: f.cnpj || null, nome_fantasia: f.nome_fantasia || null, cidade: f.cidade || null, uf: f.uf ? f.uf.toUpperCase() : null } });
      onboarding ? reset('home') : back();
    } catch (e) { setErro(e.message); setEnviando(false); }
  };
  return (
    <>
      <Card>
        <Opcoes rotulo="Tipo de atividade" itens={ATIVIDADES} valor={f.tipo_atividade} onChange={set('tipo_atividade')} />
        <Opcoes rotulo="Categoria" itens={CATEGORIAS} valor={f.categoria} onChange={set('categoria')} />
      </Card>
      <Field label="CNAE principal (7 dígitos)" value={f.cnae} onChangeText={set('cnae')} placeholder="0000-0/00" keyboardType="numbers-and-punctuation" />
      <Field label="Data de abertura" value={f.abertura} onChangeText={set('abertura')} placeholder="dd/mm/aaaa" />
      <Field label="CNPJ (opcional)" value={f.cnpj} onChangeText={set('cnpj')} placeholder="00.000.000/0000-00" />
      <Field label="Nome fantasia (opcional)" value={f.nome_fantasia} onChangeText={set('nome_fantasia')} placeholder="Nome do seu negócio" />
      <Field label="Cidade (opcional)" value={f.cidade} onChangeText={set('cidade')} placeholder="Sua cidade" />
      <Field label="UF (opcional)" value={f.uf} onChangeText={set('uf')} placeholder="SP" />
      <Aviso>{erro}</Aviso>
      <Btn onPress={enviando ? undefined : salvar}>{enviando ? 'Salvando…' : onboarding ? 'Concluir cadastro' : 'Salvar'}</Btn>
    </>
  );
}
