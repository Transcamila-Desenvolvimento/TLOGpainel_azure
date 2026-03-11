# rondonopolis/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import GrupoUsuario, GrupoAba

def acesso_permitido_por_aba(nome_aba):
    """
    Decorator que restringe o acesso baseado na aba do grupo do usuário
    Aplica apenas para usuários da filial Rondonópolis
    Para usuários de outras filiais, permite acesso normalmente
    
    Uso: @acesso_permitido_por_aba('portaria')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            try:
                # Verificar se o usuário está no grupo "Monitores" - permitir acesso ao painel/dashboard
                grupo_monitores = GrupoUsuario.objects.filter(nome='monitores', ativo=True).first()
                is_monitor = grupo_monitores and grupo_monitores.usuarios.filter(id=request.user.id).exists()
                
                # Se é monitor e está acessando o painel ou dashboard, permitir acesso
                if is_monitor and (nome_aba == 'dashboard' or nome_aba == 'painel'):
                    return view_func(request, *args, **kwargs)
                
                # Verificar se está na filial Rondonópolis
                filial_atual = request.user.userprofile.filial_selecionada
                
                # Se não está em Rondonópolis, permite acesso (comportamento padrão)
                if not filial_atual or filial_atual.codigo != 'rondonopolis':
                    return view_func(request, *args, **kwargs)
                
                # Buscar grupos do usuário
                grupos_usuario = GrupoUsuario.objects.filter(
                    usuarios=request.user,
                    ativo=True
                )
                
                if not grupos_usuario.exists():
                    # Se não tem grupo, bloqueia acesso (exceto para administradores)
                    if not request.user.is_staff and not request.user.is_superuser:
                        messages.error(request, 
                            'Você não tem permissão para acessar esta funcionalidade. '
                            'Entre em contato com o administrador para ser adicionado a um grupo.')
                        # Redirecionar para portaria (não requer permissão específica de grupo)
                        return redirect('rondonopolis:portaria_agendamentos')
                    return view_func(request, *args, **kwargs)
                
                # Verificar se algum grupo do usuário tem acesso à aba
                tem_acesso = GrupoAba.objects.filter(
                    grupo__in=grupos_usuario,
                    aba=nome_aba,
                    ativa=True
                ).exists()
                
                # Superusuários e staff sempre têm acesso
                if request.user.is_superuser or request.user.is_staff:
                    tem_acesso = True
                
                if not tem_acesso:
                    messages.error(request, 
                        f'Você não tem permissão para acessar "{nome_aba.capitalize()}". '
                        'Entre em contato com o administrador.')
                    # Redirecionar para a primeira aba disponível (evitar loop)
                    abas_disponiveis = GrupoAba.objects.filter(
                        grupo__in=grupos_usuario,
                        ativa=True
                    ).order_by('ordem', 'aba').values_list('aba', flat=True).distinct()
                    
                    if abas_disponiveis:
                        primeira_aba = abas_disponiveis[0]
                        # Mapear aba para URL
                        url_map = {
                            'portaria': 'rondonopolis:portaria_agendamentos',
                            'checklist': 'rondonopolis:checklist',
                            'armazem': 'rondonopolis:armazem',
                            'onda': 'rondonopolis:liberacao_onda',
                            'liberacao_documentos': 'rondonopolis:liberacao_documentos',
                            'processos': 'rondonopolis:visualizacao_processos',
                            'dashboard': 'rondonopolis:processos_dashboard',
                            'painel': 'rondonopolis:processos_painel',
                            'agendamentos': 'rondonopolis:lista_agendamentos',
                        }
                        url_name = url_map.get(primeira_aba)
                        if url_name:
                            return redirect(url_name)
                    
                    # Se não tem nenhuma aba disponível, redirecionar para portaria (sempre disponível)
                    return redirect('rondonopolis:portaria_agendamentos')
                
            except Exception as e:
                # Em caso de erro, logar e permitir acesso (para não quebrar o sistema)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao verificar acesso por aba: {e}")
                # Se for superusuário ou staff, permite acesso mesmo com erro
                if request.user.is_superuser or request.user.is_staff:
                    return view_func(request, *args, **kwargs)
                messages.warning(request, 'Erro ao verificar permissões. Entre em contato com o administrador.')
                # Redirecionar para portaria (não requer permissão específica de grupo)
                return redirect('rondonopolis:portaria_agendamentos')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

