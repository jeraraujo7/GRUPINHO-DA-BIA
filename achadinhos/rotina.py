"""Rotina do dia.

  buscar  -> varre casa e cozinha nas lojas e grava a vitrine (data/vitrine.json)
  postar  -> pega a melhor oferta da vitrine, confere o preço na hora e posta
  rodar   -> fica ligado das 7h às 22h: busca a cada 30 min e posta a cada 5 min
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import legenda, mercadolivre, shopee, whatsapp
from .oferta import Oferta

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
LOJAS = {"shopee": shopee, "mercadolivre": mercadolivre}


# ---------------------------------------------------------------- arquivos

def carregar_config(caminho: Path | None = None) -> dict:
    return json.loads((caminho or RAIZ / "config.json").read_text(encoding="utf-8"))


def _ler(caminho: Path, padrao):
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return padrao


def _gravar(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def caminho_vitrine() -> Path:
    return DADOS / "vitrine.json"


def caminho_historico() -> Path:
    return DADOS / "historico.json"


def caminho_registro(dia: str) -> Path:
    return DADOS / "postagens" / f"{dia}.json"


def agora_em(cfg: dict) -> datetime:
    return datetime.now(ZoneInfo(cfg["agenda"]["fuso"]))


# ---------------------------------------------------------------- filtros

def passa_filtros(o: Oferta, f: dict) -> str | None:
    """None se a oferta serve; senão o motivo da recusa."""
    if not o.link and o.loja == "shopee":
        return "sem link"
    if o.desconto_exato <= f.get("desconto_acima_de", 0):
        return f"desconto {o.desconto_exato:.1f}%"
    if not (f.get("preco_minimo", 0) <= o.preco <= f.get("preco_maximo", float("inf"))):
        return f"preço {o.preco}"
    if not o.extra.get("sem_avaliacao") and o.avaliacao < f.get("avaliacao_minima", 0):
        return f"avaliação {o.avaliacao}"
    if o.vendas < f.get("vendas_minimas", 0):
        return f"{o.vendas} vendas"
    return None


def pontuacao(o: Oferta) -> float:
    """Desconto pesa mais; vendas e avaliação desempatam."""
    return o.desconto_exato * 2 + math.log10(1 + o.vendas) * 4 + o.avaliacao


# ---------------------------------------------------------------- buscar

def lojas_ativas(cfg: dict) -> list[str]:
    return [nome for nome, ligada in cfg.get("lojas", {}).items()
            if ligada and LOJAS[nome].configurada()]


def buscar(cfg: dict, agora: datetime | None = None, log=print) -> list[Oferta]:
    """Varre todas as categorias e palavras-chave e grava a vitrine."""
    agora = agora or agora_em(cfg)
    lojas = lojas_ativas(cfg)
    if not lojas:
        raise RuntimeError("nenhuma loja configurada (faltam as chaves de acesso)")

    melhores: dict[str, Oferta] = {}
    for loja in lojas:
        mod = LOJAS[loja]
        if hasattr(mod, "buscas"):  # a loja define as próprias buscas (ex.: páginas do ML)
            buscas = mod.buscas()
        else:
            buscas = [{"categoria": c} for c in cfg.get(f"{loja}_categorias", [])]
        if getattr(mod, "usa_palavras_chave", True):
            buscas += [{"palavra_chave": t} for t in cfg["palavras_chave"]]
        total = aprovadas = 0
        for b in buscas:
            try:
                achadas = mod.buscar(**b)
            except Exception as e:  # uma busca ruim não derruba as outras
                log(f"  ! {loja} {b}: {e}")
                continue
            total += len(achadas)
            for o in achadas:
                if passa_filtros(o, cfg["filtros"]) is None:
                    atual = melhores.get(o.chave)
                    if atual is None or o.preco < atual.preco:
                        melhores[o.chave] = o
                        aprovadas += 1
        log(f"  {loja}: {len(buscas)} buscas, {total} produtos, {aprovadas} com desconto")

    ofertas = sorted(melhores.values(), key=pontuacao, reverse=True)
    _gravar(caminho_vitrine(), {"atualizada_em": agora.isoformat(),
                                "ofertas": [o.para_dict() for o in ofertas]})
    log(f"Vitrine: {len(ofertas)} ofertas")
    return ofertas


# ---------------------------------------------------------------- repetição

def em_espera(o: Oferta, historico: dict, agora: datetime, horas: float) -> bool:
    """Produto postado há pouco fica de fora, a não ser que o preço tenha caído."""
    ultimo = historico.get(o.chave)
    if not ultimo:
        return False
    if isinstance(ultimo, str):  # formato antigo: só a data
        ultimo = {"em": ultimo + "T00:00:00-03:00", "preco": float("inf")}
    passou = (agora - datetime.fromisoformat(ultimo["em"])).total_seconds() / 3600
    if passou >= horas:
        return False
    # promoção melhorou (3% mais barato) e já faz pelo menos 1h: pode repetir
    return not (passou >= 1 and o.preco <= ultimo["preco"] * 0.97)


# ---------------------------------------------------------------- conferir e postar

def conferir(o: Oferta, filtros: dict) -> tuple[Oferta | None, str]:
    """Consulta o preço na hora. Devolve (oferta atualizada, motivo se for cancelar)."""
    atual = LOJAS[o.loja].preco_atual(o)
    if atual is None:
        return None, "produto indisponível ou oferta encerrada"
    atual.palavra_chave = o.palavra_chave
    motivo = passa_filtros(atual, {**filtros, "avaliacao_minima": 0, "vendas_minimas": 0})
    if motivo and motivo != "sem link":
        return None, motivo
    atual.link = atual.link or o.link
    return atual, ""


def candidatas(cfg: dict, agora: datetime) -> list[Oferta]:
    historico = _ler(caminho_historico(), {})
    vitrine = _ler(caminho_vitrine(), {}).get("ofertas", [])
    horas = cfg["agenda"]["repetir_apos_horas"]
    lista = [o for d in vitrine if not em_espera(o := Oferta.de_dict(d), historico, agora, horas)]
    # variedade: evita o mesmo tipo de produto das 2 últimas postagens
    recentes = [r["palavra_chave"] for r in _ler(caminho_registro(agora.strftime("%Y-%m-%d")), [])[-2:]]
    variadas = [o for o in lista if o.palavra_chave not in recentes]
    return variadas or lista


def postar(cfg: dict, agora: datetime | None = None, enviar: bool = True,
           destino: str | None = None, tentativas: int = 6, log=print) -> dict | None:
    agora = agora or agora_em(cfg)
    dia = agora.strftime("%Y-%m-%d")
    for o in candidatas(cfg, agora)[:tentativas]:
        try:
            atual, motivo = conferir(o, cfg["filtros"])
        except Exception as e:
            log(f"! {o.chave}: conferência de preço falhou: {e}")
            continue
        if atual is None:
            log(f"- {o.chave}: pulada ({motivo})")
            _tirar_da_vitrine(o.chave)
            continue
        if atual.loja == "mercadolivre":
            if not mercadolivre.gera_link():
                continue
            try:
                atual.link = mercadolivre.link_afiliado(atual.extra.get("permalink") or o.extra["permalink"])
            except Exception as e:
                log(f"! link ML {o.id}: {e}")
                continue

        texto = legenda.montar(atual)
        item = {"em": agora.isoformat(), "chave": o.chave, "palavra_chave": o.palavra_chave,
                "preco": atual.preco, "desconto": atual.desconto, "legenda": texto}
        if not enviar:
            log(f"SIMULAÇÃO {o.chave}\n{texto}\n")
            return item
        whatsapp.enviar(texto, atual.imagem, destino)
        historico = _ler(caminho_historico(), {})
        historico[o.chave] = {"em": agora.isoformat(), "preco": atual.preco}
        _gravar(caminho_historico(), historico)
        registro = _ler(caminho_registro(dia), [])
        registro.append(item)
        _gravar(caminho_registro(dia), registro)
        log(f"POSTADA {o.chave}\n{texto}\n")
        return item
    log("Nenhuma oferta disponível agora.")
    return None


def _tirar_da_vitrine(chave: str) -> None:
    v = _ler(caminho_vitrine(), {})
    if v:
        v["ofertas"] = [d for d in v.get("ofertas", []) if f"{d['loja']}:{d['id']}" != chave]
        _gravar(caminho_vitrine(), v)


# ---------------------------------------------------------------- ficar ligado

def rodar(cfg: dict, ate: datetime | None = None, relogio=None, dormir=time.sleep,
          log=print) -> int:
    """Laço do dia. Devolve quantas ofertas postou."""
    relogio = relogio or (lambda: agora_em(cfg))
    ag = cfg["agenda"]
    passo_post = timedelta(minutes=ag["postar_a_cada_minutos"])
    passo_busca = timedelta(minutes=ag["buscar_a_cada_minutos"])
    ultima_busca = None
    postadas = 0
    while True:
        agora = relogio()
        inicio = agora.replace(hour=ag["hora_inicio"], minute=0, second=0, microsecond=0)
        fim = agora.replace(hour=ag["hora_fim"], minute=0, second=0, microsecond=0)
        limite = min(fim, ate) if ate else fim
        if agora >= limite:
            break
        if agora < inicio:
            dormir((inicio - agora).total_seconds())
            continue
        if ultima_busca is None or agora - ultima_busca >= passo_busca:
            try:
                buscar(cfg, agora, log=log)
            except Exception as e:
                log(f"! busca falhou: {e}")
            ultima_busca = agora
        try:
            if postar(cfg, agora, log=log):
                postadas += 1
        except Exception as e:
            log(f"! postagem falhou: {e}")
        proximo = agora + passo_post
        espera = (proximo - relogio()).total_seconds()
        if espera > 0:
            dormir(espera)
    log(f"Fim da rodada: {postadas} ofertas postadas.")
    return postadas
