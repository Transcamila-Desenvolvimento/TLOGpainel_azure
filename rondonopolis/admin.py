from django.contrib import admin
from .models import (
    Transportadora, Agendamento, Motorista,
    GrupoUsuario, GrupoAba, ConfiguracaoNotificacao, NotificacaoProcesso,
    PreferenciaNotificacaoUsuario
)

@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'telefone', 'criado_em', 'atualizado_em']
    search_fields = ['nome', 'telefone']
    list_filter = ['criado_em']
    readonly_fields = ['criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'telefone')
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Transportadora)
class TransportadoraAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'telefone']
    search_fields = ['nome', 'cnpj']

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ['ordem', 'motorista', 'data_agendada', 'horario_agendado', 'tipo', 'placa_veiculo', 'transportadora', 'peso', 'tipo_veiculo', 'status_geral']
    list_filter = ['tipo', 'data_agendada', 'transportadora', 'tipo_veiculo', 'status_geral']
    search_fields = ['motorista__nome', 'placa_veiculo', 'ordem']  # Atualizado para buscar pelo nome do motorista
    date_hierarchy = 'data_agendada'
    readonly_fields = ['criado_em', 'atualizado_em', 'criado_por']
    
    fieldsets = (
        ('Dados da Importação', {
            'fields': (
                'ordem', 'motorista', 'data_agendada', 'horario_agendado', 
                'tipo', 'placa_veiculo', 'transportadora', 'peso', 
                'tipo_veiculo', 'observacoes', 'coluna_ad'
            )
        }),
        ('Status e Etapas', {
            'fields': (
                'status_geral',
                ('portaria_liberacao', 'portaria_liberado_por'),
                ('checklist_numero', 'checklist_data', 'checklist_preenchido_por'),
                ('armazem_chegada', 'armazem_confirmado_por'),
                ('onda_status', 'onda_liberacao', 'onda_liberado_por'),
                'checklist_observacao'
            )
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em', 'criado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('motorista', 'transportadora')


class GrupoAbaInline(admin.TabularInline):
    model = GrupoAba
    extra = 0
    fields = ['aba', 'ativa', 'ordem']
    ordering = ['ordem', 'aba']


@admin.register(GrupoUsuario)
class GrupoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'descricao', 'get_usuarios_count', 'ativo', 'criado_em']
    list_filter = ['ativo', 'nome']
    search_fields = ['nome', 'descricao']
    filter_horizontal = ['usuarios']
    readonly_fields = ['criado_em', 'atualizado_em']
    inlines = [GrupoAbaInline]
    
    def get_usuarios_count(self, obj):
        return obj.usuarios.count()
    get_usuarios_count.short_description = 'Usuários'


@admin.register(ConfiguracaoNotificacao)
class ConfiguracaoNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'email_destinatario', 'whatsapp_destinatario', 'atualizado_em']
    list_filter = ['criado_em', 'atualizado_em']
    search_fields = ['usuario__username', 'usuario__email', 'email_destinatario', 'whatsapp_destinatario']
    readonly_fields = ['criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('usuario',)
        }),
        ('Contatos (Configurados pelo Administrador)', {
            'fields': ('email_destinatario', 'whatsapp_destinatario'),
            'description': 'Configure o email e WhatsApp que receberão as notificações deste usuário.'
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PreferenciaNotificacaoUsuario)
class PreferenciaNotificacaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'receber_email', 'receber_whatsapp', 'receber_navegador', 'atualizado_em']
    list_filter = ['receber_email', 'receber_whatsapp', 'receber_navegador']
    search_fields = ['usuario__username', 'usuario__email']
    readonly_fields = ['atualizado_em']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('usuario',)
        }),
        ('Preferências de Notificação', {
            'fields': ('receber_email', 'receber_whatsapp', 'receber_navegador'),
            'description': 'O usuário pode ativar/desativar tipos de notificação através do sistema.'
        }),
        ('Metadados', {
            'fields': ('atualizado_em',),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificacaoProcesso)
class NotificacaoProcessoAdmin(admin.ModelAdmin):
    list_display = ['agendamento', 'tipo', 'destinatario', 'enviado_com_sucesso', 'etapa_quando_enviado', 'enviado_em']
    list_filter = ['tipo', 'enviado_com_sucesso', 'etapa_quando_enviado', 'enviado_em']
    search_fields = ['agendamento__ordem', 'destinatario', 'assunto']
    readonly_fields = ['enviado_em']
    date_hierarchy = 'enviado_em'
    
    fieldsets = (
        ('Processo', {
            'fields': ('agendamento', 'etapa_quando_enviado')
        }),
        ('Notificação', {
            'fields': ('tipo', 'destinatario', 'assunto', 'mensagem')
        }),
        ('Status', {
            'fields': ('enviado_com_sucesso', 'erro', 'enviado_em')
        }),
    )