from django.urls import path
from . import views

app_name = 'rondonopolis'

urlpatterns = [
    # ==================== PORTARIA ====================
    path('portaria/', views.portaria_agendamentos, name='portaria_agendamentos'),
    path('portaria/horario-atual/', views.obter_horario_atual, name='obter_horario_atual'),
    path('portaria/atualizar-dados/', views.portaria_atualizar_dados, name='portaria_atualizar_dados'),
    path('portaria/tabela/', views.portaria_agendamentos, name='portaria_tabela'),  # Fix for SmartUpdate 404
    path('portaria/confirmar-chegada/', views.confirmar_chegada, name='confirmar_chegada'),
    path('portaria/confirmar-chegada-armazem/', views.confirmar_chegada_armazem_portaria, name='confirmar_chegada_armazem_portaria'),
    path('portaria/detalhes/', views.detalhes_agendamento, name='detalhes_agendamento'),
    path('portaria/confirmar-chegada-multipla/', views.confirmar_chegada_multipla, name='confirmar_chegada_multipla'),
    path('portaria/documento-impressao/', views.documento_impressao, name='documento_impressao'),
    
    # ==================== NOVAS URLs PARA MOTORISTAS ====================
    path('portaria/chamar-motorista/', views.chamar_motorista, name='chamar_motorista'),
    path('motoristas/telefone/', views.motoristas_telefone, name='motoristas_telefone'),
    path('motoristas/tela-chamada/', views.tela_chamada_motorista, name='tela_chamada_motorista'),
    path('motoristas/iniciar-chamada/', views.iniciar_chamada_motorista, name='iniciar_chamada_motorista'),
    path('motoristas/verificar-chamada/', views.verificar_chamada_motorista, name='verificar_chamada_motorista'),

    # ==================== CHECKLIST ====================
    path('checklist/', views.checklist, name='checklist'),
    path('checklist/tabela/', views.checklist_tabela, name='checklist_tabela'),
    path('checklist/atualizar-dados/', views.checklist_atualizar_dados, name='checklist_atualizar_dados'),
    path('checklist/preencher/', views.preencher_checklist, name='preencher_checklist'),

    # ==================== ARMAZÉM ====================
    path('armazem/', views.armazem, name='armazem'),
    path('armazem/tabela/', views.armazem_tabela, name='armazem_tabela'),
    path('armazem/atualizar-dados/', views.armazem_atualizar_dados, name='armazem_atualizar_dados'),
    path('armazem/registrar-entrada/', views.armazem_registrar_entrada, name='armazem_registrar_entrada'),
    path('armazem/registrar-saida/', views.armazem_registrar_saida, name='armazem_registrar_saida'),

    # ==================== LIBERAÇÃO DE ONDA ====================
    path('onda/', views.liberacao_onda, name='liberacao_onda'),
    path('onda/tabela/', views.onda_tabela, name='onda_tabela'),
    path('onda/atualizar-dados/', views.onda_atualizar_dados, name='onda_atualizar_dados'),
    path('onda/registrar-liberacao/', views.onda_registrar_liberacao, name='onda_registrar_liberacao'),

    # ==================== DOCUMENTOS ====================
    path('liberacao-documentos/', views.liberacao_documentos, name='liberacao_documentos'),
    path('liberacao-documentos/tabela/', views.documentos_tabela, name='documentos_tabela'),
    path('liberacao-documentos/atualizar-dados/', views.documentos_atualizar_dados, name='documentos_atualizar_dados'),
    path('liberacao-documentos/registrar-liberacao/', views.documentos_registrar_liberacao, name='documentos_registrar_liberacao'),

    # ==================== OUTROS / GERAIS ====================
    path('agendamentos/', views.lista_agendamentos, name='lista_agendamentos'),
    path('agendamentos/exportar/', views.exportar_agendamentos, name='exportar_agendamentos'),
    path('configuracoes_perfil/', views.configuracoes_perfil, name='configuracoes_perfil'),
    
    # ==================== IMPORTAR AGENDAMENTOS ====================
    path('agendamentos/importar/', views.importar_agendamentos_view, name='importar_agendamentos'),
    path('agendamentos/baixar-modelo/', views.baixar_modelo_importacao, name='baixar_modelo'),
    path('agendamentos/criar/', views.criar_agendamento_view, name='criar_agendamento'),
    path('agendamentos/obter/', views.obter_agendamento, name='obter_agendamento'),
    path('agendamentos/editar/', views.editar_agendamento_view, name='editar_agendamento'),
    path('agendamentos/<int:agendamento_id>/excluir/', views.excluir_agendamento_view, name='excluir_agendamento'),

    # ==================== VISUALIZAÇÃO DE PROCESSOS ====================
    path('processos/', views.visualizacao_processos, name='visualizacao_processos'),
    path('processos/exibir/<int:agendamento_id>/', views.exibir_processo_detalhes, name='exibir_processo_detalhes'),
    path('processos-painel/', views.processos_painel, name='processos_painel'),
    path('processos-dashboard/', views.processos_dashboard, name='processos_dashboard'),
    path('processos/verificar-atualizacoes/', views.verificar_atualizacoes_processos, name='verificar_atualizacoes_processos'),
    path('smart-update/', views.verificar_atualizacoes, name='smart_update'), # Feature nova
    path('api/verificar-atualizacoes/', views.verificar_atualizacoes, name='verificar_atualizacoes_legacy'), # Legado (cache fix)
    
    # ==================== GERENCIAR ETAPAS ====================
    path('agendamentos/<int:agendamento_id>/dados-etapas/', views.dados_etapas_agendamento, name='dados_etapas_agendamento'),
    path('agendamentos/salvar-etapas/', views.salvar_etapas_agendamento, name='salvar_etapas_agendamento'),
    
    # ==================== NOTIFICAÇÕES ====================
    path('notificacoes/pendentes/', views.notificacoes_pendentes, name='notificacoes_pendentes'),
    path('notificacoes/vapid-key/', views.vapid_public_key, name='vapid_public_key'),
    path('notificacoes/registrar-subscription/', views.registrar_push_subscription, name='registrar_push_subscription'),
    
    # ==================== CADASTRO RÁPIDO ====================
    path('motoristas/cadastrar-rapido/', views.cadastrar_motorista_rapido, name='cadastrar_motorista_rapido'),
    path('transportadoras/cadastrar-rapido/', views.cadastrar_transportadora_rapida, name='cadastrar_transportadora_rapida'),
    path('atualizar-nomes-maiusculas/', views.atualizar_nomes_para_maiusculas, name='atualizar_nomes_maiusculas'),
]