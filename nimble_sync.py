import requests
import sqlite3
from database import DB_PATH

BASE_URL = "https://corporeosservicos191922.protheus.cloudtotvs.com.br:4050/rest01/api/v1/xnb002"

TOKEN = None


def headers(token=None):
    token_usado = token or TOKEN

    return {
        "Authorization": f"Bearer {token_usado}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get_catalogo(token=None):
    url = f"{BASE_URL}/catalogo?pagesize=999999"
    response = requests.get(url, headers=headers(token), timeout=30)
    response.raise_for_status()
    return response.json().get("items", [])


def get_armazens(token=None):
    url = f"{BASE_URL}/armazem?PageSize=999999"
    response = requests.get(url, headers=headers(token), timeout=30)
    response.raise_for_status()
    return response.json().get("items", [])


def detectar_modelo(descricao: str):
    texto = descricao.upper()

    if "GL PRO" in texto or "GENTLELASE PRO" in texto:
        return "GL PRO"

    if "MGL" in texto or "GENTLEMAX" in texto:
        return "GENTLEMAX"

    if "VPYAG" in texto or "YAG" in texto:
        return "YAG"

    if "CANDELA" in texto:
        return "CANDELA"

    if "SIBERIAN" in texto:
        return "SIBERIAN"

    return "OUTROS"


def detectar_categoria(descricao: str):
    texto = descricao.upper()

    if "PLACA" in texto or "PCB" in texto or "CPU" in texto:
        return "PLACA ELETRÔNICA"

    if "FONTE" in texto or "HVPS" in texto or "ALTA TENSAO" in texto:
        return "FONTE / ALTA TENSÃO"

    if "SENSOR" in texto:
        return "SENSOR"

    if "FILTRO" in texto:
        return "FILTRO"

    if "BOMBA" in texto:
        return "BOMBA"

    if "DCD" in texto or "VALVULA" in texto or "CRIO" in texto:
        return "DCD / CRIOGÊNIO"

    if "FIBRA" in texto:
        return "FIBRA"

    if "LENTE" in texto or "LENTES" in texto or "SAFIRA" in texto:
        return "LENTES / ÓPTICA"

    if "CABO" in texto:
        return "CABOS"

    if "CONECTOR" in texto or "UNIAO" in texto or "MANGUEIRA" in texto:
        return "CONEXÕES / MANGUEIRAS"

    if "AGUA" in texto:
        return "SISTEMA DE ÁGUA"

    return "GERAL"


def salvar_catalogo(pecas):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for peca in pecas:
        codigo = peca.get("produtocodigo", "")
        descricao = peca.get("produtodescricao", "")
        informacao = peca.get("produtoinformacao", "")
        imagem = peca.get("produtoimagem", "")

        conta_codigo = peca.get("contacodigo", "")
        conta_descricao = peca.get("contadescricao", "")

        modelo_detectado = detectar_modelo(descricao)
        categoria_detectada = detectar_categoria(descricao)

        cursor.execute("""
            INSERT OR REPLACE INTO pecas (
                codigo,
                descricao,
                informacao,
                imagem,
                conta_codigo,
                conta_descricao,
                modelo_detectado,
                categoria_detectada
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            descricao,
            informacao,
            imagem,
            conta_codigo,
            conta_descricao,
            modelo_detectado,
            categoria_detectada
        ))

    conn.commit()
    conn.close()


def salvar_armazens(armazens):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for arm in armazens:
        codigo = arm.get("armazemcodigo", "").strip()
        descricao = arm.get("armazemdescricao", "").strip()

        if codigo in ["", ",", "0,", "I", "I0"]:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO armazens (
                codigo,
                descricao
            )
            VALUES (?, ?)
        """, (
            codigo,
            descricao
        ))

    conn.commit()
    conn.close()


def sincronizar_dados(token):
    pecas = get_catalogo(token)
    salvar_catalogo(pecas)

    armazens = get_armazens(token)
    salvar_armazens(armazens)

    return {
        "pecas": len(pecas),
        "armazens": len(armazens)
    }


if __name__ == "__main__":
    print("Este arquivo agora precisa de token via login Nimble.")