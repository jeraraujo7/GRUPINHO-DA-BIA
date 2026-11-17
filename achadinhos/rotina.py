"""Rotina do dia: planejar a fila de ofertas e postar uma por vez.

  planejar  -> busca nas lojas, filtra, escolhe as ofertas do dia e distribui os horários
  postar    -> posta a próxima oferta cujo horário já chegou, conferindo o preço na hora
"""

from __future__ import annotations

import json
import random
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


def caminho_fila(dia: str) -> Path:
    return DADOS / "fila" / f"{dia}.json"


def caminho_historico() -> Path:
    return DADOS / "historico.json"


# ---------------------------------------------------------------- filtros

def passa_filtros(o: Oferta, f: dict, agora_ts: float | None = None) -> str | None:
    """None se a oferta serve; senão o motivo da recusa."""
    agora_ts = agora_ts or time.time()
    if not o.link and o.loja == "shopee":
        return "sem link"
    if o.desconto < f.get("desconto_minimo", 0):
        return f"desconto {o.desconto}%"
    if not o.extra.get("sem_avaliacao") and o.avaliacao < f.get("avaliacao_minima", 0):
        return f"avaliação {o.avaliacao}"
    if o.vendas < f.get("vendas_minimas", 0):
        return f"{o.vendas} vendas"
    if o.preco > f.get("preco_maximo", float("inf")):
        return f"preço {o.preco}"
    fim = o.extra.get("fim_oferta") or 0
    if fim and fim < agora_ts + 12 * 3600:
        return "oferta acaba em menos de 12h"
    return None


def pontuacao(o: Oferta) -> float:
    return o.desconto * 2 + min(o.vendas, 5000) / 250 + o.avaliacao * 3


# ---------------------------------------------------------------- planejar

def horarios_do_dia(dia: datetime, n: int, inicio: int, fim: int, semente: int) -> list[datetime]:
    """n horários espalhados entre inicio e fim, com alguns minutos de variação."""
    rnd = random.Random(semente)
    total = (fim - inicio) * 60
    passo = total / max(n, 1)
    base = dia.replace(hour=inicio, minute=0, second=0, microsecond=0)
    saida = []
    for i in range(n):
        minuto = int(i * passo + passo / 2 + rnd.uniform(-passo / 4, passo / 4))
        saida.append(base + timedelta(minutes=max(0, min(total - 1, minuto))))
    return saida


def lojas_ativas(cfg: dict) -> list[str]:
    return [nome for nome, ligada in cfg.get("lojas", {}).items()
            if ligada and LOJAS[nome].configurada()]


def escolher(candidatas: list[Oferta], n: int, max_por_termo: int = 2) -> list[Oferta]:
    """As melhores, alternando lojas e sem repetir muito o mesmo tipo de produto."""
    por_loja: dict[str, list[Oferta]] = {}
    for o in sorted(candidatas, key=pontuacao, reverse=True):
        por_loja.setdefault(o.loja, []).append(o)
    escolhidas, por_termo, vistos = [], {}, set()
    while len(escolhidas) < n and any(por_loja.values()):
        for loja in list(por_loja):
            fila = por_loja[loja]
            while fila:
                o = fila.pop(0)
                if o.chave in vistos or por_termo.get(o.palavra_chave, 0) >= max_por_termo:
                    continue
                vistos.add(o.chave)
                por_termo[o.palavra_chave] = por_termo.get(o.palavra_chave, 0) + 1
                escolhidas.append(o)
                break
            if len(escolhidas) >= n:
                break
    return escolhidas


