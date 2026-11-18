import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from achadinhos import legenda, rotina, shopee
from achadinhos.oferta import Oferta

FUSO = ZoneInfo("America/Sao_Paulo")
CFG = {
    "palavras_chave": ["air fryer", "mop"],
    "filtros": {"desconto_acima_de": 5, "preco_minimo": 10, "preco_maximo": 100000,
                "avaliacao_minima": 0, "vendas_minimas": 0},
    "agenda": {"fuso": "America/Sao_Paulo", "hora_inicio": 7, "hora_fim": 22,
               "buscar_a_cada_minutos": 30, "postar_a_cada_minutos": 5, "repetir_apos_horas": 12},
    "lojas": {"shopee": True, "mercadolivre": False},
}


def oferta(i=1, preco=249.9, antigo=399.9, termo="air fryer", loja="shopee", vendas=900):
    return Oferta(loja=loja, id=str(i), nome=f"Air Fryer Mondial 4L Family {i}", preco=preco,
                  preco_antigo=antigo, link=f"https://s.shopee.com.br/x{i}",
                  imagem="https://img/x.jpg", avaliacao=4.8, vendas=vendas, palavra_chave=termo)


class TestLegenda(unittest.TestCase):
    def test_reais(self):
        self.assertEqual(legenda.reais(1899.9), "R$ 1.899,90")
        self.assertEqual(legenda.reais(85000), "R$ 85.000,00")

    def test_montar(self):
        linhas = legenda.montar(oferta()).splitlines()
        frases = [f for termos, fs in legenda.GANCHOS if "air fryer" in termos for f in fs]
        self.assertIn(linhas[0], frases)
        self.assertEqual(linhas[2], "De ~R$ 399,90~ por *R$ 249,90* (38% OFF)")
        self.assertEqual(linhas[3], "👉 https://s.shopee.com.br/x1")


class TestShopee(unittest.TestCase):
    def test_assinatura(self):
        esperado = hashlib.sha256(b"123" b"1577836800" b'{"query":"x"}' b"seg").hexdigest()
        self.assertEqual(shopee.assinatura("123", 1577836800, '{"query":"x"}', "seg"), esperado)

    def test_para_oferta(self):
        o = shopee._para_oferta({"itemId": 9, "productName": "Pote", "priceMin": "80.00",
                                 "priceMax": "80.00", "priceDiscountRate": 20,
                                 "offerLink": "https://s.shopee.com.br/a"})
        self.assertEqual((o.preco_antigo, o.desconto), (100.0, 20))


class TestFiltros(unittest.TestCase):
    F = CFG["filtros"]

    def test_acima_de_5_por_cento(self):
        self.assertIsNone(rotina.passa_filtros(oferta(preco=94, antigo=100), self.F))
        self.assertIsNotNone(rotina.passa_filtros(oferta(preco=95, antigo=100), self.F))

    def test_sem_limite_de_valor(self):
        self.assertIsNone(rotina.passa_filtros(oferta(preco=85000, antigo=99000), self.F))
        self.assertIsNotNone(rotina.passa_filtros(oferta(preco=8, antigo=12), self.F))


class TestRepeticao(unittest.TestCase):
    agora = datetime(2026, 11, 18, 12, tzinfo=FUSO)

    def hist(self, horas_atras, preco):
        return {"shopee:1": {"em": (self.agora - timedelta(hours=horas_atras)).isoformat(), "preco": preco}}

    def test_regras(self):
        o = oferta(preco=249.9)
        self.assertFalse(rotina.em_espera(o, {}, self.agora, 12))
        self.assertTrue(rotina.em_espera(o, self.hist(2, 249.9), self.agora, 12))
        self.assertFalse(rotina.em_espera(o, self.hist(13, 249.9), self.agora, 12))  # dia anterior
        self.assertFalse(rotina.em_espera(o, self.hist(2, 299.9), self.agora, 12))   # preço caiu
        self.assertTrue(rotina.em_espera(o, self.hist(0.5, 299.9), self.agora, 12))  # cedo demais


class ComPasta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(rotina, "DADOS", Path(self.tmp.name))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()


class TestBuscarEPostar(ComPasta):
    agora = datetime(2026, 11, 18, 12, tzinfo=FUSO)

    def test_buscar_filtra_e_ordena(self):
        achadas = [oferta(1, preco=97, antigo=100), oferta(2, preco=50, antigo=100),
                   oferta(3, preco=80, antigo=100)]
        with mock.patch.object(shopee, "configurada", return_value=True), \
             mock.patch.object(shopee, "buscar", return_value=achadas):
            vit = rotina.buscar(CFG, self.agora, log=lambda *_: None)
        self.assertEqual([o.id for o in vit], ["2", "3"])

    def _vitrine(self, *ofertas):
        rotina._gravar(rotina.caminho_vitrine(), {"ofertas": [o.para_dict() for o in ofertas]})

    def test_pula_se_desconto_sumiu_e_posta_a_proxima(self):
        self._vitrine(oferta(1, preco=50, antigo=100), oferta(2, preco=80, antigo=100, termo="mop"))

        def atual(o):
            return oferta(1, preco=99, antigo=100) if o.id == "1" else o
        with mock.patch.object(shopee, "preco_atual", side_effect=atual), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            item = rotina.postar(CFG, self.agora, log=lambda *_: None)
        self.assertEqual(item["chave"], "shopee:2")
        env.assert_called_once()
        hist = rotina._ler(rotina.caminho_historico(), {})
        self.assertEqual(list(hist), ["shopee:2"])
        ids = [d["id"] for d in rotina._ler(rotina.caminho_vitrine(), {})["ofertas"]]
        self.assertEqual(ids, ["2"])

    def test_nao_repete_logo_em_seguida(self):
        self._vitrine(oferta(1, preco=50, antigo=100))
        with mock.patch.object(shopee, "preco_atual", side_effect=lambda o: o), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            rotina.postar(CFG, self.agora, log=lambda *_: None)
            rotina.postar(CFG, self.agora + timedelta(minutes=5), log=lambda *_: None)
        self.assertEqual(env.call_count, 1)

    def test_simular_nao_envia(self):
        self._vitrine(oferta(1, preco=50, antigo=100))
        with mock.patch.object(shopee, "preco_atual", side_effect=lambda o: o), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            rotina.postar(CFG, self.agora, enviar=False, log=lambda *_: None)
        env.assert_not_called()
        self.assertEqual(rotina._ler(rotina.caminho_historico(), {}), {})


