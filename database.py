import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "pecas.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pecas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                descricao TEXT,
                informacao TEXT,
                imagem TEXT,
                conta_codigo TEXT,
                conta_descricao TEXT,
                modelo_detectado TEXT,
                categoria_detectada TEXT,
                estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS armazens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tecnico TEXT,
                maquina TEXT,
                serial TEXT,
                problema TEXT,
                prioridade TEXT,
                sla_horas INTEGER DEFAULT 24,
                peca_codigo TEXT,
                quantidade INTEGER,
                armazem_codigo TEXT,
                imagem TEXT,
                observacao TEXT,
                status TEXT DEFAULT 'PENDENTE',
                criado_em TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                perfil TEXT DEFAULT 'TECNICO'
            )
        """)

        conn.commit()


def atualizar_estrutura():
    conn = get_connection()
    cursor = conn.cursor()

    colunas_pecas = {
        "estoque": "INTEGER DEFAULT 0",
        "estoque_minimo": "INTEGER DEFAULT 1"
    }

    for coluna, tipo in colunas_pecas.items():
        try:
            cursor.execute(f"""
                ALTER TABLE pecas
                ADD COLUMN {coluna} {tipo}
            """)
        except:
            pass

    colunas_solicitacoes = {
        "imagem": "TEXT",
        "observacao": "TEXT",
        "prioridade": "TEXT",
        "sla_horas": "INTEGER DEFAULT 24"
    }

    for coluna, tipo in colunas_solicitacoes.items():
        try:
            cursor.execute(f"""
                ALTER TABLE solicitacoes
                ADD COLUMN {coluna} {tipo}
            """)
        except:
            pass

    conn.commit()
    conn.close()


def criar_admin_padrao():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (
            usuario,
            perfil
        )
        VALUES (?, ?)
    """, (
        "02855543282",
        "ADMIN"
    ))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    atualizar_estrutura()
    criar_admin_padrao()
    print("Banco atualizado com sucesso!")