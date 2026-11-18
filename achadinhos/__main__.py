"""Uso:
  python -m achadinhos status                quais chaves estão configuradas
  python -m achadinhos teste [-n 5] [--enviar --destino ID]
                                             busca de verdade, confere o preço e mostra n legendas;
                                             com --enviar manda para um grupo de TESTE
  python -m achadinhos buscar                atualiza a vitrine (data/vitrine.json)
  python -m achadinhos postar [--simular]    posta a melhor oferta da vitrine agora
  python -m achadinhos rodar [--horas 5.5]   fica ligado: busca a cada 30 min, posta a cada 5 min
  python -m achadinhos categorias            ids de categoria da Shopee mais comuns em casa e cozinha
  python -m achadinhos grupos                grupos do chip na Z-API (para achar o id)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import timedelta

from . import legenda, mercadolivre, rotina, shopee, whatsapp


def cmd_status(cfg, _):
    print(f"Nicho: {cfg['nicho']}")
    print(f"Shopee .............. {'ok' if shopee.configurada() else 'faltam SHOPEE_APP_ID / SHOPEE_SECRET'}")
    print(f"Mercado Livre busca . {'ok' if mercadolivre.configurada() else 'faltam ML_CLIENT_ID / ML_CLIENT_SECRET'}")
    print(f"Mercado Livre link .. {'ok' if mercadolivre.gera_link() else 'falta ML_LINK_PARAMS'}")
    print(f"WhatsApp (Z-API) .... {'ok' if whatsapp.configurado() else 'faltam ZAPI_* / WHATSAPP_GRUPO_ID'}")


def cmd_teste(cfg, a):
    ofertas = rotina.buscar(cfg)
    print(f"\nMostrando as {a.n} melhores\n" + "=" * 40)
    mostradas = 0
    for o in ofertas:
        if mostradas >= a.n:
            break
        atual, motivo = rotina.conferir(o, cfg["filtros"])
        if atual is None:
            print(f"[pulada] {o.nome[:50]}: {motivo}\n")
            continue
        if atual.loja == "mercadolivre":
            if not mercadolivre.gera_link():
                print(f"[sem gerador de link ML] {o.nome[:50]}\n")
                continue
            atual.link = mercadolivre.link_afiliado(atual.extra.get("permalink") or o.extra["permalink"])
        texto = legenda.montar(atual)
        print(texto + "\n" + "-" * 40)
        mostradas += 1
        if a.enviar:
            whatsapp.enviar(texto, atual.imagem, a.destino)


def cmd_buscar(cfg, _):
    rotina.buscar(cfg)


def cmd_postar(cfg, a):
    if not rotina.caminho_vitrine().exists():
        rotina.buscar(cfg)
    rotina.postar(cfg, enviar=not a.simular)


def cmd_rodar(cfg, a):
    ate = rotina.agora_em(cfg) + timedelta(hours=a.horas) if a.horas else None
    rotina.rodar(cfg, ate=ate, log=lambda *x: print(*x, flush=True))


def cmd_categorias(cfg, _):
    cont = Counter()
    for termo in cfg["palavras_chave"]:
        try:
            for o in shopee.buscar(termo, paginas=1):
                cont.update(o.extra.get("categorias") or [])
        except Exception as e:
            print(f"! {termo}: {e}")
    print("id da categoria  -> quantos produtos de casa e cozinha caíram nela")
    for cat, n in cont.most_common(30):
        print(f"{cat:>15}  -> {n}")
    print('\nColoque os ids de nível 1 (os que mais aparecem) em "shopee_categorias" no config.json.')


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
    sub.add_parser("buscar")
    po = sub.add_parser("postar")
    po.add_argument("--simular", action="store_true")
    r = sub.add_parser("rodar")
    r.add_argument("--horas", type=float, help="para depois de tantas horas (padrão: até o fim do dia)")
    sub.add_parser("categorias")
    sub.add_parser("grupos")
    a = p.parse_args(argv)

    if a.cmd == "teste" and a.enviar and not a.destino:
        sys.exit("No teste, --enviar exige --destino (um grupo de teste), para não postar no grupo real.")

    cfg = rotina.carregar_config()
    {"status": cmd_status, "teste": cmd_teste, "buscar": cmd_buscar, "postar": cmd_postar,
     "rodar": cmd_rodar, "categorias": cmd_categorias, "grupos": cmd_grupos}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()
