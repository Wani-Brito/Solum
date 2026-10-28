from datetime import date, datetime
import os
import re
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Date, DateTime, DECIMAL, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=8)


# --- CONFIGURAÇÃO DE CRIPTOGRAFIA DE PALAVRAS-PASSE ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash seguro da palavra-passe."""
    return pwd_context.hash(senha)


def verificar_senha(senha_informada: str, senha_hash: str) -> bool:
    """Verifica se a palavra-passe informada corresponde ao hash guardado."""
    return pwd_context.verify(senha_informada, senha_hash)


# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///./solum.db"

engine_kwargs = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(
    title="Solum Backend",
    description="Backend do sistema Solum para gestão financeira, impostos e investimentos.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# --- 2. MODELOS SQLALCHEMY (Espelho exato de todas as tabelas do banco) ---

class UsuarioModel(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    senha = Column(String(255), nullable=False)
    telefone = Column(String(20))
    tipo_usuario = Column(String(50), nullable=False)  # 'AUTONOMO', 'FREELANCER', 'MEI'
    data_cadastro = Column(DateTime, default=datetime.utcnow)

class ContaModel(Base):
    __tablename__ = "contas"
    id_conta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(100), nullable=False)
    banco = Column(String(100))
    saldo = Column(DECIMAL(12, 2), default=0.00)

class CategoriaModel(Base):
    __tablename__ = "categorias"
    id_categoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'ENTRADA', 'SAIDA'

class TransacaoModel(Base):
    __tablename__ = "transacoes"
    id_transacao = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_conta = Column(Integer, ForeignKey("contas.id_conta"), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categorias.id_categoria"), nullable=False)
    descricao = Column(String(255), nullable=False)
    valor = Column(DECIMAL(12, 2), nullable=False)
    data_transacao = Column(Date, nullable=False)
    tipo = Column(String(20), nullable=False)  # 'ENTRADA', 'SAIDA'
class UsuarioRegistroRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    telefone: Optional[str] = None
    tipo_usuario: str  # 'NORMAL', 'PREMIUM', 'MEI'

class FluxoCaixaModel(Base):
    __tablename__ = "fluxos_caixa"
    id_fluxo_caixa = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    saldo_inicial = Column(DECIMAL(12, 2), default=0.00)
    total_entradas = Column(DECIMAL(12, 2), default=0.00)
    total_saidas = Column(DECIMAL(12, 2), default=0.00)
    saldo_final = Column(DECIMAL(12, 2), default=0.00)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/auth/login")
def login_utilizador(dados: LoginRequest, db: Session = Depends(get_db)):
    """Autentica o utilizador verificando a palavra-passe armazenada."""
    utilizador = db.query(UsuarioModel).filter(UsuarioModel.email == dados.email).first()

    if not utilizador or not verificar_senha(dados.senha, utilizador.senha):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas. E-mail ou palavra-passe incorretos."
        )

    return {
        "mensagem": "Login efetuado com sucesso!",
        "id_usuario": utilizador.id_usuario,
        "nome": utilizador.nome,
        "tipo_usuario": utilizador.tipo_usuario
    }


@app.post("/auth/registar", status_code=201)
def registar_utilizador(dados: UsuarioRegistroRequest, db: Session = Depends(get_db)):
    """Regista um novo utilizador guardando a palavra-passe como hash."""
    utilizador_existente = db.query(UsuarioModel).filter(UsuarioModel.email == dados.email).first()
    if utilizador_existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está registado no sistema.")

    novo_utilizador = UsuarioModel(
        nome=dados.nome,
        email=dados.email,
        senha=hash_senha(dados.senha),
        telefone=dados.telefone,
        tipo_usuario=dados.tipo_usuario.upper()
    )

    db.add(novo_utilizador)
    db.commit()
    db.refresh(novo_utilizador)

    return {
        "mensagem": "Utilizador registado com sucesso com segurança de criptografia!",
        "id_usuario": novo_utilizador.id_usuario,
        "email": novo_utilizador.email
    }


# --- ROTA PARA CONSULTA DO HISTÓRICO DE FLUXOS DE CAIXA ---

@app.get("/negocio/fluxo-caixa/historico/{id_usuario}")
def obter_historico_fluxo_caixa(id_usuario: int, db: Session = Depends(get_db)):
    """
    Retorna o histórico cronológico de todos os meses consolidados 
    do usuário, exibindo a evolução do saldo acumulado.
    """
    historico = db.query(FluxoCaixaModel).filter(
        FluxoCaixaModel.id_usuario == id_usuario
    ).order_by(FluxoCaixaModel.ano.asc(), FluxoCaixaModel.mes.asc()).all()

    if not historico:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum histórico de fluxo de caixa encontrado para este usuário."
        )

    resultado = []
    for f in historico:
        resultado.append({
            "periodo": f"{f.mes:02d}/{f.ano}",
            "saldo_inicial": float(f.saldo_inicial),
            "total_entradas": float(f.total_entradas),
            "total_saidas": float(f.total_saidas),
            "saldo_final_acumulado": float(f.saldo_final)
        })

    return {
        "id_usuario": id_usuario,
        "total_meses_registrados": len(resultado),
        "evolucao_caixa": resultado
    }

