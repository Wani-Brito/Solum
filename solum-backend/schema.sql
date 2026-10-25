-- SOLUM - Modelo de banco de dados (PostgreSQL)
-- Gerado a partir de app/models.py. Para recriar o banco do zero: psql -f schema.sql


CREATE TABLE cnaes_mei (
	cnae VARCHAR(10) NOT NULL, 
	descricao VARCHAR(200) NOT NULL, 
	tipo_atividade VARCHAR(10) NOT NULL, 
	PRIMARY KEY (cnae)
);

CREATE TABLE configuracoes_sistema (
	chave VARCHAR(40) NOT NULL, 
	valor VARCHAR(80) NOT NULL, 
	PRIMARY KEY (chave)
);

CREATE TABLE cotacao_cache (
	simbolo VARCHAR(20) NOT NULL, 
	descricao VARCHAR(80) NOT NULL, 
	valor NUMERIC(12, 4) NOT NULL, 
	fonte VARCHAR(80) NOT NULL, 
	atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (simbolo)
);

CREATE TABLE planos (
	id_plano SERIAL NOT NULL, 
	nome VARCHAR(20) NOT NULL, 
	preco_mensal NUMERIC(12, 2) NOT NULL, 
	ativo BOOLEAN NOT NULL, 
	PRIMARY KEY (id_plano), 
	CONSTRAINT ck_plano_preco CHECK (preco_mensal >= 0), 
	UNIQUE (nome)
);

CREATE TABLE tabela_das (
	id_tabela SERIAL NOT NULL, 
	ano INTEGER NOT NULL, 
	salario_minimo NUMERIC(12, 2) NOT NULL, 
	perc_inss NUMERIC(5, 2) NOT NULL, 
	perc_inss_caminhoneiro NUMERIC(5, 2) NOT NULL, 
	valor_icms NUMERIC(12, 2) NOT NULL, 
	valor_iss NUMERIC(12, 2) NOT NULL, 
	teto_anual NUMERIC(12, 2) NOT NULL, 
	teto_caminhoneiro NUMERIC(12, 2) NOT NULL, 
	fonte VARCHAR(200) NOT NULL, 
	data_atualizacao TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_tabela), 
	CONSTRAINT ck_das_positivos CHECK (salario_minimo > 0 AND teto_anual > 0), 
	UNIQUE (ano)
);

CREATE TABLE usuarios (
	id_usuario SERIAL NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	senha VARCHAR(255) NOT NULL, 
	telefone VARCHAR(20), 
	perfil VARCHAR(10) NOT NULL, 
	ativo BOOLEAN NOT NULL, 
	data_cadastro TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_usuario), 
	CONSTRAINT ck_usuarios_perfil CHECK (perfil IN ('NORMAL', 'PREMIUM', 'ADMIN')), 
	UNIQUE (email)
);

