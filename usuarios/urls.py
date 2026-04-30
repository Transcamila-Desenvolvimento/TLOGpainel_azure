from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomPasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login, name='login'),
    path('', views.core, name='painel_tv'),
    path('logout/', views.logout, name='logout'),
    
    # NOVA URL para trocar filial
    path('selecionar-filial/<int:filial_id>/', views.selecionar_filial, name='selecionar_filial'),
    
    # Fluxo de redefinição de senha (MANTIDO)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        form_class=CustomPasswordResetForm,
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        html_email_template_name='password_reset_email_html.html',
        subject_template_name='password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        post_reset_login=True,
        success_url=reverse_lazy('password_reset_complete'),
        token_generator=default_token_generator
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    
    path('reset/link-invalido/',
         auth_views.TemplateView.as_view(template_name='password_reset_invalid.html'),
         name='password_reset_invalid'),

    path('configuracoes/filial/', views.configuracoes_filial, name='configuracoes_filial'),
]