class RetiradaMensalModel(Base):
    __tablename__ = "retiradas_mensais"
    id_retirada = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    valor = Column(DECIMAL(12, 2), nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    status = Column(String(30), default='PLANEJADA')  # 'PLANEJADA', 'REALIZADA', 'CANCELADA'

class ReservaEstabilizacaoModel(Base):
    __tablename__ = "reservas_estabilizacao"
    id_reserva = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    saldo = Column(DECIMAL(12, 2), default=0.00)
    percentual_meta = Column(DECIMAL(5, 2), default=0.00)
    data_atualizacao = Column(DateTime, default=datetime.utcnow)

class ConfiguracaoMeiModel(Base):
    __tablename__ = "configuracoes_mei"
    id_configuracao = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    ano = Column(Integer, nullable=False)
    teto_anual = Column(DECIMAL(12, 2), nullable=False)
    percentual_alerta = Column(DECIMAL(5, 2), default=80.00)

class FaturamentoMeiModel(Base):
    __tablename__ = "faturamentos_mei"
    id_faturamento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    data_faturamento = Column(Date, nullable=False)
    descricao = Column(String(255))
    valor = Column(DECIMAL(12, 2), nullable=False)

class ImpostoModel(Base):
    __tablename__ = "impostos"
    id_imposto = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    percentual = Column(DECIMAL(5, 2))
    periodicidade = Column(String(30))  # 'MENSAL', 'TRIMESTRAL', 'ANUAL', 'OUTRA'
    valor_estimado = Column(DECIMAL(12, 2))

class ReservaImpostoModel(Base):
    __tablename__ = "reservas_imposto"
    id_reserva_imposto = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_imposto = Column(Integer, ForeignKey("impostos.id_imposto"), nullable=False)
    valor_reservado = Column(DECIMAL(12, 2), default=0.00)
    percentual_reserva = Column(DECIMAL(5, 2))
    data_atualizacao = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), default='ATIVA')

class ObrigacaoImpostoModel(Base):
    __tablename__ = "obrigacoes_imposto"
    id_obrigacao = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_imposto = Column(Integer, ForeignKey("impostos.id_imposto"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255))
    data_vencimento = Column(Date, nullable=False)
    valor = Column(DECIMAL(12, 2))
    status = Column(String(30), default='PENDENTE')  # 'PENDENTE', 'PAGO', 'ATRASADO'

class ServicoModel(Base):
    __tablename__ = "servicos"
    id_servico = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    horas_trabalho = Column(DECIMAL(8, 2))
    custo_materiais = Column(DECIMAL(12, 2), default=0.00)
    outros_custos = Column(DECIMAL(12, 2), default=0.00)

class CarteiraInvestimentoModel(Base):
    __tablename__ = "carteiras_investimentos"
    id_carteira = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(100), default='Carteira principal')
    saldo_total = Column(DECIMAL(12, 2), default=0.00)
    rentabilidade_total = Column(DECIMAL(8, 2), default=0.00)

class InvestimentoModel(Base):
    __tablename__ = "investimentos"
    id_investimento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_carteira = Column(Integer, ForeignKey("carteiras_investimentos.id_carteira"), nullable=False)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(50), nullable=False)  # 'RENDA_FIXA', 'RENDA_VARIAVEL', etc.
    valor_investido = Column(DECIMAL(12, 2), nullable=False)
    valor_atual = Column(DECIMAL(12, 2))
    rentabilidade = Column(DECIMAL(8, 2))
    data_aplicacao = Column(Date)
    prazo = Column(String(100))

