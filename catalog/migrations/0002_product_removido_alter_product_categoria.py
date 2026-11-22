from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='removido',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='product',
            name='categoria',
            field=models.CharField(choices=[('tecnologia', 'Tecnologia'), ('eletronicos', 'Eletrônicos'), ('audio', 'Áudio'), ('eletrodomesticos', 'Eletrodomésticos'), ('brinquedos', 'Brinquedos'), ('servicos', 'Serviços'), ('decoracao', 'Decoração'), ('moda', 'Moda'), ('esportes', 'Esportes'), ('livros', 'Livros'), ('outros', 'Outros')], max_length=50),
        ),
    ]