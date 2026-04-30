from django.contrib import admin
from .models import Destino, Lancamento, ConfiguracaoDashboard


@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome']
    search_fields = ['nome']


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'po', 'destino', 'quantidade', 'status', 'criado_por', 'criado_em']
    list_filter = ['destino', 'status', 'criado_em']  # ✅ filtro por data
    search_fields = ['po', 'observacao']
    date_hierarchy = 'criado_em'  # ✅ navegação rápida por data
    list_editable = ['status']  # ✅ editar status direto na lista
    autocomplete_fields = ['destino', 'criado_por']  # ✅ campo de busca no admin


@admin.register(ConfiguracaoDashboard)
class ConfiguracaoDashboardAdmin(admin.ModelAdmin):
    list_display = ('tema',)
