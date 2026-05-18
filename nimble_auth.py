import requests
from urllib.parse import urlparse, parse_qs

LOGIN_URL = "https://corporeosservicos191922.protheus.cloudtotvs.com.br:4050/rest01/auth/login"


def login_nimble(usuario: str, senha: str):
    payload = {
        "user": usuario,
        "password": senha,
        "redirectUrl": "restPort",
        "restUrl": "a"
    }

    response = requests.post(
        LOGIN_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    texto = response.text.strip()

    parsed = urlparse(texto)
    params = parse_qs(parsed.query)

    token = params.get("token", [None])[0]

    if not token:
        raise Exception("Token não encontrado na resposta do Nimble")

    return token