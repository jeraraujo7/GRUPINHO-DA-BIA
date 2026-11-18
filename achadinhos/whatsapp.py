"""Envio para o grupo do WhatsApp pela Z-API (serviço não oficial).

Variáveis de ambiente (nunca no repositório):
  ZAPI_INSTANCE_ID, ZAPI_TOKEN   -> painel da Z-API, na instância conectada ao chip do grupo
  ZAPI_CLIENT_TOKEN              -> token de segurança da conta (aba Segurança)
  WHATSAPP_GRUPO_ID              -> id do grupo, ex.: 120363000000000000-group

Use um chip só para o grupo, nunca o número pessoal: há risco de bloqueio.
"""

from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

from .oferta import http_json

BASE = "https://api.z-api.io/instances/{inst}/token/{tok}"


def _nome_do_grupo() -> str:
    """Nome do grupo (WHATSAPP_GRUPO_NOME ou "whatsapp_grupo_nome" no config.json)."""
    if os.environ.get("WHATSAPP_GRUPO_NOME"):
        return os.environ["WHATSAPP_GRUPO_NOME"]
    try:
        cfg = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text(encoding="utf-8"))
        return cfg.get("whatsapp_grupo_nome", "")
    except (OSError, ValueError):
        return ""


def configurado() -> bool:
    chaves = all(os.environ.get(v) for v in ("ZAPI_INSTANCE_ID", "ZAPI_TOKEN", "ZAPI_CLIENT_TOKEN"))
    return chaves and bool(os.environ.get("WHATSAPP_GRUPO_ID") or _nome_do_grupo())


_grupo: dict[str, str] = {}


def id_do_grupo() -> str:
    """Usa WHATSAPP_GRUPO_ID; se não houver, acha o grupo pelo nome na lista do chip."""
    if os.environ.get("WHATSAPP_GRUPO_ID"):
        return os.environ["WHATSAPP_GRUPO_ID"]
    if "id" in _grupo:
        return _grupo["id"]
    procurado = _simples(_nome_do_grupo())
    for g in listar_grupos():
        if procurado and procurado in _simples(g.get("name") or g.get("subject") or ""):
            _grupo["id"] = g.get("phone") or g.get("id")
            return _grupo["id"]
    raise RuntimeError(f"o chip não está em nenhum grupo chamado '{_nome_do_grupo()}'")


def _simples(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if c.isalnum())


def _url(acao: str) -> str:
    return BASE.format(inst=os.environ["ZAPI_INSTANCE_ID"], tok=os.environ["ZAPI_TOKEN"]) + "/" + acao


def _cab() -> dict:
    return {"Client-Token": os.environ["ZAPI_CLIENT_TOKEN"]}


def enviar(texto: str, imagem: str = "", destino: str | None = None) -> dict:
    """Manda a foto com a legenda; sem foto, manda só o texto."""
    destino = destino or id_do_grupo()
    if imagem:
        corpo = {"phone": destino, "image": imagem, "caption": texto}
        return http_json(_url("send-image"), metodo="POST", corpo=corpo, cabecalhos=_cab())
    corpo = {"phone": destino, "message": texto}
    return http_json(_url("send-text"), metodo="POST", corpo=corpo, cabecalhos=_cab())


def listar_grupos() -> list[dict]:
    """Ajuda a descobrir o WHATSAPP_GRUPO_ID depois de conectar o chip."""
    resp = http_json(_url("groups?page=1&pageSize=50"), cabecalhos=_cab())
    return resp if isinstance(resp, list) else resp.get("groups", [])
