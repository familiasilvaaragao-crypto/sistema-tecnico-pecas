import streamlit.components.v1 as components
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import base64
import textwrap
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

from database import DB_PATH
from nimble_auth import login_nimble
from nimble_sync import sincronizar_dados
from ia_diagnostico import analisar_problema

LOGO_PATH = "assets/logo.png"

def imagem_base64(caminho):
    with open(caminho, "rb") as img:
        return base64.b64encode(img.read()).decode()
st.set_page_config(
    page_title="A.S Tecnologia",
    page_icon="🔧",
    layout="wide"
)

st.markdown("""
<style>

/* MOBILE CONTAINER */

.main .block-container {

    max-width: 430px;

    padding-top: 1rem;

    padding-left: 1rem;

    padding-right: 1rem;

    margin: auto;
}

/* TITULOS */

h1 {
    font-size: 1.6rem !important;
}

h2 {
    font-size: 1.2rem !important;
}

/* CARDS */

div[data-testid="metric-container"] {

    border-radius: 22px !important;

    padding: 18px !important;

    background:
        linear-gradient(
            135deg,
            rgba(15,23,42,0.95),
            rgba(30,41,59,0.95)
        ) !important;

    border:
        1px solid rgba(59,130,246,0.18) !important;

    box-shadow:
        0 10px 30px rgba(0,0,0,0.35) !important;
}

/* BOTÕES */

.stButton > button {

    width: 100%;

    height: 52px;

    border-radius: 18px !important;

    font-weight: 800 !important;

    font-size: 1rem !important;
}

/* DATAFRAME */

[data-testid="stDataFrame"] {

    border-radius: 20px !important;

    overflow: hidden;
}

/* INPUTS */

input {

    border-radius: 16px !important;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)


if "logado" not in st.session_state:
    st.session_state.logado = False
if "token" not in st.session_state:
    st.session_state.token = None
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "perfil" not in st.session_state:
    st.session_state.perfil = None


def calcular_sla(df):
    df = df.copy()

    if df.empty:
        df["criado_em_dt"] = []
        df["horas_aberto"] = []
        df["sla_status"] = []
        df["horas_restantes"] = []
        return df
    agora = datetime.now()

    df["criado_em_dt"] = pd.to_datetime(df["criado_em"], errors="coerce")
    df["horas_aberto"] = df["criado_em_dt"].apply(
        lambda x: round((agora - x).total_seconds() / 3600, 1) if pd.notnull(x) else 0
    )

    df["sla_horas"] = df["sla_horas"].fillna(24).astype(int)

    df["sla_status"] = df.apply(
        lambda row: "FINALIZADO"
        if row["status"] in ["FINALIZADO", "ENTREGUE", "NEGADO"]
        else ("VENCIDO" if row["horas_aberto"] > row["sla_horas"] else "NO PRAZO"),
        axis=1
    )

    df["horas_restantes"] = df.apply(
        lambda row: 0
        if row["sla_status"] in ["FINALIZADO", "VENCIDO"]
        else round(row["sla_horas"] - row["horas_aberto"], 1),
        axis=1
    )

    return df


def carregar_dados():
    conn = sqlite3.connect(DB_PATH)

    pecas = pd.read_sql_query("""
        SELECT codigo, descricao, categoria_detectada, modelo_detectado,
               conta_descricao, estoque, estoque_minimo
        FROM pecas
        ORDER BY descricao
    """, conn)

    armazens = pd.read_sql_query("""
        SELECT codigo, descricao
        FROM armazens
        ORDER BY descricao
    """, conn)

    solicitacoes = pd.read_sql_query("""
        SELECT id, tecnico, maquina, serial, problema, prioridade, sla_horas,
               peca_codigo, quantidade, armazem_codigo, imagem, observacao,
               status, criado_em
        FROM solicitacoes
        ORDER BY id DESC
    """, conn)

    conn.close()

    solicitacoes = calcular_sla(solicitacoes)

    return pecas, armazens, solicitacoes


def salvar_solicitacao(
    tecnico,
    maquina,
    serial,
    problema,
    prioridade,
    sla_horas,
    peca_codigo,
    quantidade,
    armazem_codigo,
    imagem,
    observacao
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO solicitacoes (
            tecnico,
            maquina,
            serial,
            problema,
            prioridade,
            sla_horas,
            peca_codigo,
            quantidade,
            armazem_codigo,
            imagem,
            observacao,
            status,
            criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tecnico,
        maquina,
        serial,
        problema,
        prioridade,
        sla_horas,
        peca_codigo,
        quantidade,
        armazem_codigo,
        imagem,
        observacao,
        "PENDENTE",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def atualizar_status(solicitacao_id, novo_status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT peca_codigo, quantidade, status
        FROM solicitacoes
        WHERE id = ?
    """, (solicitacao_id,))

    resultado = cursor.fetchone()

    if resultado:
        peca_codigo, quantidade, status_atual = resultado

        if novo_status == "APROVADO" and status_atual != "APROVADO":
            cursor.execute("""
                SELECT estoque
                FROM pecas
                WHERE codigo = ?
            """, (peca_codigo,))

            estoque_result = cursor.fetchone()

            if estoque_result:
                estoque_atual = estoque_result[0]
                novo_estoque = max(estoque_atual - quantidade, 0)

                cursor.execute("""
                    UPDATE pecas
                    SET estoque = ?
                    WHERE codigo = ?
                """, (novo_estoque, peca_codigo))

    cursor.execute("""
        UPDATE solicitacoes
        SET status = ?
        WHERE id = ?
    """, (novo_status, solicitacao_id))

    conn.commit()
    conn.close()