CREATE TABLE assinaturas (
	id_assinatura SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_plano INTEGER NOT NULL, 
	data_inicio DATE NOT NULL, 
	data_fim DATE, 
	status VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id_assinatura), 
	CONSTRAINT ck_assin_status CHECK (status IN ('ATIVA', 'PENDENTE', 'CANCELADA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_plano) REFERENCES planos (id_plano)
);

CREATE TABLE carteiras_investimentos (
	id_carteira SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id_carteira), 
	UNIQUE (id_usuario), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE categorias (
	id_categoria SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(60) NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id_categoria), 
	CONSTRAINT ck_categoria_tipo CHECK (tipo IN ('ENTRADA', 'SAIDA')), 
	CONSTRAINT uq_categoria UNIQUE (id_usuario, nome, tipo), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE clientes (
	id_cliente SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	tipo_pessoa VARCHAR(2) NOT NULL, 
	documento VARCHAR(18), 
	email VARCHAR(120), 
	bloqueado BOOLEAN NOT NULL, 
	data_cadastro TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_cliente), 
	CONSTRAINT ck_cliente_tipo CHECK (tipo_pessoa IN ('PF', 'PJ')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE configuracoes_mei (
	id_configuracao SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	teto_anual NUMERIC(12, 2) NOT NULL, 
	percentual_alerta NUMERIC(5, 2) NOT NULL, 
	PRIMARY KEY (id_configuracao), 
	CONSTRAINT uq_config_mei UNIQUE (id_usuario, ano), 
	CONSTRAINT ck_config_alerta CHECK (percentual_alerta > 0 AND percentual_alerta <= 100), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE contas (
	id_conta SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(60) NOT NULL, 
	banco VARCHAR(60), 
	saldo NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_conta), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE dados_mei (
	id_dados SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	cnpj VARCHAR(18), 
	nome_fantasia VARCHAR(100), 
	tipo_atividade VARCHAR(10) NOT NULL, 
	categoria VARCHAR(15) NOT NULL, 
	cnae VARCHAR(10) NOT NULL, 
	data_abertura DATE NOT NULL, 
	cidade VARCHAR(80), 
	uf VARCHAR(2), 
	PRIMARY KEY (id_dados), 
	CONSTRAINT ck_mei_atividade CHECK (tipo_atividade IN ('COMERCIO', 'SERVICO', 'AMBOS')), 
	CONSTRAINT ck_mei_categoria CHECK (categoria IN ('PADRAO', 'CAMINHONEIRO')), 
	UNIQUE (id_usuario), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE fluxos_caixa (
	id_fluxo_caixa SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	saldo_inicial NUMERIC(12, 2) NOT NULL, 
	total_entradas NUMERIC(12, 2) NOT NULL, 
	total_saidas NUMERIC(12, 2) NOT NULL, 
	saldo_final NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_fluxo_caixa), 
	CONSTRAINT uq_fluxo_periodo UNIQUE (id_usuario, ano, mes), 
	CONSTRAINT ck_fluxo_mes CHECK (mes BETWEEN 1 AND 12), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE impostos (
	id_imposto SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(40) NOT NULL, 
	descricao TEXT, 
	periodicidade VARCHAR(10) NOT NULL, 
	valor_estimado NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_imposto), 
	CONSTRAINT uq_imposto_usuario_nome UNIQUE (id_usuario, nome), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE logs_admin (
	id_log SERIAL NOT NULL, 
	id_admin INTEGER NOT NULL, 
	acao VARCHAR(120) NOT NULL, 
	alvo VARCHAR(80), 
	data_hora TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_log), 
	FOREIGN KEY(id_admin) REFERENCES usuarios (id_usuario)
);

CREATE TABLE metas_financeiras (
	id_meta SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(80) NOT NULL, 
	descricao TEXT, 
	valor_objetivo NUMERIC(12, 2) NOT NULL, 
	valor_atual NUMERIC(12, 2) NOT NULL, 
	prazo DATE NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	PRIMARY KEY (id_meta), 
	CONSTRAINT ck_meta_valores CHECK (valor_objetivo > 0 AND valor_atual >= 0), 
	CONSTRAINT ck_meta_status CHECK (status IN ('ATIVA', 'CONCLUIDA', 'CANCELADA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE notificacoes (
	id_notificacao SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	chave VARCHAR(80) NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	mensagem VARCHAR(200) NOT NULL, 
	lida BOOLEAN NOT NULL, 
	data_criacao TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_notificacao), 
	CONSTRAINT uq_notificacao_chave UNIQUE (id_usuario, chave), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE preferencias_usuario (
	id_usuario INTEGER NOT NULL, 
	tema VARCHAR(10) NOT NULL, 
	notif_das BOOLEAN NOT NULL, 
	notif_dasn BOOLEAN NOT NULL, 
	notif_saldo BOOLEAN NOT NULL, 
	notif_teto BOOLEAN NOT NULL, 
	notif_fatura BOOLEAN NOT NULL, 
	saldo_minimo NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_usuario), 
	CONSTRAINT ck_pref_tema CHECK (tema IN ('ESCURO', 'CLARO', 'SISTEMA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE propostas_investimento (
	id_proposta SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(80) NOT NULL, 
	descricao TEXT, 
	valor_sugerido NUMERIC(12, 2) NOT NULL, 
	risco VARCHAR(15) NOT NULL, 
	rentabilidade_estimada NUMERIC(7, 2), 
	status VARCHAR(12) NOT NULL, 
	data_criacao TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_proposta), 
	CONSTRAINT ck_prop_status CHECK (status IN ('DISPONIVEL', 'ACEITA', 'RECUSADA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE reservas_estabilizacao (
	id_reserva SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	saldo NUMERIC(12, 2) NOT NULL, 
	data_atualizacao TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_reserva), 
	CONSTRAINT ck_reserva_saldo CHECK (saldo >= 0), 
	UNIQUE (id_usuario), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE retiradas_mensais (
	id_retirada SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	valor_desejado NUMERIC(12, 2) NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	PRIMARY KEY (id_retirada), 
	CONSTRAINT uq_retirada_periodo UNIQUE (id_usuario, ano, mes), 
	CONSTRAINT ck_retirada_status CHECK (status IN ('PLANEJADA', 'REALIZADA', 'CANCELADA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE servicos (
	id_servico SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	descricao TEXT, 
	horas_trabalho NUMERIC(7, 2) NOT NULL, 
	custo_materiais NUMERIC(12, 2) NOT NULL, 
	outros_custos NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_servico), 
	CONSTRAINT ck_servico_horas CHECK (horas_trabalho > 0), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE faturas (
	id_fatura SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_cliente INTEGER NOT NULL, 
	descricao VARCHAR(150) NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	data_emissao DATE NOT NULL, 
	data_vencimento DATE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	nota_obrigatoria BOOLEAN NOT NULL, 
	nota_solicitada BOOLEAN NOT NULL, 
	nota_emitida BOOLEAN NOT NULL, 
	data_pagamento DATE, 
	PRIMARY KEY (id_fatura), 
	CONSTRAINT ck_fatura_valor CHECK (valor > 0), 
	CONSTRAINT ck_fatura_status CHECK (status IN ('PENDENTE', 'PAGA', 'ATRASADA')), 
	CONSTRAINT ck_fatura_datas CHECK (data_vencimento >= data_emissao), 
	CONSTRAINT uq_fatura_duplicada UNIQUE (id_cliente, valor, data_emissao), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_cliente) REFERENCES clientes (id_cliente)
);

CREATE TABLE investimentos (
	id_investimento SERIAL NOT NULL, 
	id_carteira INTEGER NOT NULL, 
	nome VARCHAR(80) NOT NULL, 
	tipo VARCHAR(15) NOT NULL, 
	valor_atual NUMERIC(12, 2) NOT NULL, 
	rentabilidade NUMERIC(7, 2) NOT NULL, 
	prazo VARCHAR(30), 
	data_aplicacao DATE NOT NULL, 
	PRIMARY KEY (id_investimento), 
	CONSTRAINT ck_inv_tipo CHECK (tipo IN ('RENDA_FIXA', 'RENDA_VARIAVEL', 'FUNDOS', 'TESOURO', 'OUTROS')), 
	CONSTRAINT ck_inv_valor CHECK (valor_atual > 0), 
	FOREIGN KEY(id_carteira) REFERENCES carteiras_investimentos (id_carteira) ON DELETE CASCADE
);

CREATE TABLE movimentos_reserva (
	id_movimento SERIAL NOT NULL, 
	id_reserva INTEGER NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	saldo_apos NUMERIC(12, 2) NOT NULL, 
	descricao VARCHAR(150) NOT NULL, 
	data_hora TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_movimento), 
	CONSTRAINT ck_mov_tipo CHECK (tipo IN ('APORTE', 'RETIRADA')), 
	CONSTRAINT ck_mov_valor CHECK (valor > 0), 
	FOREIGN KEY(id_reserva) REFERENCES reservas_estabilizacao (id_reserva) ON DELETE CASCADE, 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE obrigacoes_imposto (
	id_obrigacao SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_imposto INTEGER NOT NULL, 
	descricao VARCHAR(80) NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	data_vencimento DATE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id_obrigacao), 
	CONSTRAINT uq_obrigacao UNIQUE (id_usuario, descricao), 
	CONSTRAINT ck_obrig_status CHECK (status IN ('PENDENTE', 'PAGO', 'ATRASADO')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_imposto) REFERENCES impostos (id_imposto) ON DELETE CASCADE
);

CREATE TABLE pagamentos (
	id_pagamento SERIAL NOT NULL, 
	id_assinatura INTEGER NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	data_pagamento DATE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	metodo VARCHAR(15) NOT NULL, 
	PRIMARY KEY (id_pagamento), 
	CONSTRAINT ck_pag_status CHECK (status IN ('PAGO', 'PENDENTE', 'FALHOU')), 
	FOREIGN KEY(id_assinatura) REFERENCES assinaturas (id_assinatura) ON DELETE CASCADE
);

CREATE TABLE precificacoes (
	id_precificacao SERIAL NOT NULL, 
	id_servico INTEGER NOT NULL, 
	margem_lucro NUMERIC(5, 2) NOT NULL, 
	custo_hora NUMERIC(12, 2) NOT NULL, 
	servicos_por_mes INTEGER NOT NULL, 
	valor_custo NUMERIC(12, 2) NOT NULL, 
	valor_sugerido NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_precificacao), 
	CONSTRAINT ck_preco_margem CHECK (margem_lucro >= 0 AND margem_lucro < 100), 
	UNIQUE (id_servico), 
	FOREIGN KEY(id_servico) REFERENCES servicos (id_servico) ON DELETE CASCADE
);

CREATE TABLE reservas_imposto (
	id_reserva_imposto SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_imposto INTEGER NOT NULL, 
	valor_reservado NUMERIC(12, 2) NOT NULL, 
	percentual_reserva NUMERIC(5, 2) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	data_atualizacao TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_reserva_imposto), 
	CONSTRAINT uq_reserva_imposto UNIQUE (id_usuario, id_imposto), 
	CONSTRAINT ck_resimp_status CHECK (status IN ('ATIVA', 'UTILIZADA', 'FINALIZADA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_imposto) REFERENCES impostos (id_imposto) ON DELETE CASCADE
);

CREATE TABLE transacoes (
	id_transacao SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_conta INTEGER NOT NULL, 
	id_categoria INTEGER NOT NULL, 
	descricao VARCHAR(150) NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	data DATE NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	ligada_atividade BOOLEAN NOT NULL, 
	PRIMARY KEY (id_transacao), 
	CONSTRAINT ck_transacao_valor CHECK (valor > 0), 
	CONSTRAINT ck_transacao_tipo CHECK (tipo IN ('ENTRADA', 'SAIDA')), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_conta) REFERENCES contas (id_conta), 
	FOREIGN KEY(id_categoria) REFERENCES categorias (id_categoria)
);

CREATE INDEX ix_transacoes_usuario_data ON transacoes (id_usuario, data);

CREATE TABLE faturamentos_mei (
	id_faturamento SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_transacao INTEGER, 
	ano INTEGER NOT NULL, 
	data DATE NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id_faturamento), 
	CONSTRAINT ck_fat_valor CHECK (valor > 0), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	UNIQUE (id_transacao), 
	FOREIGN KEY(id_transacao) REFERENCES transacoes (id_transacao) ON DELETE CASCADE
);
