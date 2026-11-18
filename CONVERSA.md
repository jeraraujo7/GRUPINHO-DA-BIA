# Grupinho da Bia: resumo da conversa e onde paramos

Use este arquivo para continuar o trabalho em outra conversa. O plano técnico completo está no `README.md`.

- **Repositório:** github.com/jeraraujo7/GRUPINHO-DA-BIA (era ACHADINHOS-DA-BIA; o GitHub renomeou e redireciona o nome antigo)
- **Branch de trabalho:** `claude/cool-carson-lz7yd8` (ainda não foi juntado ao `main`)
- **Data:** 18/11/2026

## O que é o projeto

Grupo de ofertas no WhatsApp com links de afiliado. Um robô busca produtos de casa e cozinha em promoção, gera o link de afiliado, escreve uma legenda curta (gancho, nome, preço De/Por e link) e posta no grupo ao longo do dia.

## Decisões tomadas

| Assunto | Decisão |
|---|---|
| Onde fica o projeto | Só neste repositório. Nada vai para hive-site nem para Fuzza |
| Nicho | Casa e cozinha, todo o setor (utensílios, eletrodomésticos, cama, mesa e banho, limpeza, organização, decoração, iluminação, móveis, banheiro) |
| Lojas | Shopee e Mercado Livre |
| Canal | WhatsApp pela Z-API, com um chip só para o grupo, nunca o número pessoal |
| Aprovação | Posta direto, sem aprovação manual |
| Filtro | Desconto acima de 5%, de R$ 10 a R$ 100.000, sem mínimo de avaliação ou vendas |
| Horário | Das 7h às 22h (Brasília) |
| Ritmo | Busca as ofertas a cada 30 min e posta uma a cada 5 min (até cerca de 180 por dia) |
| Repetição | O produto pode repetir, inclusive no dia seguinte. Só não repete dentro de 12 h, a não ser que o preço caia mais 3% (e já tenha passado 1 h) |
| Preço | Conferido na hora de cada envio. A legenda sai com o preço do momento; se o desconto caiu para 5% ou menos, ou o produto sumiu, a oferta é pulada |
| Aviso de afiliado | Na descrição do grupo (texto pronto no README) |
| Chaves de acesso | Nunca no chat nem no repositório. Ficam nos Secrets do GitHub (Settings > Secrets and variables > Actions) |

## O que já está pronto

- **Código em Python**, na pasta `achadinhos/`:
  - `shopee.py`: busca na Open API de afiliados da Shopee, que já devolve o link de afiliado.
  - `mercadolivre.py`: busca no Mercado Livre. O acesso de 6 h é renovado sozinho com `ML_CLIENT_ID` e `ML_CLIENT_SECRET`.
  - `legenda.py`: monta a legenda.
  - `whatsapp.py`: envia pela Z-API.
  - `rotina.py`: monta a vitrine de ofertas e posta.
- **Configuração** em `config.json`: cerca de 80 palavras-chave, as categorias do Mercado Livre `MLB1574` e `MLB5726`, os filtros e os horários.
- **Agenda** em `.github/workflows/rotina.yml`: roda no GitHub Actions, gratuito porque o repositório é público. São 3 turnos de 5h30, começando às 7h, 12h e 17h.
  - A agenda só liga com a variável `ROTINA_LIGADA = sim`.
  - Rodando à mão, a ação `teste` mostra 5 legendas no log sem enviar nada.
- **Testes:** 12, todos passando (`python -m unittest discover -s tests -t .`).

## O que falta (próximos passos)

1. **Shopee:** a solicitação de afiliado foi feita, e o Jer termina a ativação depois. Quando a Open API for liberada:
   - cadastrar `SHOPEE_APP_ID` e `SHOPEE_SECRET` nos Secrets do GitHub;
   - rodar `python -m achadinhos categorias` e colocar os ids de categoria em `shopee_categorias` no `config.json`.
