from django.contrib import admin

from .models import UserProfile, SavedCard


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user', 'nome_loja', 'tem_cnpj', 'email_verificado', 'is_mediador',
                    'conta_bancaria_bloqueada', 'suspenso')
    list_filter = ('email_verificado', 'is_mediador', 'tem_cnpj', 'conta_bancaria_bloqueada', 'suspenso')
    search_fields = ('nome', 'nome_loja', 'user__email', 'cpf', 'cnpj')
    list_editable = ('is_mediador', 'suspenso')


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'bandeira', 'ultimos_digitos', 'validade')
    search_fields = ('usuario__email',)
