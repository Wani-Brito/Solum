import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { View, Text, TextInput, Pressable, ScrollView, Platform, useColorScheme } from 'react-native';

export const light = { bg: '#FAF6EE', sand: '#EDE3D3', sage: '#6B8F71', ink: '#2B2926', mut: '#6B6560', terra: '#C97B5C', card: '#FFFFFF', line: '#E3D9C7' };
export const dark = { bg: '#1F1D1A', sand: '#2B2926', sage: '#86AB8C', ink: '#F3ECE0', mut: '#A79F94', terra: '#D98D6E', card: '#26231F', line: '#3A362F' };

const Ctx = createContext(null);
export function ThemeProvider({ children }) {
  const sys = useColorScheme();
  const [mode, setMode] = useState('Escuro');
  const isDark = mode === 'Escuro' || (mode === 'Sistema' && sys === 'dark');
  return <Ctx.Provider value={{ c: isDark ? dark : light, mode, setMode }}>{children}</Ctx.Provider>;
}
export const useTheme = () => useContext(Ctx);

const SERIF = Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, serif' });

export function Txt({ children, size = 14, bold, color, ser, style, ...rest }) {
  const { c } = useTheme();
  return (
    <Text {...rest} style={[{ fontSize: size, color: color || c.ink, fontWeight: bold === true ? '700' : bold || '400', fontFamily: ser ? SERIF : undefined }, style]}>
      {children}
    </Text>
  );
}
export function Small({ children, color, bold, style }) {
  const { c } = useTheme();
  return <Txt size={11} color={color || c.mut} bold={bold} style={style}>{children}</Txt>;
}
export const Big = ({ children, color, size = 26, style }) => <Txt ser bold size={size} color={color} style={[{ marginVertical: 2 }, style]}>{children}</Txt>;
export const Title = ({ children }) => <Txt ser bold size={20}>{children}</Txt>;

export function Money({ children, neg, size }) {
  const { c } = useTheme();
  return <Txt bold="600" size={size} color={neg ? c.terra : c.sage}>{children}</Txt>;
}

export function Screen({ children }) {
  const { c } = useTheme();
  return <ScrollView style={{ flex: 1, backgroundColor: c.bg }} contentContainerStyle={{ padding: 14, paddingBottom: 24 }}>{children}</ScrollView>;
}

export function Top({ left, title, right }) {
  return <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>{left}{title}{right}</View>;
}

export function Card({ children, hero, sand, style }) {
  const { c } = useTheme();
  return (
    <View style={[{ backgroundColor: hero ? c.sage : sand ? c.sand : c.card, borderWidth: hero || sand ? 0 : 1, borderColor: c.line, borderRadius: 14, padding: 12, marginBottom: 10 }, style]}>
      {children}
    </View>
  );
}

export const Row = ({ children, style }) => (
  <View style={[{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }, style]}>{children}</View>
);

export function Chip({ children, tone, onPress }) {
  const { c } = useTheme();
  const bg = tone === 'g' ? c.sage : tone === 't' ? c.terra : c.sand;
  const fg = tone ? '#fff' : c.ink;
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={{ backgroundColor: bg, borderRadius: 99, paddingHorizontal: 9, paddingVertical: 2 }}>
      <Text style={{ fontSize: 10, color: fg }}>{children}</Text>
    </Pressable>
  );
}

export function Bar({ pct, warn }) {
  const { c } = useTheme();
  return (
    <View style={{ height: 8, backgroundColor: c.sand, borderRadius: 9, overflow: 'hidden', marginTop: 6, marginBottom: 4 }}>
      <View style={{ width: `${pct}%`, height: '100%', backgroundColor: warn ? c.terra : c.sage, borderRadius: 9 }} />
    </View>
  );
}

export function ListRow({ title, sub, right, rightColor, chip, tone, last, onPress }) {
  const { c } = useTheme();
  const col = rightColor === 'pos' ? c.sage : rightColor === 'neg' ? c.terra : undefined;
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 9, borderBottomWidth: last ? 0 : 1, borderBottomColor: c.line }}>
      <View style={{ flex: 1, paddingRight: 8 }}>
        <Txt>{title}</Txt>
        {sub ? <Small>{sub}</Small> : null}
      </View>
      {chip ? <Chip tone={tone}>{chip}</Chip> : right != null ? <Txt bold={col ? '600' : undefined} color={col}>{right}</Txt> : null}
    </Pressable>
  );
}
export const List = ({ items }) => <>{items.map((it, i) => <ListRow key={i} {...it} last={i === items.length - 1} />)}</>;

