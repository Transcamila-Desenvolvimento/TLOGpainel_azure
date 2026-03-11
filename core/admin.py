from django.contrib import admin
from .models import Destino, Lancamento
from .models import ConfiguracaoDashboard

@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome']
    search_fields = ['nome']

@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'po', 'destino', 'quantidade', 'status', 'criado_por', 'criado_em']
    list_filter = ['destino', 'status']
    search_fields = ['po', 'observacao']

@admin.register(ConfiguracaoDashboard)
class ConfiguracaoDashboardAdmin(admin.ModelAdmin):
    list_display = ('tema',)
