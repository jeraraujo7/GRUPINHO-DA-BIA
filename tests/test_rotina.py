import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from achadinhos import legenda, rotina, shopee
from achadinhos.oferta import Oferta

FUSO = ZoneInfo("America/Sao_Paulo")


def oferta(i=1, preco=249.9, antigo=399.9, termo="air fryer", loja="shopee", **kw):
    return Oferta(loja=loja, id=str(i), nome=f"Air Fryer Mondial 4L Family {i}", preco=preco,
                  preco_antigo=antigo, link=f"https://s.shopee.com.br/x{i}",
                  imagem="https://img/x.jpg", avaliacao=4.8, vendas=900, palavra_chave=termo, **kw)


class TestLegenda(unittest.TestCase):
    def test_reais(self):
        self.assertEqual(legenda.reais(1899.9), "R$ 1.899,90")
        self.assertEqual(legenda.reais(49), "R$ 49,00")

    def test_montar(self):
        texto = legenda.montar(oferta())
        linhas = texto.splitlines()
        frases = [f for termos, fs in legenda.GANCHOS if "air fryer" in termos for f in fs]
        self.assertIn(linhas[0], frases)
        self.assertEqual(linhas[2], "De ~R$ 399,90~ por *R$ 249,90* (38% OFF)")
        self.assertEqual(linhas[3], "👉 https://s.shopee.com.br/x1")

    def test_nome_curto(self):
        n = legenda.nome_curto("[ENVIO JÁ] Jogo de Panelas Antiaderente 10 Peças Indução Cabo Baquelite Tampa de Vidro")
        self.assertLessEqual(len(n), 61)
        self.assertFalse(n.startswith("["))


class TestShopee(unittest.TestCase):
    def test_assinatura(self):
        import hashlib
        esperado = hashlib.sha256(b"123" b"1577836800" b'{"query":"x"}' b"seg").hexdigest()
        self.assertEqual(shopee.assinatura("123", 1577836800, '{"query":"x"}', "seg"), esperado)

    def test_para_oferta(self):
        o = shopee._para_oferta({"itemId": 9, "productName": "Pote", "priceMin": "80.00",
                                 "priceMax": "80.00", "priceDiscountRate": 20, "ratingStar": "4.9",
                                 "sales": 120, "offerLink": "https://s.shopee.com.br/a"})
        self.assertEqual(o.preco_antigo, 100.0)
        self.assertEqual(o.desconto, 20)


class TestFiltrosEAgenda(unittest.TestCase):
    F = {"desconto_minimo": 20, "avaliacao_minima": 4.5, "vendas_minimas": 50,
         "preco_maximo": 800, "variacao_preco_maxima": 3}

    def test_filtros(self):
        self.assertIsNone(rotina.passa_filtros(oferta(), self.F))
        self.assertIn("desconto", rotina.passa_filtros(oferta(preco=390), self.F))

    def test_horarios_espalhados(self):
        dia = datetime(2026, 11, 18, 7, tzinfo=FUSO)
        hs = rotina.horarios_do_dia(dia, 10, 9, 21, semente=1)
        self.assertEqual(len(hs), 10)
        self.assertTrue(all(9 <= h.hour < 21 for h in hs))
        self.assertEqual(hs, sorted(hs))

    def test_escolher_alterna_e_limita_por_termo(self):
        cands = [oferta(i, termo="air fryer") for i in range(5)] + \
                [oferta(10 + i, termo="mop", loja="mercadolivre") for i in range(5)]
        esc = rotina.escolher(cands, 4)
        self.assertEqual([o.loja for o in esc], ["shopee", "mercadolivre"] * 2)


class TestPostar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(rotina, "DADOS", Path(self.tmp.name))
        self.p.start()
        self.cfg = {"agenda": {"fuso": "America/Sao_Paulo"}, "filtros": TestFiltrosEAgenda.F}
        self.agora = datetime(2026, 11, 18, 12, tzinfo=FUSO)
        fila = [
            {"horario": datetime(2026, 11, 18, 9, tzinfo=FUSO).isoformat(), "status": "pendente",
             "oferta": oferta(1).para_dict()},
            {"horario": datetime(2026, 11, 18, 10, tzinfo=FUSO).isoformat(), "status": "pendente",
             "oferta": oferta(2).para_dict()},
            {"horario": datetime(2026, 11, 18, 20, tzinfo=FUSO).isoformat(), "status": "pendente",
             "oferta": oferta(3).para_dict()},
        ]
        rotina._gravar(rotina.caminho_fila("2026-11-18"), fila)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_cancela_se_preco_subiu_e_posta_a_proxima(self):
        def atual(o):
            return oferta(int(o.id), preco=300 if o.id == "1" else o.preco)
        with mock.patch.object(shopee, "preco_atual", side_effect=atual), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            item = rotina.postar(self.cfg, self.agora, log=lambda *_: None)
        self.assertEqual(item["oferta"]["id"], "2")
        env.assert_called_once()
        fila = rotina._ler(rotina.caminho_fila("2026-11-18"), [])
        self.assertEqual([i["status"] for i in fila], ["cancelada", "postada", "pendente"])
        self.assertIn("preço subiu", fila[0]["motivo"])
        self.assertEqual(rotina._ler(rotina.caminho_historico(), {}), {"shopee:2": "2026-11-18"})

    def test_preco_caiu_atualiza_legenda(self):
        with mock.patch.object(shopee, "preco_atual", return_value=oferta(1, preco=199.9)), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            item = rotina.postar(self.cfg, self.agora, log=lambda *_: None)
        self.assertIn("*R$ 199,90*", item["legenda"])
        self.assertIn("*R$ 199,90*", env.call_args[0][0])

    def test_simular_nao_envia_nem_consome(self):
        with mock.patch.object(shopee, "preco_atual", side_effect=lambda o: o), \
             mock.patch("achadinhos.whatsapp.enviar") as env:
            rotina.postar(self.cfg, self.agora, enviar=False, log=lambda *_: None)
        env.assert_not_called()
        fila = rotina._ler(rotina.caminho_fila("2026-11-18"), [])
        self.assertTrue(all(i["status"] == "pendente" for i in fila))


if __name__ == "__main__":
    unittest.main()