def obter_perfil(usuario):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT perfil
        FROM usuarios
        WHERE usuario = ?
    """, (usuario,))

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return resultado[0]

    return "TECNICO"


def salvar_usuario(usuario, perfil):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO usuarios (usuario, perfil)
        VALUES (?, ?)
    """, (usuario, perfil))

    conn.commit()
    conn.close()


if not st.session_state.logado:

    logo_b64 = imagem_base64(LOGO_PATH)

    components.html(f"""
    <style>
    body {{
        margin: 0;
        font-family: Arial, sans-serif;
    }}

    .login-hero {{
        height: 520px;
        background: linear-gradient(135deg, #001b5e, #0057d9, #00a6ff);
        border-radius: 0 0 28px 28px;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .laser-main {{
        position: absolute;
        width: 130%;
        height: 7px;
        left: -15%;
        top: 62%;
        background: linear-gradient(90deg, transparent, #ffffff, #67e8f9, transparent);
        box-shadow: 0 0 22px #ffffff, 0 0 50px #22d3ee;
        transform: rotate(-18deg);
        animation: laserPulse 2.8s infinite ease-in-out;
    }}

    @keyframes laserPulse {{
        0%, 100% {{ opacity: .45; }}
        50% {{ opacity: 1; }}
    }}

    .login-card {{
        width: 480px;
        background: rgba(255,255,255,0.96);
        border-radius: 30px;
        padding: 35px;
        text-align: center;
        box-shadow: 0 25px 60px rgba(0,0,0,0.28);
        position: relative;
        z-index: 2;
    }}

    .login-logo {{
        width: 115px;
        margin-bottom: 10px;
    }}

    .login-title {{
        color: #003b9f;
        font-size: 32px;
        font-weight: 900;
    }}

    .login-subtitle {{
        color: #475569;
        font-size: 16px;
        margin-top: 8px;
        margin-bottom: 20px;
    }}

    .dev-text {{
        color: #0057d9;
        font-weight: 900;
        font-size: 16px;
    }}
    </style>

    <div class="login-hero">
        <div class="laser-main"></div>

        <div class="login-card">
            <img src="data:image/png;base64,{logo_b64}" class="login-logo">
            <div class="login-title">Sistema Técnico de Peças</div>
            <div class="login-subtitle">Gestão inteligente para manutenção laser</div>
            <div class="dev-text">Dev: A.S Tecnologia</div>
        </div>
    </div>
    """, height=540)

    usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
    senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")

    entrar = st.button("🔐 Entrar", use_container_width=True)

    if entrar:
        try:
            token = login_nimble(usuario, senha)

            st.session_state.token = token
            st.session_state.usuario = usuario
            st.session_state.perfil = obter_perfil(usuario)
            st.session_state.logado = True

            with st.spinner("Sincronizando dados do Nimble..."):
                resultado = sincronizar_dados(token)

            st.success(
                f"Login realizado com sucesso! "
                f"{resultado['pecas']} peças e {resultado['armazens']} armazéns sincronizados."
            )

            st.rerun()

        except Exception as e:
            st.error(f"Falha no login: {e}")

    st.stop()

