# Memória do projeto AskDelivery

Leia este arquivo antes de trabalhar no projeto. Atualize-o ao concluir mudanças
com decisões, validações e pendências relevantes; mantenha-o curto e factual.
Nunca registre senhas, tokens, conteúdo do `.env` ou dados pessoais de usuários.

## Objetivo e arquitetura

- Aplicativo web de gestão de entregas: restaurante cadastra pedidos, entregador
  aceita e realiza entregas, cliente consulta pedidos vinculados ao seu cadastro.
- Django com templates HTML e JavaScript; Bootstrap e Leaflet na interface.
- `core`: autenticação por email, perfis, cadastros e permissões.
- `orders`: pedidos, aceite, alterações de status e painel de corridas.
- `tracking`: posição atual, histórico GPS e monitoramento via WebSocket.
- DRF usa autenticação por sessão; requisições POST precisam de CSRF.
- Channels/Redis distribuem atualizações no grupo `drivers_tracking`.
- `compose.yaml`: Django/Daphne, Redis e Nginx. SQLite configurado em
  `/host_project/db.sqlite3`, caminho associado ao ambiente Docker.
- A interface compartilhada está em `core/templates/base.html`; o widget global
  de GPS usa `static/js/admin.js`. Existe também uma tela independente de GPS.

## Mapas e serviços externos

- Telas com mapa: `orders/templates/orders/{dashboard,order_detail,order_form}.html`,
  `tracking/templates/tracking/mapa_entregadores.html` e formulários de cliente e
  restaurante em `core/templates/accounts/`.
- `tracking/templates/tracking/driver_tracking.html` contém controles de GPS e
  coordenadas, mas não contém mapa Leaflet. Não confundir com `mapa_entregadores.html`.
- Busca de endereços: Nominatim. Rotas e estimativas: OSRM público.
- CARTO passou a exigir chave para seus basemaps externos; URLs antigas sem chave
  exibem blocos com a mensagem `API key required` mesmo com o Leaflet funcionando.
  Fonte: https://www.carto.com/basemaps/apikey/index.html (consulta: 2026-10-25).
- Para tiles OSM, usar `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, atribuição
  visível e vinculada aos contribuidores, zoom nativo até 19, cache HTTP e Referer
  padrão do navegador. Sem download em massa ou prefetch para uso offline.
  Política: https://operations.osmfoundation.org/policies/tiles/.
- Servidores públicos OSM não têm SLA: avaliar provedor com capacidade adequada
  antes de escalar produção. O estilo OSM padrão difere do CARTO Positron.

## Cuidados e pendências já identificadas

- Não considerar o projeto pronto para produção apenas por corrigir os mapas.
- Há ações sobre pedidos que precisam validar propriedade e transições de status.
- O botão offline da tela independente interrompe GPS local sem notificar servidor.
- Indicadores da página inicial são valores fixos no HTML.
- Documentos/aprovação de entregadores e horários têm modelos, mas fluxos parciais.
- Os arquivos `tests.py` atuais são apenas esqueletos; não assumir cobertura.
- Evitar comandos de banco/migrações no banco real para validar mudanças de templates.

## Registro de manutenção

- 2026-10-25: substituídos tiles CARTO sem chave por OSM padrão no dashboard de
  pedidos, detalhe do pedido e mapa de entregadores. Padronizados também os três
  formulários com mapa (pedido, cliente e restaurante): endpoint oficial sem
  subdomínio, atribuição vinculada e `maxZoom: 19`. Removida importação duplicada
  de Leaflet no dashboard. A tela independente `driver_tracking.html` não precisou
  de alteração, pois não renderiza mapa.
- Validação dessa correção: `git diff --check` passou; execução dos seis trechos
  `L.tileLayer` com Node/VM e Leaflet simulado confirmou URL, atribuição, zoom e
  adição da camada, além de uma única importação do Leaflet por template.
  Um tile real retornou HTTP 200 e `image/png`, e a inspeção visual confirmou
  mapa válido. A primeira tentativa com User-Agent padrão do curl retornou uma
  imagem de bloqueio apesar do HTTP 200; a verificação com User-Agent explícito
  `AskDelivery-map-check/1.0 (+https://ask.singularcode.net/)` e Referer passou.
  Não usar apenas status/MIME como prova de funcionamento de tiles.
  Sem validação das páginas em
  navegador: Django não está instalado no Python do sistema nem no `venv` local.
- As mudanças de mapas ficaram apenas nos templates: não exigem migrações nem
  `collectstatic`. A publicação deve garantir que o Django esteja usando os
  templates atualizados; recarregar a página para receber o novo HTML.
