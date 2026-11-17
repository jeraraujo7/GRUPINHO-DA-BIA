"""Envio para o grupo do WhatsApp pela Z-API (serviço não oficial).

Variáveis de ambiente (nunca no repositório):
  ZAPI_INSTANCE_ID, ZAPI_TOKEN   -> painel da Z-API, na instância conectada ao chip do grupo
  ZAPI_CLIENT_TOKEN              -> token de segurança da conta (aba Segurança)
  WHATSAPP_GRUPO_ID              -> id do grupo, ex.: 120363000000000000-group

Use um chip só para o grupo, nunca o número pessoal: há risco de bloqueio.
"""

from __future__ import annotations

import os

from .oferta import http_json

BASE = "https://api.z-api.io/instances/{inst}/token/{tok}"


def configurado() -> bool:
    return all(os.environ.get(v) for v in
               ("ZAPI_INSTANCE_ID", "ZAPI_TOKEN", "ZAPI_CLIENT_TOKEN", "WHATSAPP_GRUPO_ID"))


def _url(acao: str) -> str:
    return BASE.format(inst=os.environ["ZAPI_INSTANCE_ID"], tok=os.environ["ZAPI_TOKEN"]) + "/" + acao


def _cab() -> dict:
    return {"Client-Token": os.environ["ZAPI_CLIENT_TOKEN"]}


def enviar(texto: str, imagem: str = "", destino: str | None = None) -> dict:
    """Manda a foto com a legenda; sem foto, manda só o texto."""
    destino = destino or os.environ["WHATSAPP_GRUPO_ID"]
    if imagem:
        corpo = {"phone": destino, "image": imagem, "caption": texto}
        return http_json(_url("send-image"), metodo="POST", corpo=corpo, cabecalhos=_cab())
    corpo = {"phone": destino, "message": texto}
    return http_json(_url("send-text"), metodo="POST", corpo=corpo, cabecalhos=_cab())


def listar_grupos() -> list[dict]:
    """Ajuda a descobrir o WHATSAPP_GRUPO_ID depois de conectar o chip."""
    resp = http_json(_url("groups?page=1&pageSize=50"), cabecalhos=_cab())
    return resp if isinstance(resp, list) else resp.get("groups", [])
