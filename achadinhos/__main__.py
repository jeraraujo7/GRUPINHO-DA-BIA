"""Uso:
  python -m achadinhos status                  mostra quais chaves estão configuradas
  python -m achadinhos teste [--enviar] [--destino ID] [-n 5]
                                               busca 5 ofertas reais, confere o preço e mostra as legendas;
                                               com --enviar, manda para --destino (um grupo de teste)
  python -m achadinhos planejar                monta a fila do dia (data/fila/AAAA-MM-DD.json)
  python -m achadinhos postar [--simular]      posta a próxima oferta cujo horário já chegou
  python -m achadinhos grupos                  lista os grupos do chip na Z-API (para achar o id)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from . import legenda, mercadolivre, rotina, shopee, whatsapp


def cmd_status(cfg, _):
    print(f"Nicho: {cfg['nicho']}")
    print(f"Shopee .............. {'ok' if shopee.configurada() else 'faltam SHOPEE_APP_ID / SHOPEE_SECRET'}")
    print(f"Mercado Livre busca . {'ok' if mercadolivre.configurada() else 'falta ML_ACCESS_TOKEN'}")
    print(f"Mercado Livre link .. {'ok' if mercadolivre.gera_link() else 'falta ML_LINK_API_URL'}")
    print(f"WhatsApp (Z-API) .... {'ok' if whatsapp.configurado() else 'faltam ZAPI_* / WHATSAPP_GRUPO_ID'}")


def cmd_teste(cfg, a):
    agora = datetime.now(ZoneInfo(cfg["agenda"]["fuso"]))
    ofertas = rotina.selecionar(cfg, agora, a.n)
    print(f"\n{len(ofertas)} ofertas selecionadas\n" + "=" * 40)
    for o in ofertas:
        atual, motivo = rotina.conferir(o, cfg["filtros"])
        if atual is None:
            print(f"[cancelada] {o.nome[:50]}: {motivo}\n")
            continue
        texto = legenda.montar(atual)
        print(texto + "\n" + "-" * 40)
        if a.enviar:
            whatsapp.enviar(texto, atual.imagem, a.destino)


def cmd_planejar(cfg, _):
    rotina.planejar(cfg)


def cmd_postar(cfg, a):
    rotina.postar(cfg, enviar=not a.simular)


def cmd_grupos(_, __):
    for g in whatsapp.listar_grupos():
        print(g.get("phone") or g.get("id"), "-", g.get("name") or g.get("subject"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="achadinhos")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    t = sub.add_parser("teste")
    t.add_argument("-n", type=int, default=5)
    t.add_argument("--enviar", action="store_true")
    t.add_argument("--destino")
    sub.add_parser("planejar")
    po = sub.add_parser("postar")
    po.add_argument("--simular", action="store_true")
    sub.add_parser("grupos")
    a = p.parse_args(argv)

    if a.cmd == "teste" and a.enviar and not a.destino:
        sys.exit("No teste, --enviar exige --destino (um grupo de teste), para não postar no grupo real.")

    cfg = rotina.carregar_config()
    {"status": cmd_status, "teste": cmd_teste, "planejar": cmd_planejar,
     "postar": cmd_postar, "grupos": cmd_grupos}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()
