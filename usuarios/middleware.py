# usuarios/middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile

class FilialMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs públicas que não precisam de verificação
        urls_publicas = [
            '/admin/',
            '/auth/',
            '/password_reset/',
            '/reset/',
            '/selecionar-filial/',
            '/login/',
            '/cadastro/',
            '/logout/',
            '/configuracoes/filial/'
        ]
        
        # Se não é URL pública e usuário está autenticado
        if (request.user.is_authenticated and 
            not any(request.path.startswith(url) for url in urls_publicas)):
            
            # Verificar se o usuário está no grupo "Monitores" - permitir acesso ao painel de movimentações
            is_monitor = False
            is_mobile = False
            try:
                from rondonopolis.models import GrupoUsuario
                grupo_monitores = GrupoUsuario.objects.filter(nome='monitores', ativo=True).first()
                if grupo_monitores and grupo_monitores.usuarios.filter(id=request.user.id).exists():
                    is_monitor = True
                    
                    # Detectar se é mobile
                    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
                    is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
                    
                    # Se é mobile e está tentando acessar Painel ou Dashboard, redirecionar para Portaria
                    if is_mobile and ('/rondonopolis/processos-painel/' in request.path or '/rondonopolis/processos-dashboard/' in request.path):
                        from django.shortcuts import redirect
                        return redirect('rondonopolis:portaria_agendamentos')
                    
                    # Se não é mobile e está acessando o painel de movimentações, permitir acesso sem verificar filial
                    if not is_mobile and ('/rondonopolis/processos-painel/' in request.path or '/rondonopolis/processos-dashboard/' in request.path):
                        return self.get_response(request)
            except Exception:
                pass
            
            try:
                profile = request.user.userprofile
                
                # 1. VERIFICA SE TEM FILIAL SELECIONADA (exceto para Monitores acessando painel)
                if not profile.filial_selecionada and not (is_monitor and ('/rondonopolis/processos-painel/' in request.path or '/rondonopolis/processos-dashboard/' in request.path)):
                    messages.warning(request, 'Selecione uma filial para continuar')
                    return redirect('configuracoes_filial')
                
                # 2. VERIFICA SE ESTÁ NA FILIAL CORRETA (PROTEÇÃO REAL)
                # Exceção: Monitores podem acessar o painel de movimentações independente da filial
                if not (is_monitor and ('/rondonopolis/processos-painel/' in request.path or '/rondonopolis/processos-dashboard/' in request.path)):
                    filial_atual = profile.filial_selecionada
                    path_atual = request.path
                    
                    # Se não está acessando a URL da filial selecionada
                    if not path_atual.startswith(filial_atual.url_inicial):
                        messages.error(request, f'Acesso permitido apenas para {filial_atual.nome}')
                        return redirect(filial_atual.url_inicial)
                    
            except UserProfile.DoesNotExist:
                # Se é monitor e está acessando o painel, permitir
                if is_monitor and ('/rondonopolis/processos-painel/' in request.path or '/rondonopolis/processos-dashboard/' in request.path):
                    return self.get_response(request)
                # Cria perfil se não existir e redireciona
                UserProfile.objects.create(user=request.user)
                messages.warning(request, 'Selecione uma filial para continuar')
                return redirect('configuracoes_filial')
        
        return self.get_response(request)