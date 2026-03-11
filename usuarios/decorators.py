# usuarios/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def acesso_permitido_apenas_para_filial(codigo_filial):
    """
    Decorator que restringe o acesso apenas para uma filial específica
    Uso: @acesso_permitido_apenas_para_filial('ibipora')
    Exceção: Usuários do grupo "Monitores" podem acessar o dashboard de Rondonópolis
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # Verificar se o usuário está no grupo "Monitores" e está acessando o painel/dashboard
                is_monitor_painel = False
                try:
                    from rondonopolis.models import GrupoUsuario
                    grupo_monitores = GrupoUsuario.objects.filter(nome='monitores', ativo=True).first()
                    if grupo_monitores and grupo_monitores.usuarios.filter(id=request.user.id).exists():
                        # Verificar se está acessando o painel ou dashboard de processos
                        if ('/processos-painel/' in request.path or '/processos-dashboard/' in request.path) and codigo_filial == 'rondonopolis':
                            is_monitor_painel = True
                except Exception:
                    pass
                
                # Se é monitor acessando painel/dashboard, permitir acesso
                if is_monitor_painel:
                    return view_func(request, *args, **kwargs)
                
                try:
                    filial_atual = request.user.userprofile.filial_selecionada
                    
                    # Verifica se a filial atual é a permitida para esta view
                    if filial_atual.codigo != codigo_filial:
                        messages.error(request, 
                            f'Acesso restrito para {filial_atual.nome}. '
                            f'Esta funcionalidade é apenas para {codigo_filial.upper()}')
                        return redirect(filial_atual.url_inicial)
                        
                except:
                    messages.error(request, 'Erro de configuração de filial')
                    return redirect('configuracoes_filial')
                    
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator