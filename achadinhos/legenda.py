"""Legenda curta no estilo do grupo.

Exemplo:
    A air fryer que faltava na sua cozinha! 🍟
    Air Fryer Mondial 4L Family
    De ~R$ 399,90~ por *R$ 249,90* (37% OFF)
    👉 https://link-de-afiliado
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from .oferta import Oferta

# (termos que aparecem no nome/palavra-chave, ganchos possíveis)
GANCHOS = [
    (("air fryer", "fritadeira"), [
        "A air fryer que faltava na sua cozinha! 🍟",
        "Batata crocante sem óleo e sem gastar muito! 🍟",
    ]),
    (("panela", "frigideira", "caçarola"), [
        "Panela nova, comida mais gostosa! 🍳",
        "Hora de aposentar aquela panela velha! 🍳",
    ]),
    (("pote", "hermetico", "marmita"), [
        "Geladeira organizada é outra vida! 🥗",
        "Chega de pote sem tampa! 🥗",
    ]),
    (("organizador", "prateleira", "cesto", "nicho"), [
        "Tudo no lugar, sem gastar muito! 🧺",
        "O armário dos sonhos começa aqui! 🧺",
    ]),
    (("liquidificador", "mixer", "batedeira", "processador"), [
        "Vitamina, bolo e molho num piscar de olhos! 🥤",
        "O ajudante que sua cozinha merece! 🥤",
    ]),
    (("cafeteira", "cafe", "chaleira"), [
        "Seu café da manhã vai subir de nível! ☕",
        "Para quem não vive sem um cafezinho! ☕",
    ]),
    (("faca", "talher", "tabua"), [
        "Cozinhar fica bem mais fácil assim! 🔪",
    ]),
    (("jogo de cama", "lencol", "edredom", "travesseiro", "cobertor", "manta"), [
        "Sua cama merece esse carinho! 🛏️",
        "Noite de sono de hotel, preço de achadinho! 🛏️",
    ]),
    (("toalha", "banheiro", "tapete"), [
        "A casa mais aconchegante gastando pouco! 🏠",
    ]),
    (("aspirador", "mop", "vassoura", "limpeza"), [
        "Faxina mais rápida, fim de semana livre! ✨",
        "Casa limpa sem tanto esforço! ✨",
    ]),
    (("luminaria", "lampada", "led", "abajur"), [
        "Uma luz que muda o clima da casa! 💡",
    ]),
    (("cortina", "persiana"), [
        "O quarto escurinho que você queria! 🌙",
    ]),
    (("garrafa", "termica", "copo"), [
        "Gelado o dia todo, do jeito que você gosta! 🧊",
    ]),
]

GANCHOS_GERAIS = [
    "Achadinho do dia para a sua casa! 🏠",
    "Esse preço não dura muito! ⏰",
    "Olha o que eu achei pra sua casa! 👀",
]


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower())
                   if unicodedata.category(c) != "Mn")


def reais(valor: float) -> str:
    """1899.9 -> 'R$ 1.899,90'"""
    inteiro, centavos = f"{valor:.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"R$ {inteiro},{centavos}"


def nome_curto(nome: str, limite: int = 60) -> str:
    nome = re.sub(r"[\[\(【].*?[\]\)】]", "", nome)      # tira [ENVIO JÁ], (Promoção)…
    nome = re.sub(r"\s+", " ", nome).strip(" -|,")
    if len(nome) <= limite:
        return nome
    corte = nome[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(" -|,") + "…"


def gancho(oferta: Oferta) -> str:
    texto = _sem_acento(f"{oferta.palavra_chave} {oferta.nome}")
    opcoes = GANCHOS_GERAIS
    for termos, frases in GANCHOS:
        if any(t in texto for t in termos):
            opcoes = frases
            break
    # escolha estável por produto, para a mesma oferta sempre sair igual
    i = int(hashlib.md5(oferta.chave.encode()).hexdigest(), 16) % len(opcoes)
    return opcoes[i]


def montar(oferta: Oferta) -> str:
    linhas = [gancho(oferta), nome_curto(oferta.nome)]
    por = reais(oferta.preco)
    if oferta.extra.get("a_partir_de"):
        por = f"a partir de {por}"
    if oferta.desconto > 0:
        linhas.append(f"De ~{reais(oferta.preco_antigo)}~ por *{por}* ({oferta.desconto}% OFF)")
    else:
        linhas.append(f"Por *{por}*")
    linhas.append(f"👉 {oferta.link}")
    return "\n".join(linhas)
