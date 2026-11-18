# Grupinho da Bia: resumo da conversa e onde paramos

Use este arquivo para continuar o trabalho em outra conversa. O plano técnico completo está no `README.md`.

- **Repositório:** github.com/jeraraujo7/GRUPINHO-DA-BIA (público)
- **Branch de trabalho:** `claude/cool-carson-lz7yd8` (ainda não foi juntado ao `main`)
- **Pasta do cliente no Drive:** G:\Meu Drive\CLIENTES\GRUPINHO DA BIA (subpastas Marca, Textos e Código)
- **Última atualização:** 18/11/2026

## O que é o projeto

Grupo de ofertas no WhatsApp com links de afiliado. Um robô busca produtos de casa e cozinha em promoção na Shopee e no Mercado Livre, gera o link de afiliado, escreve uma legenda curta (gancho, nome, preço De/Por e link) e posta no grupo ao longo do dia.

## Decisões tomadas

| Assunto | Decisão |
|---|---|
| Onde fica o projeto | Só neste repositório. Nada vai para hive-site nem para Fuzza |
| Nicho | Casa e cozinha, todo o setor (utensílios, eletro, cama, mesa e banho, limpeza, organização, decoração, iluminação, móveis, banheiro) |
| Lojas | Shopee e Mercado Livre |
| Canal | WhatsApp pela Z-API, com um chip só para o grupo, nunca o número pessoal |
| Aprovação | Posta direto, sem aprovação manual |
| Filtro | Desconto acima de 5%, de R$ 10 a R$ 100.000, sem mínimo de avaliação ou vendas |
| Horário e ritmo | Das 7h às 22h (Brasília). Busca a cada 30 min, posta a cada 5 min (até cerca de 180 por dia) |
| Repetição | Pode repetir, mas não dentro de 12 h, a não ser que o preço caia mais 3% (e já tenha passado 1 h) |
| Preço | Conferido na hora de cada envio. Se o desconto caiu para 5% ou menos, ou o produto sumiu, a oferta é pulada |
| Chaves de acesso | Nunca no chat nem no repositório. Ficam nos Secrets do GitHub (Settings > Secrets and variables > Actions) |

## O que já está pronto

- **Código** em `achadinhos/` (Shopee, Mercado Livre, legenda, envio pela Z-API e rotina) e **agenda** em `.github/workflows/rotina.yml` (GitHub Actions, 3 turnos a partir das 7h, 12h e 17h; só liga com a variável `ROTINA_LIGADA = sim`; a ação manual `teste` mostra 5 legendas no log sem enviar nada).
- **Testes:** 13, todos passando (`python -m unittest discover -s tests -t .`).
- **Link de afiliado do Mercado Livre:** pronto. O Gerador de Links faz links curtos `meli.la`; o endereço longo traz `matt_word=arajojefferson39&matt_tool=27581938`, que está em `ml_link_params` no `config.json` e é colado em cada produto. O `ref` do link de exemplo é próprio daquele link e não é usado. Conferir no primeiro dia se cliques e vendas aparecem no Portal do Afiliado.
- **Identidade visual** na pasta `marca/` e no Drive (detalhes abaixo).
- **Bio do grupo** em `marca/BIO.md` e no Drive: aviso de afiliado (CONAR), a loja responde por entrega, troca e garantia, preço pode mudar, ninguém pede Pix no privado, regras do grupo, e bio curta do Instagram.
- **Link do grupo, link curto e QR Code** (detalhes abaixo).

## O que falta (próximos passos)

1. **Mercado Livre: busca de produtos travada.** O suporte do Mercado Livre respondeu em 18/11 (chamado 496547907):
   - não existe API oficial de afiliados para gerar links; o canal oficial é o Gerador de Links do Portal (o nosso link pelos parâmetros `matt_word`/`matt_tool` continua valendo, mas é preciso conferir no Portal se os cliques contam);
   - a opção de criar aplicação no DevCenter **não aparece para a conta** e o formulário está fechado. Eles não têm como liberar, e sem aplicativo a API bloqueia a busca (403).

   Decisão pendente do Jer. Recomendação do Claude: **começar só com a Shopee**, que tem API oficial, e tratar o Mercado Livre depois, por um destes caminhos:
   - (a) ler a página pública de ofertas do Mercado Livre (mercadolivre.com.br/ofertas), filtrando casa e cozinha. Funciona sem aplicativo, mas o site pode bloquear o robô e mudar o layout;
   - (b) semiautomático: o Jer cola links de produtos num arquivo, e o robô confere o preço e posta junto com os da Shopee.