pecas, armazens, solicitacoes = carregar_dados()

if "sla_status" not in solicitacoes.columns:
    solicitacoes = calcular_sla(solicitacoes)

col_logo, col_title, col_user = st.columns([1, 5, 1.5])

with col_logo:
    st.image(LOGO_PATH, width=105)

with col_title:

 st.markdown("""
<div class="header-box">

<h1>🔧 SISTEMA TÉCNICO DE PEÇAS</h1>

<p class="header-sub">
Gestão inteligente de manutenção, SLA e peças técnicas
</p>

<p class="header-sub">
Dev: A.S Tecnologia
</p>

</div>
""", unsafe_allow_html=True)

col_logo, col_user = st.columns([6,1])

with col_logo:
    st.image(LOGO_PATH, width=130)

with col_user:

    st.write("")

    st.write(f"👤 {st.session_state.usuario}")

    st.write(f"🔑 {st.session_state.perfil}")

    if st.button("Sair"):
        st.session_state.logado = False
        st.session_state.token = None
        st.session_state.usuario = None
        st.session_state.perfil = None
        st.rerun()


perfil = st.session_state.perfil

if perfil == "ADMIN":
    opcoes_menu = [
        "Dashboard",
        "Catálogo de Peças",
        "Controle de Estoque",
        "Solicitação Técnica",
        "Histórico de Solicitações",
        "Histórico por Serial",
        "Usuários"
    ]
elif perfil == "SUPERVISOR":
    opcoes_menu = [
        "Dashboard",
        "Catálogo de Peças",
        "Solicitação Técnica",
        "Histórico de Solicitações",
        "Histórico por Serial"
    ]
else:
    opcoes_menu = [
        "Catálogo de Peças",
        "Solicitação Técnica",
        "Histórico por Serial"
    ]

menu = st.sidebar.radio("Menu", opcoes_menu)


if menu == "Dashboard":
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

    with col1:
        st.metric("📦 Total de peças", len(pecas))

    with col2:
        st.metric("🏢 Armazéns", len(armazens))

    with col3:
        pendentes = solicitacoes[solicitacoes["status"] == "PENDENTE"].shape[0]
        st.metric("⏳ Pendentes", pendentes)

    with col4:
        st.metric("📝 Solicitações", len(solicitacoes))

    with col5:
        criticos = pecas[pecas["estoque"] <= pecas["estoque_minimo"]].shape[0]
        st.metric("⚠️ Estoque crítico", criticos)

    with col6:
        vencidos = solicitacoes[solicitacoes["sla_status"] == "VENCIDO"].shape[0]
        st.metric("🚨 SLA vencido", vencidos)
    
    with col7:
     media_horas = 0

    if len(solicitacoes) > 0:
        media_horas = round(
            solicitacoes["horas_aberto"].mean(),
            1
        )

    st.metric(
        "⏱ Média Horas",
        media_horas
    )

    with col8:
     percentual_sla = 0

    if len(solicitacoes) > 0:

        dentro_sla = solicitacoes[
            solicitacoes["sla_status"] == "NO PRAZO"
        ].shape[0]

        percentual_sla = round(
            (dentro_sla / len(solicitacoes)) * 100,
            1
        )

    st.metric(
        "📈 SLA OK %",
        f"{percentual_sla}%"
    )


    st.divider()

    colg1, colg2 = st.columns(2)

    with colg1:
        st.subheader("📊 Status das Solicitações")

        if len(solicitacoes) > 0:
            status_count = solicitacoes["status"].value_counts().reset_index()
            status_count.columns = ["Status", "Quantidade"]

            fig_status = px.pie(
                status_count,
                names="Status",
                values="Quantidade",
                hole=0.4
            )

            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Ainda não existem solicitações.")

    with colg2:
        st.subheader("🚨 Status SLA")

        if len(solicitacoes) > 0:
            sla_count = solicitacoes["sla_status"].value_counts().reset_index()
            sla_count.columns = ["SLA", "Quantidade"]

            fig_sla = px.bar(
                sla_count,
                x="SLA",
                y="Quantidade"
            )

            st.plotly_chart(fig_sla, use_container_width=True)
        else:
            st.info("Ainda não existem dados de SLA.")

    colg3, colg4 = st.columns(2)

    with colg3:
        st.subheader("📈 Problemas Mais Comuns")
    st.divider()

    st.subheader("🏆 Ranking Técnico")

    
    st.divider()

    st.subheader("🚨 Máquinas Mais Críticas")

    maquinas = (
    solicitacoes["serial"]
    .value_counts()
    .reset_index()
)

    maquinas.columns = [
    "Serial",
    "Chamados"
]

    fig_maq = px.bar(
    maquinas.head(10),
    x="Serial",
    y="Chamados"
)

    st.plotly_chart(
    fig_maq,
    use_container_width=True
)


    ranking = (
    solicitacoes["tecnico"]
    .value_counts()
    .reset_index()
)

    ranking.columns = [
    "Tecnico",
    "Chamados"
]

    fig_rank = px.bar(
    ranking,
    x="Tecnico",
    y="Chamados"
)

    st.plotly_chart(
    fig_rank,
    use_container_width=True
)



    if len(solicitacoes) > 0:
            problemas = solicitacoes["problema"].value_counts().head(10).reset_index()
            problemas.columns = ["Problema", "Quantidade"]

            fig_prob = px.bar(problemas, x="Problema", y="Quantidade")
            st.plotly_chart(fig_prob, use_container_width=True)
    else:
            st.info("Ainda não existem dados de problemas.")

    with colg4:
        st.subheader("⚠️ Estoque Crítico")

        estoque_critico = pecas[pecas["estoque"] <= pecas["estoque_minimo"]]

        if len(estoque_critico) > 0:
            fig_est = px.bar(
                estoque_critico.head(10),
                x="codigo",
                y="estoque",
                hover_data=["descricao", "estoque_minimo"]
            )

            st.plotly_chart(fig_est, use_container_width=True)
        else:
            st.success("Nenhum item crítico.")

    st.divider()

    st.subheader("🚨 Chamados com SLA Vencido")

