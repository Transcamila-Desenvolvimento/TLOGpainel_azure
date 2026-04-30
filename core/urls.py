from django.urls import path
from . import views

urlpatterns = [
    path('', views.painel_tv, name='painel_tv'),
    path('painel/lancamentos/', views.lancamento_list, name='lancamento_list'),
    path('painel/lancamentos/novo/', views.lancamento_create, name='lancamento_create'),
    path('painel/lancamentos/<int:pk>/editar/', views.lancamento_update, name='lancamento_update'),
    path('painel/lancamentos/<int:pk>/excluir/', views.lancamento_delete, name='lancamento_delete'),

    # Processos finalizados
    path('painel/lancamentos/finalizados/', views.processos_finalizados, name='processos_finalizados'),
    path('painel/lancamentos/finalizados/acoes-em-lote/', views.acoes_em_lote, name='acoes_em_lote'),

    # Configurações
    path('configuracoes/', views.configuracoes, name='configuracoes'),

    path('exportar-processos/', views.exportar_processos, name='exportar_processos'),

     path('configuracoes_perfil/', views.configuracoes_perfil, name='configuracoes_perfil'),
]

