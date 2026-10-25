import React, { useState } from 'react';
import { View } from 'react-native';
import { api } from '../api';
import { Aviso, Btn, Card, Field, Link, Small, Top, Txt, useTheme } from '../ui';

export function Login({ go, entrar }) {
  const { c } = useTheme();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const enviar = async () => {
    setErro(null);
    if (!email.trim() || !senha) return setErro('Informe e-mail e senha.');
    setEnviando(true);
    try { entrar(await api('/auth/login', { method: 'POST', corpo: { email: email.trim(), senha } })); }
    catch (e) { setErro(e.message); setEnviando(false); }
  };
  return (
    <View style={{ flex: 1, padding: 14, justifyContent: 'center' }}>
      <View style={{ alignItems: 'center', marginBottom: 22 }}>
        <Txt ser bold size={26} style={{ letterSpacing: 1 }}>SOLUM<Txt ser bold size={26} color={c.sage}>.</Txt></Txt>
        <Small>Sua liberdade merece estabilidade.</Small>
      </View>
      <Field label="E-mail" value={email} onChangeText={setEmail} placeholder="voce@email.com" keyboardType="email-address" />
      <Field label="Senha" value={senha} onChangeText={setSenha} placeholder="Sua senha" secure />
      <Aviso>{erro}</Aviso>
      <Btn onPress={enviando ? undefined : enviar}>{enviando ? 'Entrando…' : 'Entrar'}</Btn>
      <Btn outline onPress={() => go('cadastro')}>Criar conta</Btn>
      <View style={{ alignItems: 'center', marginTop: 12 }}><Small>Novo por aqui? Crie sua conta em 1 minuto.</Small></View>
    </View>
  );
}

export function Cadastro({ back, entrar }) {
  const { c } = useTheme();
  const [f, setF] = useState({ nome: '', email: '', telefone: '', senha: '', confirmar: '' });
  const [aceite, setAceite] = useState(false);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const enviar = async () => {
    setErro(null);
    if (f.nome.trim().length < 2) return setErro('Informe seu nome.');
    if (f.senha.length < 6) return setErro('A senha precisa ter pelo menos 6 caracteres.');
    if (f.senha !== f.confirmar) return setErro('As senhas não conferem.');
    if (!aceite) return setErro('Aceite os termos de uso para continuar.');
    setEnviando(true);
    try { entrar(await api('/auth/registro', { method: 'POST', corpo: { nome: f.nome.trim(), email: f.email.trim(), senha: f.senha, telefone: f.telefone || null } }), true); }
    catch (e) { setErro(e.message); setEnviando(false); }
  };
  return (
    <View style={{ flex: 1, padding: 14 }}>
      <Top left={<Link onPress={back}>← Voltar</Link>} right={<Small>Passo 1 de 2</Small>} />
      <Txt ser bold size={22} style={{ marginTop: 4, marginBottom: 12 }}>Criar conta</Txt>
      <Field label="Nome" value={f.nome} onChangeText={set('nome')} placeholder="Seu nome completo" />
      <Field label="E-mail" value={f.email} onChangeText={set('email')} placeholder="voce@email.com" keyboardType="email-address" />
      <Field label="Telefone" value={f.telefone} onChangeText={set('telefone')} placeholder="(19) 90000-0000" keyboardType="phone-pad" />
      <Field label="Senha" value={f.senha} onChangeText={set('senha')} placeholder="Mínimo 6 caracteres" secure />
      <Field label="Confirmar senha" value={f.confirmar} onChangeText={set('confirmar')} placeholder="Repita a senha" secure />
      <Card sand><Link onPress={() => setAceite(!aceite)} color={c.ink}>{aceite ? '☑' : '☐'} Li e aceito os termos de uso e a política de privacidade.</Link></Card>
      <Aviso>{erro}</Aviso>
      <Btn onPress={enviando ? undefined : enviar}>{enviando ? 'Criando…' : 'Criar conta'}</Btn>
      <View style={{ alignItems: 'center', marginTop: 10 }}><Small>Já tem conta? <Small color={c.sage} bold>Entrar</Small></Small></View>
    </View>
  );
}
