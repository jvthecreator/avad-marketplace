from django.db import migrations, models


def express_para_sedex(apps, schema_editor):
    """Pedidos antigos feitos com a Transportadora AVAD Express passam a constar como SEDEX."""
    Order = apps.get_model('orders', 'Order')
    Order.objects.filter(metodo_frete='avad_express').update(metodo_frete='sedex')


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_cartitem'),
    ]

    operations = [
        migrations.RunPython(express_para_sedex, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='metodo_frete',
            field=models.CharField(choices=[('pac', 'PAC'), ('sedex', 'SEDEX')], default='pac', max_length=20),
        ),
    ]