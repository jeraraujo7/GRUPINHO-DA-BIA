"""Modelo comum de oferta, usado por todas as lojas."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field


@dataclass
class Oferta:
    loja: str            # "shopee" ou "mercadolivre"
    id: str              # id do produto na loja
    nome: str
    preco: float         # preço atual (por)
    preco_antigo: float  # preço cheio (de)
    link: str            # link de afiliado
    imagem: str = ""
    avaliacao: float = 0.0
    vendas: int = 0
    palavra_chave: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def chave(self) -> str:
        return f"{self.loja}:{self.id}"

    @property
    def desconto(self) -> int:
        if self.preco_antigo <= 0 or self.preco >= self.preco_antigo:
            return 0
        return round((1 - self.preco / self.preco_antigo) * 100)

    def para_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def de_dict(cls, d: dict) -> "Oferta":
        return cls(**d)


def json_compacto(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def http_json(url: str, *, metodo: str = "GET", corpo: dict | str | None = None,
              cabecalhos: dict | None = None, timeout: int = 30) -> dict:
    """Requisição HTTP simples que devolve JSON (só biblioteca padrão).

    `corpo` pode ser um dict ou o texto JSON já pronto (necessário quando a
    assinatura é calculada sobre o texto exato enviado, como na Shopee).
    """
    dados = None
    cab = {"Accept": "application/json", "User-Agent": "achadinhos-bot/1.0"}
    if corpo is not None:
        texto = corpo if isinstance(corpo, str) else json_compacto(corpo)
        dados = texto.encode()
        cab["Content-Type"] = "application/json"
    cab.update(cabecalhos or {})
    req = urllib.request.Request(url, data=dados, headers=cab, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} em {url.split('?')[0]}: {detalhe}") from None