class PropostaInvestimentoModel(Base):
    __tablename__ = "propostas_investimento"
    id_proposta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    valor_sugerido = Column(DECIMAL(12, 2))
    risco = Column(String(50))
    prazo = Column(String(100))
    rentabilidade_estimada = Column(DECIMAL(8, 2))
    status = Column(String(30), default='DISPONIVEL')

class MetaFinanceiraModel(Base):
    __tablename__ = "metas_financeiras"
    id_meta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    valor_objetivo = Column(DECIMAL(12, 2), nullable=False)
    valor_atual = Column(DECIMAL(12, 2), default=0.00)
    prazo = Column(Date)
    status = Column(String(30), default='ATIVA')

# --- 3. SCHEMAS PYDANTIC (Validação de Entrada) ---
class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(..., min_length=8)
    telefone: Optional[str] = None
    tipo_usuario: str = Field(..., min_length=2, max_length=50)

class TransacaoCreate(BaseModel):
    id_usuario: int
    id_conta: int
    id_categoria: int
    descricao: str
    valor: float
    data_transacao: date
    tipo: str

class ServicoCreate(BaseModel):
    id_usuario: int
    nome: str
    descricao: Optional[str] = None
    horas_trabalho: float
    custo_materiais: float = 0.00
    outros_custos: float = 0.00

class SuavizacaoRequest(BaseModel):
    receita_mes_atual: float
    saldo_reserva_atual: float
    salario_sintetico_desejado: float
    tipo_usuario: str = "NORMAL"  # 'NORMAL' ou 'PREMIUM'

# --- 5. ROTAS DA API ---
@app.get("/")
def read_root():
    return {"message": "API do Solum funcionando corretamente!", "status": "online"}


@app.get("/health")
def health_check():
    return {"status": "ok", "database": DATABASE_URL}


