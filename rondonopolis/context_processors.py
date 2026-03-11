# rondonopolis/context_processors.py
from .models import GrupoUsuario, GrupoAba

def grupos_context(request):
    """
    Context processor para obter as abas disponíveis para o usuário baseado em seu grupo
    Aplica apenas para usuários da filial Rondonópolis
    """
    abas_disponiveis = []
    grupos_usuario = []
    
    if request.user.is_authenticated:
        try:
            # Verificar se o usuário está na filial Rondonópolis
            filial_atual = request.user.userprofile.filial_selecionada
            
            if filial_atual and filial_atual.codigo == 'rondonopolis':
                # Buscar grupos do usuário
                grupos_usuario = GrupoUsuario.objects.filter(
                    usuarios=request.user,
                    ativo=True
                )
                
                # Superusuários e staff sempre têm acesso a todas as abas
                if request.user.is_superuser or request.user.is_staff:
                    abas_disponiveis = ['portaria', 'checklist', 'armazem', 'onda', 'liberacao_documentos', 'agendamentos', 'processos', 'dashboard', 'painel']
                else:
                    # Buscar abas ativas dos grupos do usuário
                    abas_ativas = GrupoAba.objects.filter(
                        grupo__in=grupos_usuario,
                        ativa=True
                    ).order_by('ordem', 'aba').values_list('aba', flat=True).distinct()
                    
                    abas_disponiveis = list(abas_ativas)
            else:
                # Se não está em Rondonópolis, retornar todas as abas (comportamento padrão)
                abas_disponiveis = ['portaria', 'checklist', 'armazem', 'onda', 'liberacao_documentos', 'agendamentos', 'processos', 'dashboard', 'painel']
        except Exception:
            # Em caso de erro, retornar todas as abas
            abas_disponiveis = ['portaria', 'checklist', 'armazem', 'onda', 'agendamentos', 'processos', 'dashboard', 'painel']
    else:
        abas_disponiveis = []
    
    return {
        'abas_disponiveis': abas_disponiveis,
        'grupos_usuario': grupos_usuario,
    }

