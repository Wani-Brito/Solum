# Solum: painel web do administrador (React)

Painel do administrador: controle administrativo, usuários, vendas, Tabela DAS, configurações e perfil. Só aceita o perfil Admin.

## Como rodar

Precisa do Node 18 ou mais novo e da API rodando (veja `solum-backend`).

```bat
cd solum-web
copy .env.example .env
npm install
npm run dev
```

Abra http://localhost:5173 e entre com o administrador do seed (`admin@solum.app`, senha `admin123`).

O endereço da API fica em `.env` (`VITE_API_URL`, padrão `http://localhost:8000`). O endereço do painel precisa estar em `ALLOWED_ORIGINS` da API.

Para gerar a versão de produção: `npm run build` (arquivos na pasta `dist`).

## Estrutura

```
src/api.js       cliente da API (token, tratamento de erros)
src/util.jsx     formatação, carregamento e gráficos de barras
src/pages.jsx    Login, Controle, Usuários, Vendas, Tabela DAS, Configurações, Meu perfil
src/App.jsx      menu lateral, sessão e troca de páginas
src/styles.css   paleta (modo escuro por padrão)
```

## Problemas comuns

- "Não foi possível conectar à API": a API não está rodando ou o endereço em `.env` está errado.
- Erro `EPERM` ao rodar `npm install` no Windows: o Windows ou o antivírus bloqueou a criação de pastas. Desligue temporariamente o "Acesso controlado a pastas" do Windows Defender, ou rode o terminal como administrador, ou use uma pasta fora de OneDrive e de unidades externas.
