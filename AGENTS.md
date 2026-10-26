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





