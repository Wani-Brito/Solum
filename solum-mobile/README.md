# Solum: app mobile (React Native com Expo)

Aplicativo do MEI. Usa só `react` e `react-native`, então funciona com a versão do Expo que você instalar.

## Como rodar

1. Deixe a API rodando (veja `solum-backend`) e rode o seed de demonstração.
2. Crie um projeto Expo vazio, **numa pasta fora desta**:

```bat
npx create-expo-app@latest solum-app --template blank
```

3. Copie para dentro do projeto criado o arquivo `App.js` (substituindo o que veio) e a pasta `src`:

```bat
copy /Y solum-mobile\App.js solum-app\App.js
xcopy /E /I /Y solum-mobile\src solum-app\src
```

4. Aponte o app para a API (veja abaixo) e inicie:

```bat
cd solum-app
npx expo start
```

Escaneie o QR code com o Expo Go no celular, ou aperte `a` (emulador Android) ou `w` (navegador).

## Endereço da API

O padrão é `http://localhost:8000`, que só funciona no navegador do mesmo computador. Defina o endereço certo sem editar o código:

- Celular com Expo Go: use o IP do computador na rede Wi-Fi, ex.: `EXPO_PUBLIC_API_URL=http://192.168.0.10:8000 npx expo start` (no Windows PowerShell: `$env:EXPO_PUBLIC_API_URL="http://192.168.0.10:8000"; npx expo start`).
- Emulador Android: `http://10.0.2.2:8000`.

No celular, inclua o endereço do app em `ALLOWED_ORIGINS` só se for rodar no navegador; apps nativos não usam CORS.

## Entrar

Usuária de demonstração: `emilly@email.com`, senha `12345678`. Ou crie uma conta nova: o app leva ao cadastro do MEI logo depois.

## Estrutura

```
App.js                  navegação em pilha, abas e sessão
src/api.js              cliente da API (token, erros)
src/config.js           endereço da API
src/ui.js               tema escuro/claro e componentes
src/util.js             formatação de dinheiro e datas
src/screens/            Auth, Mei, Home (dashboard, caixa, lançamentos, salário, chatbot),
                        Fiscal (impostos, precificação), Faturas, Metas, Invest, Mais
```

O app abre sempre no modo escuro; o usuário troca em Mais, Preferências.
