import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_usuario', models.CharField(choices=[('comprador', 'Comprador'), ('vendedor', 'Vendedor'), ('mediador', 'Mediador')], max_length=20)),
                ('categoria', models.CharField(choices=[('pedido', 'Pedido'), ('disputa', 'Disputa'), ('reembolso', 'Reembolso'), ('avaliacao', 'Avaliação')], default='pedido', max_length=20)),
                ('titulo', models.CharField(max_length=120)),
                ('mensagem', models.CharField(max_length=300)),
                ('link', models.CharField(blank=True, max_length=200)),
                ('lida', models.BooleanField(default=False)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificacoes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-criada_em'],
            },
        ),
    ]