@app.post("/usuarios/", status_code=201)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    email_normalizado = str(usuario.email).lower().strip()
    usuario_existente = db.query(UsuarioModel).filter(UsuarioModel.email == email_normalizado).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está registado no sistema.")

    db_usuario = UsuarioModel(
        nome=usuario.nome.strip(),
        email=email_normalizado,
        senha=hash_senha(usuario.senha),
        telefone=usuario.telefone,
        tipo_usuario=usuario.tipo_usuario.upper()
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return {"message": "Usuário criado com sucesso!", "id_usuario": db_usuario.id_usuario}

@app.post("/transacoes/", status_code=201)
def criar_transacao(transacao: TransacaoCreate, db: Session = Depends(get_db)):
    if transacao.valor <= 0:
        raise HTTPException(
            status_code=400, 
            detail="O valor não pode ser negativo ou zero (Regra de Integridade)[cite: 1]."
        )
    
    db_transacao = TransacaoModel(
        id_usuario=transacao.id_usuario,
        id_conta=transacao.id_conta,
        id_categoria=transacao.id_categoria,
        descricao=transacao.descricao,
        valor=transacao.valor,
        data_transacao=transacao.data_transacao,
        tipo=transacao.tipo.upper()
    )
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return {"message": "Transação registada com sucesso!", "id_transacao": db_transacao.id_transacao}

@app.post("/servicos/", status_code=201)
def criar_servico(servico: ServicoCreate, db: Session = Depends(get_db)):
    db_servico = ServicoModel(
        id_usuario=servico.id_usuario,
        nome=servico.nome,
        descricao=servico.descricao,
        horas_trabalho=servico.horas_trabalho,
        custo_materiais=servico.custo_materiais,
        outros_custos=servico.outros_custos
    )
    db.add(db_servico)
    db.commit()
    db.refresh(db_servico)
    return {"message": "Serviço registado com sucesso!", "id_servico": db_servico.id_servico}

@app.post("/negocio/suavizacao-renda")
def calcular_suavizacao_renda(dados: SuavizacaoRequest):
    """
    Suavização de renda com regra de transbordo para investimentos se o excedente 
    ultrapassar 20% do salário base (Exclusivo para utilizadores Premium)[cite: 1].
    """
    receita = dados.receita_mes_atual
    saldo_reserva = dados.saldo_reserva_atual
    salario_alvo = dados.salario_sintetico_desejado
    tipo_usuario = dados.tipo_usuario.upper()
    
    valor_para_investimento = 0.00
    mensagem_investimento = ""

    if receita >= salario_alvo:
        excedente = receita - salario_alvo
        novo_saldo_reserva = saldo_reserva + excedente
        valor_retirado = salario_alvo
        mensagem = f"Receita superior ao salário. Excedente de R$ {excedente:.2f} enviado para a reserva de estabilização."
        
        limite_excedente_reserva = salario_alvo * 0.20
        if excedente > limite_excedente_reserva:
            valor_para_investimento = excedente - limite_excedente_reserva
            novo_saldo_reserva = novo_saldo_reserva - valor_para_investimento
            
            if tipo_usuario == "PREMIUM":
                mensagem_investimento = f"Perfil Premium: O excedente ultrapassou 20% do salário base. Valor de R$ {valor_para_investimento:.2f} direcionado para a carteira de investimentos."
            else:
                mensagem_investimento = f"Aviso: O excedente ultrapassou 20% do salário base, mas a indicação de investimentos é exclusiva para utilizadores Premium[cite: 1]."
    else:
        deficit = salario_alvo - receita
        if saldo_reserva >= deficit:
            novo_saldo_reserva = saldo_reserva - deficit
            valor_retirado = salario_alvo
            mensagem = f"Receita inferior ao salário. R$ {deficit:.2f} retirados da reserva para completar o salário sintético."
        else:
            valor_retirado = receita + saldo_reserva
            novo_saldo_reserva = 0.00
            mensagem = f"Aviso: Reserva insuficiente para completar o salário. Valor real disponível para retirada: R$ {valor_retirado:.2f}."

    return {
        "salario_sintetico_efetivo": round(valor_retirado, 2),
        "novo_saldo_reserva": round(novo_saldo_reserva, 2),
        "valor_enviado_investimentos": round(valor_para_investimento, 2) if tipo_usuario == "PREMIUM" else 0.00,
        "detalhe_regra": mensagem,
        "detalhe_investimento": mensagem_investimento
    }
# --- ROTA EXCLUSIVA PREMIUM: Simulação de Recomendações de Investimento ---
class RecomendacaoInvestimentoRequest(BaseModel):
    id_usuario: int
    tipo_usuario: str  # 'NORMAL' ou 'PREMIUM'
    valor_disponivel: float
    perfil_risco: str  # 'CONSERVADOR', 'MODERADO', 'ARROJADO'

@app.post("/negocio/investimentos/recomendacao")
def recomendar_investimento(dados: RecomendacaoInvestimentoRequest):
    """
    Regra de Negócio: Funcionalidade de indicação de investimentos avançados.
    Se o utilizador for 'NORMAL', o sistema bloqueia e sugere o upgrade.
    Se for 'PREMIUM', calcula opções com base no perfil de risco.
    """
    tipo = dados.tipo_usuario.upper()
    
    if tipo != "PREMIUM":
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado: A recomendação automatizada de investimentos é um recurso exclusivo para assinantes Premium do Solum."
        )
    
    valor = dados.valor_disponivel
    risco = dados.perfil_risco.upper()
    
    # Lógica de recomendação baseada no risco
    if risco == "CONSERVADOR":
        sugestao = {
            "produto": "Tesouro Selic / CDB Liquidez Diária",
            "rentabilidade_estimada_aa": "10.5% ao ano",
            "valor_alocado": valor,
            "descricao": "Ideal para proteger o excedente da sua reserva de estabilização com liquidez imediata."
        }
    elif risco == "MODERADO":
        sugestao = {
            "produto": "Fundos Multimercado / LCI & LCA",
            "rentabilidade_estimada_aa": "12.0% ao ano",
            "valor_alocado": valor,
            "descricao": "Equilíbrio entre renda fixa e ativos moderados para impulsionar o seu capital."
        }
    elif risco == "ARROJADO":
        sugestao = {
            "produto": "ETFs Globais / Ações Selecionadas",
            "rentabilidade_estimada_aa": "15.0%+ ao ano (Variável)",
            "valor_alocado": valor,
            "descricao": "Para quem busca maior crescimento de patrimônio a longo prazo e tolera oscilações."
        }
    else:
        raise HTTPException(status_code=400, detail="Perfil de risco inválido. Utilize 'CONSERVADOR', 'MODERADO' ou 'ARROJADO'.")

    return {
        "status": "Sucesso",
        "usuario_tipo": "PREMIUM",
        "recomendacao": sugestao
    }