export function Field({ label, value, onChangeText, placeholder, secure, big, keyboardType, multiline, editable = true }) {
  const { c } = useTheme();
  return (
    <View style={{ borderWidth: 1, borderColor: c.line, backgroundColor: c.card, borderRadius: 10, paddingHorizontal: 10, paddingVertical: 8, marginBottom: 8, opacity: editable ? 1 : 0.6 }}>
      <Small>{label}</Small>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={c.mut}
        secureTextEntry={secure}
        keyboardType={keyboardType}
        multiline={multiline}
        editable={editable}
        autoCapitalize="none"
        style={{ color: c.ink, fontSize: big ? 26 : 14, fontFamily: big ? SERIF : undefined, fontWeight: big ? '700' : '400', padding: 0, marginTop: 2 }}
      />
    </View>
  );
}

export function Btn({ children, outline, color, onPress, style }) {
  const { c } = useTheme();
  const accent = color || c.sage;
  return (
    <Pressable onPress={onPress} style={[{ marginTop: 8, borderRadius: 12, paddingVertical: 11, alignItems: 'center', backgroundColor: outline ? 'transparent' : c.ink, borderWidth: outline ? 1.5 : 0, borderColor: accent }, style]}>
      <Text style={{ fontWeight: '600', fontSize: 14, color: outline ? accent : c.bg }}>{children}</Text>
    </Pressable>
  );
}

export function Seg({ items, initial = 0, onChange, style }) {
  const { c } = useTheme();
  const [on, setOn] = useState(initial);
  return (
    <View style={[{ flexDirection: 'row', backgroundColor: c.sand, borderRadius: 10, padding: 3, marginBottom: 10 }, style]}>
      {items.map((t, i) => (
        <Pressable key={t} onPress={() => { setOn(i); onChange && onChange(t, i); }} style={{ flex: 1, alignItems: 'center', paddingVertical: 6, borderRadius: 8, backgroundColor: on === i ? c.card : 'transparent' }}>
          <Text style={{ fontSize: 12, color: on === i ? c.ink : c.mut, fontWeight: on === i ? '600' : '400' }}>{t}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function Avatar({ size = 30, nome = 'E' }) {
  const { c } = useTheme();
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: c.sage, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: '#fff', fontWeight: '700', fontSize: size * 0.4 }}>{(nome || 'E').trim()[0].toUpperCase()}</Text>
    </View>
  );
}

export function MiniBars({ data }) {
  const { c } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: 70, gap: 6, marginTop: 8 }}>
      {data.map((d, i) => (
        <View key={i} style={{ flex: 1, height: `${d[0]}%`, backgroundColor: d[1] ? c.terra : c.sage, opacity: 0.85, borderTopLeftRadius: 4, borderTopRightRadius: 4 }} />
      ))}
    </View>
  );
}

export const Link = ({ children, onPress, color, bold }) => (
  <Pressable onPress={onPress}><Txt size={11} color={color} bold={bold}>{children}</Txt></Pressable>
);

/** Escolha entre opções (chips). itens: [{id, rotulo}] */
export function Opcoes({ itens, valor, onChange, rotulo }) {
  const { c } = useTheme();
  return (
    <View style={{ marginBottom: 8 }}>
      {rotulo ? <Small style={{ marginBottom: 4 }}>{rotulo}</Small> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        {itens.map((i) => (
          <Pressable key={i.id} onPress={() => onChange(i.id)} style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 99, borderWidth: 1, borderColor: valor === i.id ? c.sage : c.line, backgroundColor: valor === i.id ? c.sage : c.card }}>
            <Text style={{ fontSize: 12, color: valor === i.id ? '#fff' : c.ink }}>{i.rotulo}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function useCarga(carregar, deps = []) {
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: true });
  const recarregar = useCallback(() => {
    setEstado((s) => ({ ...s, carregando: true, erro: null }));
    carregar().then((dados) => setEstado({ dados, erro: null, carregando: false })).catch((e) => setEstado({ dados: null, erro: e, carregando: false }));
  }, deps);
  useEffect(() => { recarregar(); }, [recarregar]);
  return { ...estado, recarregar };
}

/** Mostra carregando, erro (com tentar de novo) ou o conteúdo. */
export function Estado({ carga, children }) {
  const { c } = useTheme();
  if (carga.carregando && !carga.dados) return <View style={{ padding: 30, alignItems: 'center' }}><Small>Carregando…</Small></View>;
  if (carga.erro) {
    return (
      <Card style={{ borderColor: c.terra }}>
        <Txt color={c.terra} bold>Não deu certo</Txt>
        <Small style={{ marginVertical: 4 }}>{carga.erro.message}</Small>
        <Btn outline color={c.terra} onPress={carga.recarregar}>Tentar de novo</Btn>
      </Card>
    );
  }
  return children(carga.dados);
}

export function Aviso({ tipo = 'erro', children }) {
  const { c } = useTheme();
  if (!children) return null;
  const cor = tipo === 'erro' ? c.terra : c.sage;
  return <View style={{ backgroundColor: cor + '30', borderRadius: 10, padding: 10, marginTop: 8 }}><Text style={{ color: cor, fontSize: 13 }}>{children}</Text></View>;
}

export function Vazio({ children }) {
  return <View style={{ padding: 20, alignItems: 'center' }}><Small>{children}</Small></View>;
}