sla_vencido = solicitacoes[
    solicitacoes["sla_status"] == "VENCIDO"
]

if len(sla_vencido) > 0:

    st.error(
        f"Existem {len(sla_vencido)} chamados com SLA vencido!"
    )

    criticos = sla_vencido[
        sla_vencido["prioridade"] == "CRITICA"
    ].shape[0]

    altos = sla_vencido[
        sla_vencido["prioridade"] == "ALTA"
    ].shape[0]

    col_sla1, col_sla2 = st.columns(2)

    with col_sla1:
        st.metric(
            "🚨 Criticidade Alta",
            criticos
        )

    with col_sla2:
        st.metric(
            "⚠️ Prioridade Alta",
            altos
        )


    sla_vencido = solicitacoes[solicitacoes["sla_status"] == "VENCIDO"]

    if len(sla_vencido) > 0:
        st.dataframe(
            sla_vencido[
                [
                    "id",
                    "tecnico",
                    "maquina",
                    "serial",
                    "problema",
                    "prioridade",
                    "sla_horas",
                    "horas_aberto",
                    "status",
                    "criado_em"
                ]
            ],
            use_container_width=True,
            height=300
        )
    else:
        st.success("Nenhum chamado vencido.")

    st.divider()

    st.subheader("Últimas solicitações")

    st.dataframe(
        solicitacoes.head(10),
        use_container_width=True,
        height=400
    )


elif menu == "Catálogo de Peças":
    st.subheader("📋 Catálogo Técnico")

    colf1, colf2, colf3 = st.columns(3)

    with colf1:
        busca = st.text_input("🔎 Buscar peça", placeholder="Código, nome ou referência...")

    with colf2:
        modelos = ["TODOS"] + sorted(pecas["modelo_detectado"].dropna().unique().tolist())
        modelo = st.selectbox("🖥 Modelo", modelos)

    with colf3:
        categorias = ["TODAS"] + sorted(pecas["categoria_detectada"].dropna().unique().tolist())
        categoria = st.selectbox("🧩 Categoria", categorias)

    df = pecas.copy()

    if busca:
        df = df[
            df["descricao"].str.contains(busca, case=False, na=False)
            |
            df["codigo"].str.contains(busca, case=False, na=False)
        ]

    if modelo != "TODOS":
        df = df[df["modelo_detectado"] == modelo]

    if categoria != "TODAS":
        df = df[df["categoria_detectada"] == categoria]

    st.metric("Resultado da busca", len(df))
    st.dataframe(df, use_container_width=True, height=550)


