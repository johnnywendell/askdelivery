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


## Administrador e solicitações de cadastro

- Middleware garante `Usuario(tipo=ADMIN)` ao primeiro acesso autenticado de
  superusuários sem perfil, inclusive contas antigas/criadas pelo shell.
  Meu perfil aceita ADMIN sem formulário de subtipo.
- Admin escolhe restaurante ao criar/cotar pedidos (HTML e API); frete e reserva
  continuam vinculados à carteira do restaurante escolhido.
- `/cadastro/` público oferece cliente/restaurante/entregador, exige dados e foto,
  valida senha e mantém User/Usuario inativos, sem permissões, até aprovação.
  Opções booleanas são livres; endereço tem busca e seleção no mapa.
- Lista de usuários mostra solicitações e dados para revisão. Aprovação somente
  por superusuário via POST/CSRF, atômica e idempotente, registra responsável/data,
  ativa a conta e concede apenas a permissão do tipo. Entregador fica aprovado.
- Removidos prints de POST/FILES dos cadastros administrativos.
- Migração core 0002 necessária; banco real não alterado. Validação em banco
  temporário: 45 testes core/wallet/orders; migrações sem divergências.

## Ajustes de cadastro e ativação

- Cadastro público exibe erros gerais e por campo em vermelho, com borda e rótulo
  dos campos inválidos destacados. Validação do servidor reúne os avisos ao enviar.
- Edição exclusiva de superusuário tem controle “Usuário ativo” para cliente,
  restaurante e entregador; sincroniza User.is_active e Usuario.ativo. Ativação de
  pendente registra aprovação, concede permissão do tipo e aprova entregador.
- Validação: 47 testes core/wallet/orders em SQLite temporário, incluindo ativação,
  desativação, aprovação pela edição e erros do cadastro. Banco real não alterado.
