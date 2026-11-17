# Achadinhos da Bia

Grupo de ofertas no WhatsApp com links de afiliado. O Claude busca os produtos em promoção, gera os links de afiliado, escreve uma legenda curta e posta no grupo todos os dias.

## Como a rotina funciona

Todo dia, no horário definido:

1. **Buscar as ofertas** nas lojas em que há conta de afiliado, dentro do nicho escolhido.
2. **Filtrar** por desconto mínimo (por exemplo, 20% ou mais), avaliação boa e produto em estoque.
3. **Gerar o link de afiliado** de cada produto.
4. **Escrever a legenda** curta, com preço antigo, preço novo e o link:
   > A TV que faltava na sua sala!
   > De R$ 2.799 por R$ 1.899
   > https://link-de-afiliado
5. **Postar no grupo**, espaçando as mensagens ao longo do dia (por exemplo, uma por hora).

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
- **Postagem direta:** não há aprovação manual. A segurança vem dos filtros e da conferência de preço na hora de cada envio: se o preço subiu mais de 3%, o desconto caiu abaixo do mínimo ou o produto sumiu, a oferta é cancelada e não vai para o grupo.

## Decisões tomadas

| Pergunta | Decisão |
|---|---|
| Nicho | Casa e cozinha |
| Lojas | Shopee e Mercado Livre |
| Canal | WhatsApp pela Z-API, com um chip só para o grupo |
| Aprovação | Posta direto, com conferência de preço na hora |

## Como funciona o código

```
config.json              nicho, palavras-chave, filtros e horários
achadinhos/shopee.py     busca na Shopee Afiliados (já devolve o link de afiliado)
achadinhos/mercadolivre.py  busca no Mercado Livre e gera o link de afiliado
achadinhos/legenda.py    legenda curta: gancho, nome, De/Por e link
achadinhos/whatsapp.py   envio pela Z-API (foto + legenda)
achadinhos/rotina.py     planejar a fila do dia e postar uma oferta por vez
data/fila/AAAA-MM-DD.json   fila do dia (status de cada oferta)
data/historico.json      o que já foi postado (não repete por 14 dias)
.github/workflows/rotina.yml  agenda automática
```

Filtros atuais (em `config.json`): desconto de 20% ou mais, avaliação 4,5 ou mais, pelo menos 50 vendas, até R$ 800. São 10 ofertas por dia, espalhadas entre 9h e 21h.

Comandos:

```bash
python -m achadinhos status       # quais chaves estão configuradas
python -m achadinhos teste        # 5 ofertas reais, preço conferido, só mostra as legendas
python -m achadinhos teste --enviar --destino ID_DO_GRUPO_DE_TESTE
python -m achadinhos grupos       # lista os grupos do chip, para achar o id
python -m achadinhos planejar     # monta a fila do dia
python -m achadinhos postar       # posta a próxima oferta cujo horário chegou
python -m unittest discover -s tests -t .
```

## Agenda automática

O arquivo `.github/workflows/rotina.yml` roda no GitHub Actions: às 8h monta a fila e, a cada 30 minutos entre 9h e 21h30, posta a próxima oferta. Ele só liga quando:

1. o código estiver no branch `main` (o GitHub só agenda tarefas no branch principal);
2. as chaves estiverem cadastradas em **Settings > Secrets and variables > Actions > Secrets**, que é um formulário seguro do próprio GitHub;
3. a variável `ROTINA_LIGADA` estiver como `sim` na aba **Variables** do mesmo lugar. Para pausar tudo, basta trocar para `nao`.

Para o teste com 5 ofertas reais antes de ligar: aba **Actions > Rotina de ofertas > Run workflow**, ação `teste`. As legendas aparecem no log e nada é enviado ao grupo.

Chaves usadas:

| Nome | De onde vem |
|---|---|
| `SHOPEE_APP_ID`, `SHOPEE_SECRET` | Shopee Afiliados > Open API |
| `ML_ACCESS_TOKEN` | aplicativo criado em developers.mercadolivre.com.br |
| `ML_LINK_API_URL`, `ML_LINK_API_KEY` | serviço que gera o link de afiliado do Mercado Livre (veja abaixo) |
| `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN` | painel da Z-API |
| `WHATSAPP_GRUPO_ID` | id do grupo, achado com `python -m achadinhos grupos` |

**Mercado Livre:** o Mercado Livre não tem uma API aberta para gerar o link de afiliado; o caminho oficial é o Gerador de Links do Portal do Afiliado. Por isso o gerador de link é configurável. Enquanto `ML_LINK_API_URL` não estiver configurada, só a Shopee posta.

## Texto sugerido para a descrição do grupo

> Achadinhos da Bia 🏠 Ofertas de casa e cozinha todos os dias. Os links do grupo são links de afiliado: posso receber uma comissão pelas compras, sem custo extra para você. Os preços são conferidos na hora do envio, mas podem mudar a qualquer momento na loja.
