"""Mercado Livre: busca de produtos e link de afiliado.

Busca e preço: API do Mercado Livre (api.mercadolibre.com), com o acesso do
aplicativo criado em developers.mercadolivre.com.br:
  ML_CLIENT_ID, ML_CLIENT_SECRET  -> o token (que vence a cada 6h) é renovado sozinho
  ML_ACCESS_TOKEN                 -> alternativa: token fixo, se preferir

Link de afiliado: o Mercado Livre não publica uma API aberta para gerar o link
(o caminho oficial é o "Gerador de Links" no Portal do Afiliado). Por isso o
gerador fica configurável:
  ML_LINK_API_URL  endpoint que recebe {"url": "<produto>"} e devolve o link
  ML_LINK_API_KEY  chave desse serviço (enviada no cabeçalho X-API-Key)
Sem ele, as ofertas do Mercado Livre são encontradas mas não são postadas.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.parse

from .oferta import Oferta, http_json

API = "https://api.mercadolibre.com"


_token = {"valor": "", "vence": 0.0}


def configurada() -> bool:
    return bool(os.environ.get("ML_ACCESS_TOKEN")
                or (os.environ.get("ML_CLIENT_ID") and os.environ.get("ML_CLIENT_SECRET")))


def token() -> str:
    if os.environ.get("ML_ACCESS_TOKEN"):
        return os.environ["ML_ACCESS_TOKEN"]
    if not (os.environ.get("ML_CLIENT_ID") and os.environ.get("ML_CLIENT_SECRET")):
        return ""
    if time.time() < _token["vence"]:
        return _token["valor"]
    corpo = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ["ML_CLIENT_ID"],
        "client_secret": os.environ["ML_CLIENT_SECRET"],
    }).encode()
    req = urllib.request.Request(f"{API}/oauth/token", data=corpo, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode())
    _token["valor"] = resp["access_token"]
    _token["vence"] = time.time() + int(resp.get("expires_in", 21600)) - 300  # renova 5 min antes
    return _token["valor"]


def gera_link() -> bool:
    return bool(os.environ.get("ML_LINK_API_URL"))


def _cab() -> dict:
    tok = token()
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _para_oferta(r: dict, palavra_chave: str = "") -> Oferta | None:
    preco = r.get("price")
    antigo = r.get("original_price") or preco
    if not preco or r.get("available_quantity", 1) == 0:
        return None
    return Oferta(
        loja="mercadolivre",
        id=r["id"],
        nome=(r.get("title") or "").strip(),
        preco=float(preco),
        preco_antigo=float(antigo),
        link="",  # preenchido por link_afiliado()
        imagem=(r.get("thumbnail") or "").replace("-I.jpg", "-O.jpg"),
        avaliacao=0.0,
        vendas=int(r.get("sold_quantity") or 0),
        palavra_chave=palavra_chave,
        extra={"permalink": r.get("permalink", ""), "sem_avaliacao": True},
    )


def buscar(palavra_chave: str = "", categoria: str | None = None,
           paginas: int = 2, limite: int = 50) -> list[Oferta]:
    """Busca por palavra-chave ou por categoria (ex.: MLB1574 Casa, Móveis e Decoração)."""
    rotulo = f"categoria {categoria}" if categoria else palavra_chave
    ofertas = []
    for pagina in range(paginas):
        params = {"limit": limite, "offset": pagina * limite}
        if categoria:
            params["category"] = categoria
        if palavra_chave:
            params["q"] = palavra_chave
        dados = http_json(f"{API}/sites/MLB/search?{urllib.parse.urlencode(params)}", cabecalhos=_cab())
        resultados = dados.get("results", [])
        ofertas += [o for r in resultados if (o := _para_oferta(r, rotulo))]
        if len(resultados) < limite:
            break
    return ofertas


def link_afiliado(permalink: str) -> str:
    url = os.environ["ML_LINK_API_URL"]
    cab = {}
    if os.environ.get("ML_LINK_API_KEY"):
        cab["X-API-Key"] = os.environ["ML_LINK_API_KEY"]
    resp = http_json(url, metodo="POST", corpo={"url": permalink}, cabecalhos=cab)
    link = resp.get("final_url") or resp.get("affiliate_url") or resp.get("link")
    if not link:
        raise RuntimeError(f"gerador de link do Mercado Livre não devolveu link: {str(resp)[:200]}")
    return link


def preco_atual(oferta: Oferta) -> Oferta | None:
    r = http_json(f"{API}/items/{oferta.id}", cabecalhos=_cab())
    if r.get("status") != "active":
        return None
    nova = _para_oferta(r, oferta.palavra_chave)
    if nova:
        nova.link = oferta.link
    return nova
