# Grupinho da Bia

Grupo de ofertas no WhatsApp com links de afiliado. O Claude busca os produtos em promoção, gera os links de afiliado, escreve uma legenda curta e posta no grupo todos os dias.

## Como a rotina funciona

Todo dia, das 7h às 22h:

1. **A cada 30 minutos, buscar as ofertas** em todo o setor de casa e cozinha (utensílios, eletrodomésticos, cama, mesa e banho, limpeza, organização, decoração, iluminação, móveis), nas categorias e em cerca de 80 palavras-chave.
2. **Filtrar:** fica tudo que estiver com desconto acima de 5%, de R$ 10 a R$ 100.000, em estoque. O resultado é a "vitrine", ordenada pelo maior desconto (vendas e avaliação desempatam).
3. **A cada 5 minutos, postar** a melhor oferta da vitrine:
   - confere o preço na hora; se o desconto caiu para 5% ou menos, ou o produto sumiu, pula para a próxima;
   - gera o link de afiliado;
   - escreve a legenda curta, com preço antigo, preço novo e o link:
     > A TV que faltava na sua sala!
     > De ~R$ 2.799,00~ por *R$ 1.899,00* (32% OFF)
     > 👉 https://link-de-afiliado
4. **Repetição:** o mesmo produto pode voltar, inclusive no dia seguinte. Ele só não repete dentro de 12 horas, a não ser que o preço tenha caído pelo menos mais 3% (e já tenha passado 1 hora).

## O que precisa ser providenciado

**1. Contas de afiliado**
- Shopee Afiliados: https://affiliate.shopee.com.br (a mais fácil de automatizar)
- Mercado Livre Afiliados: https://www.mercadolivre.com.br/afiliados
- Amazon Associados: https://associados.amazon.com.br (a busca automática costuma ser liberada só depois das primeiras vendas)
- Parceiro Magalu: https://www.parceiromagalu.com.br

Recomendação: começar com Shopee e Mercado Livre.

