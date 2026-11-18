"""Mercado Livre: ofertas lidas das páginas públicas de categoria e link de afiliado.

Por que páginas e não API: o suporte do Mercado Livre confirmou (chamado
496547907, 18/11/2026) que a conta não pode criar aplicativo no DevCenter, e
sem aplicativo a API bloqueia a busca. A busca do site, a página de ofertas e a
página de cada produto pedem login para acesso automático. As páginas de
categoria (/c/...) abrem sem login e trazem os produtos em destaque com preço
antigo, preço atual e % OFF. São essas que o robô lê ("mercadolivre_paginas"
no config.json).

Conferência de preço: como a página do produto pede login, o preço é conferido
relendo a página de categoria (cache de 10 min). Se o produto saiu da página,
a oferta é pulada.

Link de afiliado: não há API oficial (o canal oficial é o Gerador de Links do
Portal). Os parâmetros de rastreio do link de exemplo são colados em cada produto:
  ML_LINK_PARAMS   ex.: "matt_tool=123&matt_word=apelido" (aceita o link inteiro).
                   Sem a variável, vale "ml_link_params" do config.json.
  ML_LINK_API_URL  alternativa: endpoint que recebe {"url": "<produto>"} e
  ML_LINK_API_KEY  devolve o link (chave no cabeçalho X-API-Key)
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .oferta import Oferta, http_json

CONFIG = Path(__file__).resolve().parent.parent / "config.json"
PAGINAS_PADRAO = [
    "https://www.mercadolivre.com.br/c/casa-moveis-e-decoracao",
    "https://www.mercadolivre.com.br/c/eletrodomesticos",
]
NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
CACHE_MINUTOS = 10

# o robô não usa as palavras-chave aqui: a busca do site pede login
usa_palavras_chave = False

_cache: dict[str, tuple[float, list[Oferta]]] = {}


class PedeLogin(RuntimeError):
    pass


def _config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def paginas() -> list[str]:
    return _config().get("mercadolivre_paginas") or PAGINAS_PADRAO


def configurada() -> bool:
    return True  # páginas públicas, não precisa de chave


# ---------------------------------------------------------------- leitura da página

def baixar(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": NAVEGADOR, "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            final = r.geturl()
            corpo = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} em {url}") from None
    if "account-verification" in final or "/login" in final:
        raise PedeLogin(f"o Mercado Livre pediu login para ler {url}")
    return corpo


def _valor(aria: str) -> float | None:
    """'Antes: 1704 reais com 90 centavos' -> 1704.9"""
    m = re.search(r"([\d.]+)\s+reais(?:\s+com\s+(\d+)\s+centavos?)?", aria or "")
    if not m:
        return None
    return float(m.group(1).replace(".", "")) + int(m.group(2) or 0) / 100


def _id(link: str) -> str:
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(link.replace("#", "?", 1)).query)
    if q.get("wid"):
        return q["wid"][0]
    m = re.search(r"(MLBU?)-?(\d+)", link)
    return f"{m.group(1)}{m.group(2)}" if m else ""


def _imagem(src: str) -> str:
    """Troca a miniatura .webp pela foto grande em .jpg (melhor para o WhatsApp)."""
    m = re.search(r"D_[A-Z_0-9]*?_(\d+-ML[A-Z]\d+_\d+)-[A-Z]+\.webp", src or "")
    return f"https://http2.mlstatic.com/D_NQ_NP_{m.group(1)}-O.jpg" if m else (src or "")


def _rotulo(nome: str) -> str:
    """Duas primeiras palavras do título: serve para variar os tipos de produto."""
    return " ".join(re.findall(r"[A-Za-zÀ-ÿ]+", nome.lower())[:2])


def ler_pagina(texto: str) -> list[Oferta]:
    ofertas, vistos = [], set()
    for card in texto.split('class="poly-card__portada"')[1:]:
        titulo = re.search(r'class="poly-component__title[^"]*"[^>]*>([^<]+)<', card)
        link = re.search(r'<a href="([^"]+)"[^>]*class="poly-component__title', card)
        atual = re.search(r'class="poly-price__current".*?aria-label="([^"]+)"', card, re.S)
        if not (titulo and link and atual):
            continue
        antes = re.search(r'andes-money-amount--previous[^>]*aria-label="([^"]+)"', card)
        img = re.search(r'<img[^>]+class="poly-component__picture"[^>]+src="([^"]+)"', card)
        link_url = html.unescape(link.group(1))
        preco = _valor(atual.group(1))
        preco_antigo = _valor(antes.group(1)) if antes else preco
        ident = _id(link_url)
        if not preco or not ident or ident in vistos:
            continue
        vistos.add(ident)
        nome = html.unescape(titulo.group(1)).strip()
        ofertas.append(Oferta(
            loja="mercadolivre", id=ident, nome=nome, preco=preco,
            preco_antigo=preco_antigo or preco, link="",
            imagem=_imagem(img.group(1) if img else ""),
            palavra_chave=_rotulo(nome),
            extra={"permalink": link_url.split("#")[0], "sem_avaliacao": True,
                   "pix": "no Pix" in card.split("poly-price__installments")[0]},
        ))
    return ofertas


def _ofertas_da_pagina(url: str, max_idade: float = CACHE_MINUTOS * 60) -> list[Oferta]:
    guardado = _cache.get(url)
    if guardado and time.time() - guardado[0] < max_idade:
        return guardado[1]
    ofertas = ler_pagina(baixar(url))
    _cache[url] = (time.time(), ofertas)
    return ofertas


def buscar(palavra_chave: str = "", categoria: str | None = None, **_) -> list[Oferta]:
    """`categoria` é o endereço de uma página /c/ do Mercado Livre."""
    if not categoria:
        return []
    return _ofertas_da_pagina(categoria, max_idade=0)


def buscas() -> list[dict]:
    return [{"categoria": u} for u in paginas()]


def preco_atual(oferta: Oferta) -> Oferta | None:
    """Relê as páginas (cache de 10 min). None se o produto saiu delas."""
    for url in paginas():
        for o in _ofertas_da_pagina(url):
            if o.id == oferta.id:
                o.link = oferta.link
                return o
    return None


# ---------------------------------------------------------------- link de afiliado

def _params_afiliado() -> list[tuple[str, str]]:
    bruto = (os.environ.get("ML_LINK_PARAMS") or _config().get("ml_link_params", "")).strip()
    if "?" in bruto:  # colaram o link inteiro
        bruto = bruto.split("?", 1)[1]
    bruto = bruto.split("#", 1)[0]
    return urllib.parse.parse_qsl(bruto)


def gera_link() -> bool:
    return bool(_params_afiliado() or os.environ.get("ML_LINK_API_URL"))


def link_afiliado(permalink: str) -> str:
    params = _params_afiliado()
    if params:
        partes = urllib.parse.urlsplit(permalink)
        nomes = {k for k, _ in params}
        atuais = [(k, v) for k, v in urllib.parse.parse_qsl(partes.query) if k not in nomes]
        consulta = urllib.parse.urlencode(atuais + params)
        return urllib.parse.urlunsplit(partes._replace(query=consulta, fragment=""))
    url = os.environ["ML_LINK_API_URL"]
    cab = {}
    if os.environ.get("ML_LINK_API_KEY"):
        cab["X-API-Key"] = os.environ["ML_LINK_API_KEY"]
    resp = http_json(url, metodo="POST", corpo={"url": permalink}, cabecalhos=cab)
    link = resp.get("final_url") or resp.get("affiliate_url") or resp.get("link")
    if not link:
        raise RuntimeError(f"gerador de link do Mercado Livre não devolveu link: {str(resp)[:200]}")
    return link
