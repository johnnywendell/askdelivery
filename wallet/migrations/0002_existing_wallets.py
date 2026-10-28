from django.db import migrations


def create_wallets(apps, schema_editor):
    Usuario = apps.get_model('core', 'Usuario')
    Wallet = apps.get_model('wallet', 'Wallet')
    alias = schema_editor.connection.alias
    for pk in Usuario.objects.using(alias).values_list('pk', flat=True).iterator():
        Wallet.objects.using(alias).get_or_create(usuario_id=pk)


class Migration(migrations.Migration):
    dependencies = [('wallet', '0001_initial'), ('orders', '0002_order_delivery_base_order_delivery_distance_km_and_more')]
    operations = [migrations.RunPython(create_wallets, migrations.RunPython.noop)]