**2. Forma de postar no WhatsApp**
- Serviço não oficial, como Z-API (https://www.z-api.io) ou Evolution API (gratuita, precisa de servidor). Conecta um número por QR Code. Há risco de bloqueio, então usar um chip só para o grupo, nunca o número pessoal.
- Alternativa ou reserva: canal no Telegram, que tem robô oficial, gratuito e sem risco de bloqueio.

**3. Chaves de acesso**
As chaves são cadastradas por um formulário seguro do ambiente, nunca coladas no chat nem gravadas neste repositório.

## Cuidados

- **Preço certo:** conferir o preço na hora de postar. Oferta com preço errado gera reclamação e pode cair no Código de Defesa do Consumidor.
- **Aviso de afiliado:** informar na descrição do grupo que os links são de afiliado, como recomenda o CONAR.
- **Postagem direta:** não há aprovação manual. A segurança vem da conferência de preço na hora de cada envio: a legenda sempre sai com o preço do momento, e a oferta é pulada se o desconto caiu para 5% ou menos ou o produto sumiu.
- **Volume e bloqueio:** a cada 5 minutos das 7h às 22h são até 180 mensagens por dia. É bastante para um serviço não oficial como a Z-API, e aumenta o risco de o WhatsApp bloquear o chip. Se acontecer, dá para aumentar `postar_a_cada_minutos` no `config.json`.

## Decisões tomadas

| Pergunta | Decisão |
|---|---|
| Nicho | Casa e cozinha, todo o setor (não só alguns produtos) |
| Filtro | Desconto acima de 5%, de R$ 10 a R$ 100.000 |
| Ritmo | Das 7h às 22h: busca a cada 30 min, posta a cada 5 min |
| Repetição | Pode repetir; espera 12h, ou menos se o preço cair |
| Lojas | Shopee e Mercado Livre |
| Canal | WhatsApp pela Z-API, com um chip só para o grupo |
| Aprovação | Posta direto, com conferência de preço na hora |

## Como funciona o código

```
config.json              palavras-chave, categorias, filtros e horários
achadinhos/shopee.py     busca na Shopee Afiliados (já devolve o link de afiliado)
achadinhos/mercadolivre.py  busca no Mercado Livre e gera o link de afiliado
achadinhos/legenda.py    legenda curta: gancho, nome, De/Por e link
achadinhos/whatsapp.py   envio pela Z-API (foto + legenda)
achadinhos/rotina.py     buscar (vitrine), postar a melhor oferta, ficar ligado o dia todo
data/vitrine.json        ofertas da última busca (refeita a cada 30 min, fora do git)
data/historico.json      última vez que cada produto foi postado e a que preço
data/postagens/AAAA-MM-DD.json   tudo o que foi postado no dia
.github/workflows/rotina.yml  agenda automática
```

Tudo isso é ajustável no `config.json` (`filtros` e `agenda`).

**Categorias:** no Mercado Livre a busca já varre as categorias Casa, Móveis e Decoração (`MLB1574`) e Eletrodomésticos (`MLB5726`). Na Shopee, depois que o acesso for liberado, rode `python -m achadinhos categorias` e coloque os ids que mais aparecem em `shopee_categorias`. Enquanto isso, a Shopee é varrida pelas palavras-chave.

Comandos:

```bash
python -m achadinhos status       # quais chaves estão configuradas
python -m achadinhos teste        # 5 ofertas reais, preço conferido, só mostra as legendas
python -m achadinhos teste --enviar --destino ID_DO_GRUPO_DE_TESTE
python -m achadinhos grupos       # lista os grupos do chip, para achar o id
python -m achadinhos buscar       # atualiza a vitrine
python -m achadinhos postar       # posta a melhor oferta agora
python -m achadinhos rodar        # fica ligado até as 22h (busca a cada 30 min, posta a cada 5)
python -m achadinhos categorias   # ids de categoria da Shopee para casa e cozinha
python -m unittest discover -s tests -t .
```

## Agenda automática

O arquivo `.github/workflows/rotina.yml` roda no GitHub Actions (gratuito, porque o repositório é público). Como cada execução do GitHub dura no máximo 6 horas, o dia é dividido em 3 turnos que começam às 7h, 12h e 17h. Cada turno fica ligado por 5h30, e o seguinte espera na fila e assume logo depois. O GitHub às vezes atrasa o início em alguns minutos. A agenda só liga quando:

1. o código estiver no branch `main` (o GitHub só agenda tarefas no branch principal);
2. as chaves estiverem cadastradas em **Settings > Secrets and variables > Actions > Secrets**, que é um formulário seguro do próprio GitHub;
3. a variável `ROTINA_LIGADA` estiver como `sim` na aba **Variables** do mesmo lugar. Para pausar tudo, basta trocar para `nao`.

Para o teste com 5 ofertas reais antes de ligar: aba **Actions > Rotina de ofertas > Run workflow**, ação `teste`. As legendas aparecem no log e nada é enviado ao grupo.

Chaves usadas:

| Nome | De onde vem |
|---|---|
| `SHOPEE_APP_ID`, `SHOPEE_SECRET` | Shopee Afiliados > Open API |
| `ML_CLIENT_ID`, `ML_CLIENT_SECRET` | aplicativo criado em developers.mercadolivre.com.br (o acesso de 6h é renovado sozinho) |
| `ML_LINK_PARAMS` | parâmetros de rastreio do link de afiliado do Mercado Livre, copiados de um link de exemplo (veja abaixo) |
| `ML_LINK_API_URL`, `ML_LINK_API_KEY` | alternativa: serviço externo que gera o link de afiliado |
| `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN` | painel da Z-API |
| `WHATSAPP_GRUPO_ID` | id do grupo, achado com `python -m achadinhos grupos` |

**Mercado Livre:** o Mercado Livre não tem uma API aberta para gerar o link de afiliado; o caminho oficial é o Gerador de Links do Portal do Afiliado. Por isso o robô copia os parâmetros de rastreio de um link de exemplo (como `matt_tool` e `matt_word`) e cola em cada produto. Esses parâmetros ficam em `ml_link_params` no `config.json` (a variável `ML_LINK_PARAMS`, se existir, tem prioridade). Se o Gerador de Links devolver só um link curto (`mercadolivre.com/sec/...`), abra esse link no navegador e copie o endereço longo em que ele termina. Sem esses parâmetros, só a Shopee posta.

## Texto para a descrição do grupo

O texto completo, com aviso de afiliado, responsabilidade da loja, segurança e regras, está em [`marca/BIO.md`](marca/BIO.md).

## Identidade visual

Logo, paleta, fontes e peças para redes sociais ficam na pasta [`marca/`](marca/). As imagens prontas estão em `marca/png`. Para refazer depois de mudar `marca/pecas.html`, rode `node marca/exportar.js`.
