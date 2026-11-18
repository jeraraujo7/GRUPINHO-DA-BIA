"""Shopee Afiliados (Open API GraphQL do Brasil).

Credenciais (variáveis de ambiente, nunca no repositório):
  SHOPEE_APP_ID, SHOPEE_SECRET  -> painel affiliate.shopee.com.br > Open API

Autenticação: cabeçalho
  Authorization: SHA256 Credential={AppId}, Timestamp={ts}, Signature={sha256(AppId+ts+corpo+Secret)}
"""

from __future__ import annotations

import hashlib
import os
import time

from .oferta import Oferta, http_json, json_compacto

URL = os.environ.get("SHOPEE_URL", "https://open-api.affiliate.shopee.com.br/graphql")

CAMPOS = """
  itemId productName priceMin priceMax priceDiscountRate ratingStar sales
  imageUrl offerLink productLink shopName commissionRate periodEndTime productCatIds
"""

# sortType: 1 relevância, 2 mais vendidos, 3 maior preço, 4 menor preço, 5 maior comissão
BUSCA = "query{productOfferV2(%s,sortType:2,page:%d,limit:%d){nodes{%s}pageInfo{page limit hasNextPage}}}"
POR_ITEM = "query{productOfferV2(itemId:%d,limit:1){nodes{%s}}}"


class ErroShopee(RuntimeError):
    pass


def configurada() -> bool:
    return bool(os.environ.get("SHOPEE_APP_ID") and os.environ.get("SHOPEE_SECRET"))


def assinatura(app_id: str, timestamp: int, corpo: str, secret: str) -> str:
    return hashlib.sha256(f"{app_id}{timestamp}{corpo}{secret}".encode()).hexdigest()


def _consulta(query: str) -> dict:
    app_id = os.environ["SHOPEE_APP_ID"]
    secret = os.environ["SHOPEE_SECRET"]
    corpo = json_compacto({"query": query})
    ts = int(time.time())
    cab = {
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, "
                         f"Signature={assinatura(app_id, ts, corpo, secret)}"
    }
    resp = http_json(URL, metodo="POST", corpo=corpo, cabecalhos=cab)
    if resp.get("errors"):
        raise ErroShopee(str(resp["errors"])[:500])
    return resp.get("data") or {}


def _para_oferta(n: dict, palavra_chave: str = "") -> Oferta | None:
    try:
        preco = float(n["priceMin"])
        preco_max = float(n.get("priceMax") or preco)
        desc = int(n.get("priceDiscountRate") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    if preco <= 0:
        return None
    # A API dá o preço atual e o % de desconto; o preço "de" sai daí.
    preco_antigo = round(preco / (1 - desc / 100), 2) if 0 < desc < 100 else preco
    return Oferta(
        loja="shopee",
        id=str(n["itemId"]),
        nome=(n.get("productName") or "").strip(),
        preco=preco,
        preco_antigo=preco_antigo,
        link=n.get("offerLink") or "",
        imagem=n.get("imageUrl") or "",
        avaliacao=float(n.get("ratingStar") or 0),
        vendas=int(n.get("sales") or 0),
        palavra_chave=palavra_chave,
        extra={
            "a_partir_de": preco_max > preco * 1.05,
            "fim_oferta": int(n.get("periodEndTime") or 0),
            "loja_nome": n.get("shopName") or "",
            "comissao": n.get("commissionRate") or "",
            "categorias": n.get("productCatIds") or [],
        },
    )


def buscar(palavra_chave: str = "", categoria: int | None = None,
           paginas: int = 2, limite: int = 50) -> list[Oferta]:
    """Busca por palavra-chave ou por id de categoria (nível 1, 2 ou 3)."""
    if categoria:
        filtro, rotulo = f"productCatId:{int(categoria)}", f"categoria {categoria}"
    else:
        filtro, rotulo = f"keyword:{json_compacto(palavra_chave)}", palavra_chave
    ofertas = []
    for pagina in range(1, paginas + 1):
        dados = _consulta(BUSCA % (filtro, pagina, limite, CAMPOS))
        bloco = dados.get("productOfferV2") or {}
        for n in bloco.get("nodes") or []:
            o = _para_oferta(n, rotulo)
            if o and o.link:
                ofertas.append(o)
        if not (bloco.get("pageInfo") or {}).get("hasNextPage"):
            break
    return ofertas


def preco_atual(oferta: Oferta) -> Oferta | None:
    """Consulta o produto de novo. None se a oferta sumiu (sem estoque/encerrada)."""
    dados = _consulta(POR_ITEM % (int(oferta.id), CAMPOS))
    nodes = (dados.get("productOfferV2") or {}).get("nodes") or []
    if not nodes:
        return None
    nova = _para_oferta(nodes[0], oferta.palavra_chave)
    if nova and not nova.link:
        nova.link = oferta.link
    return nova
