# Carteira do MVP

Cada perfil `Usuario` recebe uma carteira. A migração cria carteiras zeradas para
perfis anteriores; o sinal atende aos novos cadastros. A carteira fica no menu
**Minha carteira** e no perfil; superusuários também veem **Gestão de carteiras**.

## Regras

- Frete: **base + km em linha reta × tarifa/km**, entre restaurante e destino.
  Haversine com raio 6371 km, distância arredondada para 3 casas e total para
  centavos com ROUND_HALF_UP. Padrão: R$ 5,00 + R$ 2,00/km.
- O formulário consulta a cotação no servidor antes de salvar. A gravação recalcula
  e valida o saldo; a prévia não garante saldo nem congela tarifa.
- Novos pedidos HTML e API reservam o frete na criação. Valor, distância e tarifas
  ficam registrados no pedido. O entregador vê o valor no painel de corridas.
- O saldo disponível já exclui reservas. Reservas incluem entregas e saques.
- Aceite mantém a reserva. Pedidos legados sem cotação são financiados no aceite;
  legados já em rota são financiados na conclusão. Se faltar saldo, a operação
  não avança. Pedidos históricos concluídos não são cobrados retroativamente.
- Conclusão após saída para entrega transfere **100% do frete** ao entregador;
  não há comissão. Cancelamento antes da saída para entrega devolve a reserva.
  Cancelamentos em rota e estornos após conclusão exigem um fluxo futuro de disputa.
- O destino fica bloqueado após criação: cancelar e recriar gera nova cotação.
  Nome, telefone e cliente vinculado podem ser editados antes do aceite.
- Apenas o restaurante dono cancela/edita, e apenas o entregador atribuído inicia
  ou conclui. Repetir conclusão, cancelamento ou revisão não repete movimentos.
- Depósitos ficam pendentes até confirmação administrativa do recebimento externo.
  Saques reservam saldo imediatamente: confirmar consome a reserva, recusar devolve.
  O administrador deve pagar externamente **antes de confirmar o saque**.
- Não há integração Pix/banco, cobrança automática externa nem envio de dinheiro.
  A observação pode identificar um comprovante externo; não há upload de comprovantes.
- Extrato é privado, paginado e filtrável. Administração mostra solicitações
  paginadas por situação. Histórico financeiro tem exclusão protegida e admin
  somente leitura; operações usam serviços transacionais.

## Instalação

O repositório ignorava todas as migrações. Agora as baselines de core, orders e
tracking estão versionadas e as alterações financeiras são migrações separadas.
Use o ambiente configurado da aplicação e faça backup do banco antes da atualização.

**Banco novo:** `python manage.py migrate`.

**Banco legado com tabelas dos apps mas sem suas migrações no histórico:**

```sh
python manage.py adopt_legacy_migrations
python manage.py adopt_legacy_migrations --apply
python manage.py migrate
```

O primeiro comando só confere a presença das tabelas e colunas da baseline.
O segundo registra essas migrações iniciais sem recriar tabelas; não compara todos
os tipos, índices ou constraints. Em bancos com alterações manuais, revise a
compatibilidade antes de aplicar. Não use `--fake` para as novas migrações de wallet
ou orders/0002. O comando de adoção também resolve o histórico legado em que admin
já foi migrado antes de core ter migrações versionadas.

Em Docker, prefixe os comandos com `docker compose exec web`. Reinicie a aplicação
após aplicar migrações e publique os arquivos estáticos conforme o processo do ambiente.
Cadastre a tarifa em Gestão de carteiras (opcional: os valores padrão já funcionam).
Restaurantes sem latitude/longitude precisam completar esse cadastro.

## Validação

`python manage.py test wallet` cobre saldo, reservas, liquidação única, rollback,
solicitações, autorização, CSRF, telas, cotação, criação API/HTML e pedidos legados.
Validado em Django 6.0.5 / SQLite, com banco isolado e Channels em memória. Validada
instalação nova e adoção de um banco legado sintético com perfil existente.

Updates condicionais protegem saldos contra valores negativos inclusive em SQLite;
`select_for_update` acrescenta bloqueios por linha em bancos que os suportam.
SQLite pode rejeitar escritas concorrentes com `database is locked`; PostgreSQL
é uma evolução para maior concorrência. Não há integração bancária real nos testes.
