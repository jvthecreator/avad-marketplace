# Remove a coluna tipo_usuario do perfil: qualquer usuário pode ser comprador e vendedor.
# O papel é escolhido no login (sessão); só is_mediador limita quem entra como mediador.
# Também corrige nomes de loja gravados com "&amp;" pelo seed antigo (ex.: "Casa &amp; Conforto").

from django.db import migrations


def corrigir_nome_loja(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    for perfil in UserProfile.objects.filter(nome_loja__contains='&amp;'):
        perfil.nome_loja = perfil.nome_loja.replace('&amp;', '&')
        perfil.save(update_fields=['nome_loja'])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_userprofile_meta_mensal"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="tipo_usuario",
        ),
        migrations.RunPython(corrigir_nome_loja, migrations.RunPython.noop),
    ]
