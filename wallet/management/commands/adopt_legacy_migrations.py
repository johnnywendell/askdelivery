"""Registra a baseline de bancos criados quando as migrações eram ignoradas."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = 'Valida tabelas legadas de core/orders/tracking e adota suas migrações iniciais.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Registra a baseline validada no histórico.')

    def handle(self, *args, **options):
        targets = [(app, '0001_initial') for app in ('core', 'orders', 'tracking')]
        loader = MigrationLoader(connection)
        state = loader.project_state(targets)
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()
        missing = [target for target in targets if target not in applied]
        if not missing:
            self.stdout.write('Baseline já registrada; execute migrate normalmente.')
            return
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            legacy_tables = {model._meta.db_table for model in state.apps.get_models()
                             if model._meta.app_label in {app for app, _ in missing}}
            if not tables.intersection(legacy_tables):
                self.stdout.write('Banco novo: execute migrate normalmente, sem adotar baseline.')
                return
            for app, _ in missing:
                for model in state.apps.get_app_config(app).get_models(include_auto_created=True):
                    table = model._meta.db_table
                    if table not in tables:
                        raise CommandError(f'Tabela ausente: {table}. Nenhum histórico foi alterado.')
                    columns = {col.name for col in connection.introspection.get_table_description(cursor, table)}
                    expected = {field.column for field in model._meta.local_fields}
                    if expected - columns:
                        raise CommandError(f'Colunas ausentes em {table}: {sorted(expected - columns)}. Nenhum histórico foi alterado.')
        if not options['apply']:
            self.stdout.write('Tabelas e colunas da baseline conferidas. Faça backup e execute novamente com --apply.')
            return
        with transaction.atomic():
            for app, name in missing:
                recorder.record_applied(app, name)
        self.stdout.write(self.style.SUCCESS('Baseline registrada. Execute migrate para instalar a carteira.'))
