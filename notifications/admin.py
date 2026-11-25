from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'tipo_usuario', 'categoria', 'lida', 'criada_em')
    list_filter = ('tipo_usuario', 'categoria', 'lida')
    search_fields = ('titulo', 'usuario__email')