# --- SCHEMAS E ROTAS PARA RESERVA/COTA MENSAL DE IMPOSTO ---

class CotaImpostoRequest(BaseModel):
    id_usuario: int
    faturamento_mes: float
    atividade: str  # 'COMERCIO', 'SERVICO' ou 'AMBOS'
    outros_impostos_estimados: Optional[float] = 0.00  # Caso tenha impostos extras/carne leão/retenções

@app.post("/negocio/cota-imposto-mensal")
def calcular_cota_imposto_mensal(dados: CotaImpostoRequest, db: Session = Depends(get_db)):
    """
    Calcula e separa do faturamento do mês o valor necessário para o pagamento dos impostos (DAS-MEI + extras).
    Atualiza ou sugere o valor a ser depositado na Reserva de Imposto.
    """
    if dados.faturamento_mes < 0:
        raise HTTPException(status_code=400, detail="O faturamento do mês não pode ser negativo.")

    # 1. Cálculo da cota DAS-MEI oficial
    inss = 81.05
    icms = 1.00
    iss = 5.00
    
    atividade_upper = dados.atividade.upper()
    if atividade_upper == "COMERCIO":
        das_valor = inss + icms
    elif atividade_upper == "SERVICO":
        das_valor = inss + iss
    elif atividade_upper == "AMBOS":
        das_valor = inss + icms + iss
    else:
        raise HTTPException(
            status_code=400, 
            detail="Atividade inválida. Escolha entre: 'COMERCIO', 'SERVICO' ou 'AMBOS'."
        )

    # 2. Total da Cota de Imposto do Mês
    total_imposto_mes = das_valor + dados.outros_impostos_estimados
    
    # 3. Percentual do Faturamento Bruto comprometido com imposto
    percentual_comprometido = 0.0
    if dados.faturamento_mes > 0:
        percentual_comprometido = (total_imposto_mes / dados.faturamento_mes) * 100

    # 4. Cálculo do Faturamento Líquido (Livre de imposto)
    faturamento_liquido = max(0.00, dados.faturamento_mes - total_imposto_mes)

    # 5. Salva/Atualiza o registro na tabela de Reservas de Imposto (se existir usuário no banco)
    reserva_db = db.query(ReservaImpostoModel).filter(ReservaImpostoModel.id_usuario == dados.id_usuario).first()
    
    if reserva_db:
        reserva_db.valor_reservado += total_imposto_mes
        reserva_db.percentual_reserva = round(percentual_comprometido, 2)
        reserva_db.data_atualizacao = datetime.utcnow()
        db.commit()
    
    return {
        "faturamento_bruto_mes": round(dados.faturamento_mes, 2),
        "cota_das_mei": round(das_valor, 2),
        "outros_impostos": round(dados.outros_impostos_estimados, 2),
        "total_cota_imposto_separar": round(total_imposto_mes, 2),
        "faturamento_liquido_disponivel": round(faturamento_liquido, 2),
        "percentual_faturamento_reservado": round(percentual_comprometido, 2),
        "orientacao": f"Separe exatamente R$ {total_imposto_mes:.2f} do seu faturamento em uma conta/reserva exclusiva para impostos."
    }
class MensagemChatbotRequest(BaseModel):
    id_usuario: int
    id_conta: int
    id_categoria_padrao: int
    mensagem: str  # Ex: "Gastei 150 com internet" ou "Recebi 500 do projeto"