2. **Mercado Livre:** o Jer já é afiliado. Falta:
   - **Link de afiliado: pronto (18/11).** O Gerador de Links devolve links curtos `meli.la`. O endereço longo traz `matt_word=arajojefferson39&matt_tool=27581938`, que agora está em `ml_link_params` no `config.json` e é colado em cada produto. O `ref` do link de exemplo é próprio daquele link e não é usado. Conferir no primeiro teste se as vendas aparecem no Portal do Afiliado.
   - **Aplicativo:** criar em https://developers.mercadolivre.com.br (Meus aplicativos > Criar aplicativo; se pedir endereço de retorno, usar `https://github.com`). Depois cadastrar `ML_CLIENT_ID` e `ML_CLIENT_SECRET` nos Secrets do GitHub.
3. **Z-API:** criar a instância, conectar o chip do grupo pelo QR Code e cadastrar `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN` e `WHATSAPP_GRUPO_ID` (o id sai do comando `python -m achadinhos grupos`).
4. **Juntar o branch ao `main`:** o Claude pode abrir o pull request quando o Jer pedir.
5. **Teste com 5 ofertas reais:** em Actions > Rotina de ofertas > Run workflow, ação `teste`.
6. **Ligar a rotina:** criar a variável `ROTINA_LIGADA = sim`.

## Grupo no WhatsApp

- **Link de convite:** https://chat.whatsapp.com/JRY7yIMbOv609NylCljfsz
- **Link curto:** https://is.gd/grupinhodabia (criado no is.gd, sem conta; não dá para editar o destino. Se o link do grupo mudar, crie outro link curto)
- **QR Code:** `marca/png/qr-code-grupo.png`, aponta direto para o link do WhatsApp. Para refazer: `python marca/gerar_qr.py <link>`
- Use nos convites (post, story, bio do Instagram). Se o link vazar para spam, dá para gerar outro em Dados do grupo > Convidar via link > Redefinir link, e atualizar aqui.
- O id técnico do grupo (`WHATSAPP_GRUPO_ID`) é outro: sai do comando `python -m achadinhos grupos` depois que a Z-API estiver conectada.
- Pasta do cliente no Drive: G:\Meu Drive\CLIENTES\GRUPINHO DA BIA (subpastas Marca, Textos e Código).

## Identidade visual (18/11)

- Nome: **Grupinho da Bia**. Logo: etiqueta de preço inclinada com "bia", no azul de ágata.
- Paleta: Ágata `#1D44B8`, Ágata escuro `#102C7A`, Gema `#FFC83D`, Melancia `#F2445A` (só no selo de desconto), Louça `#F2F5FB`, Grafite `#151B2E`. Fontes: Bricolage Grotesque e Figtree.
- Tudo na pasta `marca/`: `pecas.html` (fonte das peças), `exportar.js`, `png/` (foto do grupo, logos, card de oferta, post e story de convite, capas de destaque), `guia.html` e `BIO.md` (descrição do grupo com aviso de afiliado e proteções).
- Guia publicado: https://claude.ai/artifact/1qiqZzJeruZfMSzGSAfxAh

## Observações

- **Acesso ao computador:** a sessão do Claude na nuvem não acessa o computador nem o navegador do Jer. Login e criação de contas ou aplicativos precisam ser feitos por ele, ou numa sessão do Claude Desktop rodando no computador dele.
- **Rede da sessão na nuvem:** ela bloqueia o site do Mercado Livre, então a busca do Mercado Livre não foi testada de verdade. O teste real vai acontecer no GitHub Actions.
- **Risco de bloqueio:** 180 mensagens por dia por um serviço não oficial aumentam o risco de o WhatsApp bloquear o chip. Se acontecer, basta aumentar `postar_a_cada_minutos` no `config.json`.
- **Dados públicos:** o repositório é público, então a vitrine, o histórico e as postagens gravados em `data/` ficam visíveis. Nenhuma chave vai para lá.

## Para começar a próxima conversa

> Projeto Achadinhos da Bia, repositório jeraraujo7/GRUPINHO-DA-BIA, branch claude/cool-carson-lz7yd8. Leia o CONVERSA.md e o README.md. [Cole aqui o link de exemplo do Mercado Livre, ou diga o que já foi feito da lista "O que falta".]
