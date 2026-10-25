import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, SafeAreaView, StatusBar, Platform } from 'react-native';
import { ThemeProvider, useTheme } from './src/ui';
import { api, aoSessaoExpirar, definirToken } from './src/api';
import { Login, Cadastro } from './src/screens/Auth';
import { Mei } from './src/screens/Mei';
import { Home, Caixa, NovaTransacao, Salario, Chatbot } from './src/screens/Home';
import { Impostos, Precificacao } from './src/screens/Fiscal';
import { Faturas, NovaFatura, Notificacoes } from './src/screens/Faturas';
import { Metas, NovaMeta, Aporte } from './src/screens/Metas';
import { Invest } from './src/screens/Invest';
import { Mais, Perfil, Prefs, Contas } from './src/screens/Mais';

const TABS = [['home', '⌂', 'Início'], ['caixa', '⇅', 'Caixa'], ['salario', '◔', 'Salário'], ['impostos', '%', 'Impostos'], ['mais', '⋯', 'Mais']];
const TAB_OF = { home: 'home', caixa: 'caixa', nova: 'caixa', chatbot: 'caixa', salario: 'salario', impostos: 'impostos' };
const SEM_ABAS = ['login', 'cadastro', 'mei', 'perfil', 'prefs'];
const TELAS = { login: Login, cadastro: Cadastro, mei: Mei, home: Home, caixa: Caixa, nova: NovaTransacao, chatbot: Chatbot, salario: Salario, impostos: Impostos, precificacao: Precificacao, faturas: Faturas, 'nova-fatura': NovaFatura, notificacoes: Notificacoes, metas: Metas, 'nova-meta': NovaMeta, aporte: Aporte, invest: Invest, mais: Mais, perfil: Perfil, prefs: Prefs, contas: Contas };

function Shell() {
  const { c } = useTheme();
  const [pilha, setPilha] = useState([{ nome: 'login' }]);
  const [usuario, setUsuario] = useState(null);
  const atual = pilha[pilha.length - 1];

  const nav = {
    go: (nome, params) => setPilha((p) => [...p, { nome, params }]),
    back: () => setPilha((p) => (p.length > 1 ? p.slice(0, -1) : p)),
    reset: (nome, params) => setPilha([{ nome, params }]),
  };
  const sair = () => { definirToken(null); setUsuario(null); nav.reset('login'); };
  useEffect(() => { aoSessaoExpirar(sair); }, []);

  // depois do login: se o MEI ainda não foi cadastrado, começa pelo cadastro dele
  const entrar = async (resposta, novoUsuario) => {
    definirToken(resposta.access_token);
    setUsuario(resposta.usuario);
    if (novoUsuario) return nav.reset('mei', { onboarding: true });
    try { await api('/mei'); nav.reset('home'); }
    catch (e) { e.status === 404 ? nav.reset('mei', { onboarding: true }) : nav.reset('home'); }
  };

  const Tela = TELAS[atual.nome];
  const ativa = TAB_OF[atual.nome] || 'mais';
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.bg, paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 }}>
      <StatusBar barStyle={c.bg === '#FAF6EE' ? 'dark-content' : 'light-content'} />
      <View style={{ flex: 1 }}>
        <Tela key={pilha.length + atual.nome} {...nav} entrar={entrar} sair={sair} usuario={usuario} atualizarUsuario={setUsuario} params={atual.params} />
      </View>
      {!SEM_ABAS.includes(atual.nome) && (
        <View style={{ flexDirection: 'row', backgroundColor: c.card, borderTopWidth: 1, borderTopColor: c.line, paddingTop: 8, paddingBottom: 10 }}>
          {TABS.map(([k, icone, rotulo]) => (
            <Pressable key={k} onPress={() => nav.reset(k)} style={{ flex: 1, alignItems: 'center' }}>
              <Text style={{ fontSize: 16, color: ativa === k ? c.sage : c.mut }}>{icone}</Text>
              <Text style={{ fontSize: 10, color: ativa === k ? c.sage : c.mut, fontWeight: ativa === k ? '700' : '400' }}>{rotulo}</Text>
            </Pressable>
          ))}
        </View>
      )}
    </SafeAreaView>
  );
}

export default function App() {
  return <ThemeProvider><Shell /></ThemeProvider>;
}