@app.post("/chatbot/registrar-transacao")
def processar_mensagem_chatbot(dados: MensagemChatbotRequest, db: Session = Depends(get_db)):
    """
    Endpoint de Chatbot: Converte linguagem natural simples em lançamentos financeiros
    que alimentam o fluxo de caixa acumulativo do usuário.
    """
    texto = dados.mensagem.lower()
    
    # 1. Identifica a intenção (ENTRADA ou SAIDA)
    se_saida = any(palavra in texto for palavra in ["gastei", "paguei", "comprei", "saida", "despesa", "custo"])
    se_entrada = any(palavra in texto for palavra in ["recebi", "ganhei", "vendi", "entrada", "faturei", "pix"])
    
    if se_saida:
        tipo_transacao = "SAIDA"
    elif se_entrada:
        tipo_transacao = "ENTRADA"
    else:
        raise HTTPException(
            status_code=400, 
            detail="Não foi possível identificar se é um recebimento ou gasto. Tente usar termos como 'Recebi' ou 'Gastei'."
        )

    # 2. Extrai o primeiro número/valor encontrado no texto
    numeros = re.findall(r'\d+(?:[\.,]\d+)?', texto.replace(',', '.'))
    if not numeros:
        raise HTTPException(status_code=400, detail="Nenhum valor numérico foi encontrado na mensagem.")
    
    valor_extraido = float(numeros[0])
    if valor_extraido <= 0:
        raise HTTPException(status_code=400, detail="O valor da transação deve ser maior que zero.")

    # 3. Cria a transação automaticamente na tabela oficial
    nova_transacao = TransacaoModel(
        id_usuario=dados.id_usuario,
        id_conta=dados.id_conta,
        id_categoria=dados.id_categoria_padrao,
        descricao=f"[Chatbot] {dados.mensagem.strip()}",
        valor=valor_extraido,
        data_transacao=date.today(),
        tipo=tipo_transacao
    )
    
    db.add(nova_transacao)
    db.commit()
    db.refresh(nova_transacao)

    return {
        "status": "Transação registrada com sucesso via Chatbot",
        "tipo_identificado": tipo_transacao,
        "valor_registrado": round(valor_extraido, 2),
        "data": nova_transacao.data_transacao,
        "mensagem_retorno_bot": f"Anotado! Registrei uma {tipo_transacao} de R$ {valor_extraido:.2f} no seu saldo de {nova_transacao.data_transacao.strftime('%m/%Y')}."
    }
# --- SCHEMAS E ROTAS PARA METAS FINANCEIRAS ---

class MetaCreate(BaseModel):
    id_usuario: int
    nome: str
    descricao: Optional[str] = None
    valor_objetivo: float
    prazo: date

class MetaAporteRequest(BaseModel):
    id_meta: int
    valor_aporte: float

@app.post("/metas/", status_code=201)
def criar_meta(meta: MetaCreate, db: Session = Depends(get_db)):
    if meta.valor_objetivo <= 0:
        raise HTTPException(status_code=400, detail="O valor objetivo da meta deve ser maior que zero.")

    db_meta = MetaFinanceiraModel(
        id_usuario=meta.id_usuario,
        nome=meta.nome,
        descricao=meta.descricao,
        valor_objetivo=meta.valor_objetivo,
        valor_atual=0.00,
        prazo=meta.prazo,
        status="ATIVA"
    )
    db.add(db_meta)
    db.commit()
    db.refresh(db_meta)
    return {"message": "Meta financeira criada com sucesso!", "id_meta": db_meta.id_meta}

@app.post("/metas/aporte")
def realizar_aporte_meta(dados: MetaAporteRequest, db: Session = Depends(get_db)):
    """
    Registra um aporte de valor para uma meta financeira específica
    e calcula a porcentagem de conclusão.
    """
    meta = db.query(MetaFinanceiraModel).filter(
        MetaFinanceiraModel.id_meta == dados.id_meta
    ).first()

    if not meta:
        raise HTTPException(status_code=404, detail="Meta financeira não encontrada.")

    if dados.valor_aporte <= 0:
        raise HTTPException(status_code=400, detail="O valor do aporte deve ser superior a zero.")

    novo_valor_atual = float(meta.valor_atual) + dados.valor_aporte
    meta.valor_atual = novo_valor_atual

    # Verifica se atingiu ou ultrapassou a meta
    if novo_valor_atual >= float(meta.valor_objetivo):
        meta.status = "CONCLUIDA"

    db.commit()

    percentual_concluido = (novo_valor_atual / float(meta.valor_objetivo)) * 100

    return {
        "id_meta": meta.id_meta,
        "nome_meta": meta.nome,
        "valor_objetivo": float(meta.valor_objetivo),
        "valor_atualizado": round(novo_valor_atual, 2),
        "percentual_concluido": f"{min(percentual_concluido, 100.0):.2f}%",
        "status": meta.status
    }