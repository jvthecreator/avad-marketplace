from django.db import migrations, models
from django.utils import timezone


def preencher_entregue_em(apps, schema_editor):
    """Pedidos já entregues antes desta migration ganham 14 dias a partir de agora."""
    Order = apps.get_model('orders', 'Order')
    Order.objects.filter(status='entregue', entregue_em__isnull=True).update(entregue_em=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_remove_avad_express'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='entregue_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(preencher_entregue_em, migrations.RunPython.noop),
    ]