elif menu == "Controle de Estoque":
    st.subheader("📦 Controle de Estoque")

    estoque_df = pecas.copy()

    col1, col2 = st.columns(2)

    with col1:
        busca_estoque = st.text_input("Buscar peça")

    with col2:
        somente_critico = st.checkbox("Mostrar apenas estoque crítico")

    if busca_estoque:
        estoque_df = estoque_df[
            estoque_df["descricao"].str.contains(busca_estoque, case=False, na=False)
            |
            estoque_df["codigo"].str.contains(busca_estoque, case=False, na=False)
        ]

    if somente_critico:
        estoque_df = estoque_df[estoque_df["estoque"] <= estoque_df["estoque_minimo"]]

    st.metric("Itens encontrados", len(estoque_df))
    st.dataframe(estoque_df, use_container_width=True, height=450)

    st.divider()
    st.subheader("➕ Atualizar Estoque")

    peca_estoque = st.selectbox(
        "Selecionar peça",
        [f"{row['codigo']} - {row['descricao']}" for _, row in pecas.iterrows()]
    )

    novo_estoque = st.number_input("Novo estoque", min_value=0, value=0, step=1)
    estoque_minimo = st.number_input("Estoque mínimo", min_value=0, value=1, step=1)

    if st.button("💾 Salvar Estoque"):
        codigo = peca_estoque.split(" - ")[0]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pecas
            SET estoque = ?, estoque_minimo = ?
            WHERE codigo = ?
        """, (novo_estoque, estoque_minimo, codigo))

        conn.commit()
        conn.close()

        st.success("Estoque atualizado!")
        st.rerun()


elif menu == "Solicitação Técnica":
    st.subheader("🛠️ Nova Solicitação Técnica")

    with st.form("form_solicitacao"):
        col1, col2 = st.columns(2)

        with col1:
            tecnico = st.text_input("Técnico", value=st.session_state.usuario)

            maquina = st.selectbox(
                "Máquina",
                ["GentleMax Pro", "GL Pro", "MGL", "VPYAG", "Siberian", "Outro"]
            )

            serial = st.text_input("Serial da máquina", placeholder="Ex: 903516771")

        with col2:
            problema = st.selectbox(
                "Problema / Sintoma",
                [
                    "Erro DCD",
                    "Erro Flow / Fluxo",
                    "Sem disparo",
                    "Erro temperatura",
                    "Falha de fonte HVPS",
                    "Falha no aplicador",
                    "Falha de sensor",
                    "Manutenção preventiva",
                    "Outro"
                ]
            )

            diagnostico = analisar_problema(problema)

            prioridade = diagnostico["prioridade"]
            sla_horas = diagnostico["sla"]

            st.divider()

            if prioridade == "CRITICA":
                st.error(f"🚨 Prioridade: {prioridade} | SLA: {sla_horas}h")
            elif prioridade == "ALTA":
                st.warning(f"⚠️ Prioridade: {prioridade} | SLA: {sla_horas}h")
            else:
                st.info(f"ℹ️ Prioridade: {prioridade} | SLA: {sla_horas}h")

            colia1, colia2 = st.columns(2)

            with colia1:
                st.subheader("🧠 Possíveis Causas")
                for causa in diagnostico["causas"]:
                    st.write(f"• {causa}")

            with colia2:
                st.subheader("🔧 Peças Sugeridas")
                for peca in diagnostico["pecas"]:
                    st.write(f"• {peca}")

            st.subheader("📋 Checklist Técnico")

            for item in diagnostico["checklist"]:
                st.checkbox(item, key=f"{problema}_{item}")

            quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)

            armazem_opcoes = [
                f"{row['codigo']} - {row['descricao']}"
                for _, row in armazens.iterrows()
            ]

            armazem_escolhido = st.selectbox("Armazém", armazem_opcoes)

        st.divider()
        st.markdown("### 🔎 Selecionar peça")

        busca_peca = st.text_input(
            "Buscar peça para solicitação",
            placeholder="Digite: sensor, bomba, placa, fonte..."
        )

        pecas_filtradas = pecas.copy()

        sugestoes = {
            "Erro DCD": ["DCD", "VALVULA", "CRIO", "GAS"],
            "Erro Flow / Fluxo": ["FLUXO", "BOMBA", "FILTRO", "AGUA", "SENSOR"],
            "Sem disparo": ["HVPS", "FONTE", "CAPACITOR", "PLACA", "SHUTTER"],
            "Erro temperatura": ["TEMPERATURA", "SENSOR", "VENTILADOR"],
            "Falha de fonte HVPS": ["HVPS", "FONTE", "ALTA TENSAO"],
            "Falha no aplicador": ["APLICADOR", "FIBRA", "LENTE"],
            "Falha de sensor": ["SENSOR", "PRESSAO", "FLUXO"],
            "Manutenção preventiva": ["FILTRO", "AGUA", "LENTE", "VEDACAO"]
        }

        if problema in sugestoes:
            termos = sugestoes[problema]
            filtro_auto = False

            for termo in termos:
                filtro_auto = filtro_auto | pecas_filtradas["descricao"].str.contains(
                    termo,
                    case=False,
                    na=False
                )

            pecas_filtradas = pecas_filtradas[filtro_auto]

        if busca_peca:
            pecas_filtradas = pecas[
                pecas["descricao"].str.contains(busca_peca, case=False, na=False)
                |
                pecas["codigo"].str.contains(busca_peca, case=False, na=False)
            ]

        st.info(f"Sugestões automáticas para: {problema}")

        peca_opcoes = [
            f"{row['codigo']} - {row['descricao']} | Estoque: {row['estoque']}"
            for _, row in pecas_filtradas.head(200).iterrows()
        ]

        if not peca_opcoes:
            st.warning("Nenhuma peça encontrada.")
            peca_escolhida = ""
        else:
            peca_escolhida = st.selectbox("Peça", peca_opcoes)

        st.divider()
        st.subheader("📷 Evidência Técnica")

        imagem = st.file_uploader("Upload da imagem", type=["png", "jpg", "jpeg"])

        observacao = st.text_area(
            "Observações técnicas",
            placeholder="Descreva detalhes do defeito..."
        )
        caminho_imagem = ""

        if imagem:
            os.makedirs("uploads", exist_ok=True)

            nome_arquivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{imagem.name}"
            caminho_imagem = os.path.join("uploads", nome_arquivo)

            with open(caminho_imagem, "wb") as f:
                f.write(imagem.getbuffer())

            st.image(caminho_imagem, width=300)

        enviar = st.form_submit_button("✅ Criar Solicitação")

        if enviar:
            if not tecnico or not serial or not peca_escolhida:
                st.error("Preencha técnico, serial e peça.")
            else:
                peca_codigo = peca_escolhida.split(" - ")[0]
                armazem_codigo = armazem_escolhido.split(" - ")[0]

                salvar_solicitacao(
                    tecnico,
                    maquina,
                    serial,
                    problema,
                    prioridade,
                    sla_horas,
                    peca_codigo,
                    quantidade,
                    armazem_codigo,
                    caminho_imagem,
                    observacao
                )

                st.success("Solicitação criada com sucesso!")


elif menu == "Histórico de Solicitações":
    st.subheader("📑 Histórico de Solicitações")

    filtro_status = st.selectbox(
        "Filtrar Status",
        [
            "TODOS",
            "PENDENTE",
            "EM ANALISE",
            "APROVADO",
            "SEPARADO",
            "ENTREGUE",
            "FINALIZADO",
            "NEGADO"
        ]
    )

    filtro_sla = st.selectbox(
        "Filtrar SLA",
        [
            "TODOS",
            "NO PRAZO",
            "VENCIDO",
            "FINALIZADO"
        ]
    )

    df_sol = solicitacoes.copy()

    if filtro_status != "TODOS":
        df_sol = df_sol[df_sol["status"] == filtro_status]

    if filtro_sla != "TODOS":
        df_sol = df_sol[df_sol["sla_status"] == filtro_sla]

    st.metric("Total", len(df_sol))

    st.dataframe(
        df_sol,
        use_container_width=True,
        height=420
    )

    col_export1, col_export2 = st.columns(2)

    with col_export1:
        excel_buffer = BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df_sol.to_excel(writer, index=False, sheet_name="Solicitacoes")

        st.download_button(
            label="📥 Exportar Excel",
            data=excel_buffer.getvalue(),
            file_name="solicitacoes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col_export2:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "Relatorio de Solicitacoes", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", size=10)

        for _, row in df_sol.head(30).iterrows():
            texto = (
                f"ID: {row['id']} | "
                f"Tecnico: {row['tecnico']} | "
                f"Problema: {row['problema']} | "
                f"Prioridade: {row['prioridade']} | "
                f"SLA: {row['sla_status']} | "
                f"Status: {row['status']}"
            )

            pdf.multi_cell(0, 8, texto)

        pdf_buffer = BytesIO()
        pdf_bytes = pdf.output(dest="S").encode("latin-1")
        pdf_buffer.write(pdf_bytes)

        st.download_button(
            label="📄 Exportar PDF",
            data=pdf_buffer.getvalue(),
            file_name="relatorio_solicitacoes.pdf",
            mime="application/pdf"
        )

    st.divider()
    st.subheader("📷 Evidências")

    for _, row in df_sol.iterrows():
        if row.get("imagem"):
            st.markdown(f"### Solicitação #{row['id']}")
            st.image(row["imagem"], width=300)

            if row.get("observacao"):
                st.write(row["observacao"])

            st.divider()

    if perfil in ["ADMIN", "SUPERVISOR"]:
        st.subheader("⚙️ Atualizar Status")

        if len(solicitacoes) > 0:
            ids = solicitacoes["id"].tolist()
            solicitacao_id = st.selectbox("Selecionar Solicitação", ids)

            novo_status = st.selectbox(
                "Novo Status",
                [
                    "PENDENTE",
                    "EM ANALISE",
                    "APROVADO",
                    "SEPARADO",
                    "ENTREGUE",
                    "FINALIZADO",
                    "NEGADO"
                ]
            )

            if st.button("💾 Atualizar Status"):
                atualizar_status(solicitacao_id, novo_status)
                st.success("Status atualizado com sucesso!")
                st.rerun()
        else:
            st.info("Ainda não existem solicitações cadastradas.")
    else:
        st.info("Seu perfil permite apenas consulta do histórico.")


elif menu == "Histórico por Serial":
    st.subheader("🖥️ Histórico Técnico da Máquina")

    serial_busca = st.text_input("Digite o serial da máquina", placeholder="Ex: 903516771")

    if serial_busca:
        historico = solicitacoes[
            solicitacoes["serial"].astype(str).str.contains(
                serial_busca,
                case=False,
                na=False
            )
        ]

        if len(historico) == 0:
            st.warning("Nenhum histórico encontrado.")
        else:
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Chamados", len(historico))
            with col2:
                st.metric("Máquina", historico.iloc[0]["maquina"])
            with col3:
                st.metric("Último Status", historico.iloc[0]["status"])
            with col4:
                st.metric("Última Manutenção", historico.iloc[0]["criado_em"])
            with col5:
                vencidos_serial = historico[historico["sla_status"] == "VENCIDO"].shape[0]
                st.metric("SLA vencido", vencidos_serial)

            st.divider()
            st.subheader("📑 Histórico Completo")
            st.dataframe(historico, use_container_width=True, height=450)

            st.divider()
            st.subheader("📈 Problemas Recorrentes")

            problemas = historico["problema"].value_counts().reset_index()
            problemas.columns = ["Problema", "Quantidade"]

            fig = px.bar(problemas, x="Problema", y="Quantidade")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("🔧 Peças Mais Utilizadas")

            pecas_usadas = historico["peca_codigo"].value_counts().reset_index()
            pecas_usadas.columns = ["Peça", "Quantidade"]

            st.dataframe(pecas_usadas, use_container_width=True)

            st.divider()
            st.subheader("📷 Evidências da Máquina")

            for _, row in historico.iterrows():
                if row.get("imagem"):
                    st.markdown(f"### Solicitação #{row['id']}")
                    st.image(row["imagem"], width=300)

                    if row.get("observacao"):
                        st.write(row["observacao"])

                    st.divider()


elif menu == "Usuários":
    st.subheader("👥 Gestão de Usuários")

    conn = sqlite3.connect(DB_PATH)

    usuarios_df = pd.read_sql_query("""
        SELECT usuario, perfil
        FROM usuarios
        ORDER BY usuario
    """, conn)

    conn.close()

    st.dataframe(usuarios_df, use_container_width=True, height=350)

    st.divider()
    st.subheader("➕ Adicionar / Alterar Usuário")

    usuario_novo = st.text_input("Usuário Nimble/TOTVS")

    perfil_novo = st.selectbox("Perfil", ["TECNICO", "SUPERVISOR", "ADMIN"])

    if st.button("💾 Salvar Usuário"):
        if not usuario_novo:
            st.error("Informe o usuário.")
        else:
            salvar_usuario(usuario_novo, perfil_novo)
            st.success("Usuário salvo com sucesso!")
            st.rerun()