def selecionar(cfg: dict, agora: datetime, n: int, termos_por_loja: int = 6,
               log=print) -> list[Oferta]:
    """Busca, filtra e escolhe as n melhores ofertas, já com link de afiliado."""
    dia = agora.strftime("%Y-%m-%d")
    filtros = cfg["filtros"]

    historico = _ler(caminho_historico(), {})
    limite = (agora - timedelta(days=cfg["agenda"]["nao_repetir_por_dias"])).strftime("%Y-%m-%d")

    lojas = lojas_ativas(cfg)
    if not lojas:
        raise RuntimeError("nenhuma loja configurada (faltam as chaves de acesso)")

    rnd = random.Random(dia)
    candidatas: list[Oferta] = []
    for loja in lojas:
        termos = rnd.sample(cfg["palavras_chave"], min(termos_por_loja, len(cfg["palavras_chave"])))
        for termo in termos:
            try:
                achadas = LOJAS[loja].buscar(termo)
            except Exception as e:  # uma busca ruim não derruba o dia
                log(f"  ! {loja} '{termo}': {e}")
                continue
            boas = 0
            for o in achadas:
                if historico.get(o.chave, "") >= limite:
                    continue
                if passa_filtros(o, filtros) is None:
                    candidatas.append(o)
                    boas += 1
            log(f"  {loja} '{termo}': {len(achadas)} achadas, {boas} passaram nos filtros")

    escolhidas = []
    for o in escolher(candidatas, n * 2):
        if o.loja == "mercadolivre":
            if not mercadolivre.gera_link():
                continue
            try:
                o.link = mercadolivre.link_afiliado(o.extra["permalink"])
            except Exception as e:
                log(f"  ! link ML {o.id}: {e}")
                continue
        escolhidas.append(o)
        if len(escolhidas) >= n:
            break
    return escolhidas


def planejar(cfg: dict, agora: datetime | None = None, n: int | None = None,
             log=print) -> list[dict]:
    fuso = ZoneInfo(cfg["agenda"]["fuso"])
    agora = agora or datetime.now(fuso)
    dia = agora.strftime("%Y-%m-%d")
    escolhidas = selecionar(cfg, agora, n or cfg["agenda"]["ofertas_por_dia"], log=log)
    horas = horarios_do_dia(agora, len(escolhidas), cfg["agenda"]["hora_inicio"],
                            cfg["agenda"]["hora_fim"], semente=int(dia.replace("-", "")))
    fila = [{"horario": h.isoformat(), "status": "pendente", "oferta": o.para_dict()}
            for h, o in zip(horas, escolhidas)]
    _gravar(caminho_fila(dia), fila)
    log(f"Fila de {dia}: {len(fila)} ofertas")
    return fila


# ---------------------------------------------------------------- conferir e postar

def conferir(o: Oferta, filtros: dict) -> tuple[Oferta | None, str]:
    """Consulta o preço na hora. Devolve (oferta atualizada, motivo se for cancelar)."""
    atual = LOJAS[o.loja].preco_atual(o)
    if atual is None:
        return None, "produto indisponível ou oferta encerrada"
    subiu = (atual.preco - o.preco) / o.preco * 100
    if subiu > filtros.get("variacao_preco_maxima", 0):
        return None, f"preço subiu de {legenda.reais(o.preco)} para {legenda.reais(atual.preco)}"
    if atual.desconto < filtros.get("desconto_minimo", 0):
        return None, f"desconto caiu para {atual.desconto}%"
    atual.link = atual.link or o.link
    return atual, ""


def postar(cfg: dict, agora: datetime | None = None, enviar: bool = True,
           destino: str | None = None, log=print) -> dict | None:
    fuso = ZoneInfo(cfg["agenda"]["fuso"])
    agora = agora or datetime.now(fuso)
    dia = agora.strftime("%Y-%m-%d")
    fila = _ler(caminho_fila(dia), [])
    historico = _ler(caminho_historico(), {})

    for item in fila:
        if item["status"] != "pendente" or datetime.fromisoformat(item["horario"]) > agora:
            continue
        o = Oferta.de_dict(item["oferta"])
        try:
            atual, motivo = conferir(o, cfg["filtros"])
        except Exception as e:
            item["status"], item["motivo"] = "erro", f"conferência de preço falhou: {e}"
            log(f"! {o.chave}: {item['motivo']}")
            continue
        if atual is None:
            item["status"], item["motivo"] = "cancelada", motivo
            log(f"- {o.chave}: cancelada ({motivo})")
            continue

        texto = legenda.montar(atual)
        if enviar:
            whatsapp.enviar(texto, atual.imagem, destino)
            item["status"] = "postada"
            historico[o.chave] = dia
        else:
            item["status"] = "pendente"  # simulação não consome a fila
        item["postada_em"] = agora.isoformat()
        item["legenda"] = texto
        item["oferta"] = atual.para_dict()
        log(("POSTADA" if enviar else "SIMULAÇÃO") + f" {o.chave}\n{texto}\n")
        if enviar:
            _gravar(caminho_fila(dia), fila)
            _gravar(caminho_historico(), historico)
        return item  # uma oferta por execução, para espaçar as mensagens

    if enviar:
        _gravar(caminho_fila(dia), fila)
    log("Nada para postar agora.")
    return None