class TestRodar(ComPasta):
    def test_ritmo_do_dia(self):
        """De 6h50 a 9h: espera até 7h, busca a cada 30 min e posta a cada 5 min."""
        t = [datetime(2026, 11, 18, 6, 50, tzinfo=FUSO)]

        def dormir(seg):
            t[0] += timedelta(seconds=seg)
        cfg = {**CFG, "agenda": {**CFG["agenda"], "hora_fim": 9}}
        with mock.patch.object(rotina, "buscar") as b, \
             mock.patch.object(rotina, "postar", return_value={"ok": 1}) as p:
            n = rotina.rodar(cfg, relogio=lambda: t[0], dormir=dormir, log=lambda *_: None)
        self.assertEqual(n, 24)              # 7h00 ... 8h55
        self.assertEqual(b.call_count, 4)    # 7h00, 7h30, 8h00, 8h30
        self.assertEqual(p.call_args_list[0].args[1].hour, 7)


CARD_ML = """
<div class="poly-card__portada"><img class="poly-component__picture" src="https://http2.mlstatic.com/D_Q_NP_2X_849756-MLA112337335323_052026-AB.webp" alt="x"/></div>
<div class="poly-card__content"><h3><a href="https://www.mercadolivre.com.br/guarda-roupa/p/MLB70374494#polycard_client=x&amp;wid=MLB4752587193&amp;sid=y" class="poly-component__title poly-component__title--line-clamp-2">Guarda-roupa Casal 6 Portas</a></h3>
<s class="andes-money-amount andes-money-amount--previous" aria-label="Antes: 1704 reais com 90 centavos"></s>
<div class="poly-price__current"><span class="andes-money-amount" aria-label="1381 reais"></span></div>
<span class="poly-price__unit-description">no Pix</span><span class="poly-price__installments">ou 1502 reais</span></div>
<div class="poly-card__portada"><img class="poly-component__picture" src="a.webp"/></div>
<div class="poly-card__content"><h3><a href="https://produto.mercadolivre.com.br/MLB-5365991654-sofa-_JM" class="poly-component__title">Sofá 3 Lugares</a></h3>
<div class="poly-price__current"><span class="andes-money-amount" aria-label="789 reais"></span></div></div>
"""


class TestMercadoLivrePaginas(unittest.TestCase):
    def test_ler_pagina(self):
        from achadinhos import mercadolivre
        guarda, sofa = mercadolivre.ler_pagina(CARD_ML)
        self.assertEqual((guarda.id, guarda.preco, guarda.preco_antigo, guarda.desconto),
                         ("MLB4752587193", 1381.0, 1704.9, 19))
        self.assertTrue(guarda.extra["pix"])
        self.assertEqual(guarda.extra["permalink"], "https://www.mercadolivre.com.br/guarda-roupa/p/MLB70374494")
        self.assertEqual(guarda.imagem, "https://http2.mlstatic.com/D_NQ_NP_849756-MLA112337335323_052026-O.jpg")
        self.assertEqual((sofa.id, sofa.desconto, sofa.extra["pix"]), ("MLB5365991654", 0, False))
        self.assertIn("no Pix", legenda.montar(guarda))

    def test_pede_login(self):
        from achadinhos import mercadolivre
        resp = mock.MagicMock()
        resp.__enter__.return_value.geturl.return_value = "https://www.mercadolivre.com.br/gz/account-verification?go=x"
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(mercadolivre.PedeLogin):
                mercadolivre.baixar("https://www.mercadolivre.com.br/ofertas")

    def test_preco_atual_relendo_a_pagina(self):
        from achadinhos import mercadolivre
        with mock.patch.object(mercadolivre, "baixar", return_value=CARD_ML), \
             mock.patch.object(mercadolivre, "paginas", return_value=["u1"]):
            mercadolivre._cache.clear()
            o = mercadolivre.ler_pagina(CARD_ML)[0]
            o.link = "L"
            self.assertEqual(mercadolivre.preco_atual(o).link, "L")
            o.id = "MLB0"
            self.assertIsNone(mercadolivre.preco_atual(o))


if __name__ == "__main__":
    unittest.main()


class LinkMercadoLivre(unittest.TestCase):
    def test_cola_parametros_do_link_de_exemplo(self):
        import os
        from unittest import mock
        from achadinhos import mercadolivre
        exemplo = "https://www.mercadolivre.com.br/x/p/MLB1?matt_tool=111&matt_word=bia#pos"
        with mock.patch.dict(os.environ, {"ML_LINK_PARAMS": exemplo}, clear=False):
            self.assertTrue(mercadolivre.gera_link())
            link = mercadolivre.link_afiliado("https://produto.mercadolivre.com.br/MLB-2-panela?matt_tool=9&x=1")
        self.assertEqual(link, "https://produto.mercadolivre.com.br/MLB-2-panela?x=1&matt_tool=111&matt_word=bia")
