# paranagua/urls.py
from django.urls import path
from . import views

app_name = 'paranagua'  # Nome do namespace

urlpatterns = [
    path('', views.painel_tv, name='painel_tv'),
    path('lancamentos/', views.lancamento_list, name='lancamento_list'),
    path('lancamentos/novo/', views.lancamento_create, name='lancamento_create'),
    path('lancamentos/<int:pk>/editar/', views.lancamento_update, name='lancamento_update'),
    path('lancamentos/<int:pk>/excluir/', views.lancamento_delete, name='lancamento_delete'),
    path('processos-finalizados/', views.processos_finalizados, name='processos_finalizados'),
    path('lancamentos/finalizados/acoes-em-lote/', views.acoes_em_lote, name='acoes_em_lote'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('exportar/', views.exportar_lancamentos, name='exportar_lancamentos'),
]