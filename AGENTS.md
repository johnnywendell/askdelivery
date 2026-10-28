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






## Wallet e frete

- `wallet` registrado: menu/perfil com saldo, reservas, extrato e solicitações;
  superusuário confirma depósitos/saques externos e configura tarifa.
- Frete = base + distância Haversine em linha reta × tarifa/km (padrão 5 + 2/km),
  cotado no servidor e congelado no pedido. Reserva na criação, pagamento integral
  ao entregador na conclusão, liberação ao cancelar antes da saída. Sem Pix/banco.
- Services usam atomicidade, bloqueios e updates condicionais; histórico protegido.
  Acesso por dono/entregador atribuído. Destino reservado exige cancelar/recriar.
- Migrações agora versionadas. Banco legado sem histórico: conferir e executar
  `adopt_legacy_migrations --apply` antes de `migrate`; detalhes em `wallet/README.md`.
- Validados testes financeiros/HTTP em Django 6.0.5, instalação nova e migração de
  legado sintético. Banco real não alterado. Pendências: gateway, disputa/estorno
  após saída, distância viária e validação de concorrência em PostgreSQL.

## Página inicial

- Index dinâmico em `core/dashboard.py`: superusuário vê operação e solicitações
  globais; restaurante vê seus pedidos/saldos; entregador vê corridas atribuídas,
  ganhos creditados no dia e quantidade de oportunidades. Cliente mantém tela básica.
- Visão administrativa exige `is_superuser`, conforme permissões existentes;
  `tipo=ADMIN` e `is_staff` isoladamente não liberam dados globais.
- Consulta somente leitura, listas limitadas, atualização pelo botão do painel.
  Ganhos usam transações de pagamento; saldos globais não representam receita.
- Validação: 7 testes do index cobrem perfis, isolamento, saldos/ganhos, ausência
  de cadastro/movimentação e login; suíte core/wallet/orders com 37 testes.