2. **Teste com 5 ofertas:** em Actions > Rotina de ofertas > Run workflow, ação `teste`. Ler o log e conferir as legendas e os links. Se a busca do Mercado Livre falhar mesmo com o aplicativo (o Mercado Livre tem restringido esse acesso), ajustar `achadinhos/mercadolivre.py`.
3. **Z-API:** criar a instância em z-api.io, conectar o chip do grupo pelo QR Code (o Jer precisa do celular do chip) e cadastrar nos Secrets `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN` e `ZAPI_CLIENT_TOKEN`. Depois rodar `python -m achadinhos grupos` para pegar o `WHATSAPP_GRUPO_ID` e cadastrar também.
4. **Shopee:** aguardando o Jer avisar que a conta de afiliado foi ativada. Aí: cadastrar `SHOPEE_APP_ID` e `SHOPEE_SECRET` nos Secrets e rodar `python -m achadinhos categorias` para preencher `shopee_categorias` no `config.json`.
5. **Juntar o branch ao `main`:** abrir o pull request quando o Jer pedir.
6. **Ligar a rotina:** criar a variável `ROTINA_LIGADA = sim` em Settings > Secrets and variables > Actions > Variables.

## Grupo no WhatsApp

- **Link de convite:** https://chat.whatsapp.com/JRY7yIMbOv609NylCljfsz
- **Link curto:** https://is.gd/grupinhodabia (criado no is.gd sem conta, não dá para editar o destino)
- **QR Code:** `marca/png/qr-code-grupo.png`, aponta direto para o link do WhatsApp. Para refazer: `python marca/gerar_qr.py <link>` e depois `node marca/exportar.js`.
- Se o link do grupo for redefinido no WhatsApp, o link curto e o QR Code param de funcionar: criar outro link curto, refazer o QR e atualizar as peças, a bio do Instagram e o documento "Link do grupo no WhatsApp" no Drive.
- O `WHATSAPP_GRUPO_ID` do robô é outro identificador, que sai da Z-API.

## Identidade visual

- Logo: etiqueta de preço inclinada com "bia", no azul das panelas de ágata.
- Paleta: Ágata `#1D44B8`, Ágata escuro `#102C7A`, Gema `#FFC83D` (preço e botões), Melancia `#F2445A` (só no selo de desconto), Louça `#F2F5FB`, Grafite `#151B2E`. Fontes: Bricolage Grotesque (títulos e preços) e Figtree (textos).
- `marca/pecas.html` é a fonte das peças; `node marca/exportar.js` gera os PNGs em `marca/png/`: foto do grupo, logos, card de oferta, post e story de convite (com QR Code e link curto), capas de destaque.
- Guia publicado: https://claude.ai/artifact/1qiqZzJeruZfMSzGSAfxAh

## Observações

- **Sessões na nuvem x no PC:** a sessão na nuvem não alcança o navegador nem o computador do Jer. Tudo que exige login (Mercado Livre, Z-API, GitHub Settings) deve ser feito numa sessão do Claude Desktop rodando no PC dele.
- **Rede do ambiente de nuvem "ACHADINHOS DA BIA":** hosts liberados `is.gd`, `meli.la` e `api.mercadolibre.com`.
- **Risco de bloqueio:** 180 mensagens por dia por serviço não oficial aumentam o risco de o WhatsApp bloquear o chip. Se acontecer, aumentar `postar_a_cada_minutos` no `config.json`.
- **Dados públicos:** o repositório é público, então a vitrine, o histórico e as postagens em `data/` ficam visíveis, assim como o link do grupo neste arquivo. Nenhuma chave vai para lá.

## Para começar a próxima conversa (no PC)

> Projeto Grupinho da Bia, repositório jeraraujo7/GRUPINHO-DA-BIA, branch claude/cool-carson-lz7yd8. Leia o CONVERSA.md e o README.md. O Mercado Livre não libera aplicativo para a minha conta (passo 1 do "O que falta"), então vamos seguir com a Shopee primeiro. Use o meu navegador para a Z-API e, quando a Shopee for ativada, para cadastrar as chaves nos Secrets do GitHub sem mostrar os valores no chat. Só me chame para código de verificação, aceite de termos ou o QR Code no celular do chip.
