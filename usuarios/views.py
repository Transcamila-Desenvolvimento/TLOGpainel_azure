# usuarios/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout as logout_django
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from .models import UserProfile, Filial  # Import dos novos modelos

def obter_primeira_aba_mobile(user):
    """
    Retorna a URL da primeira aba disponível no menu mobile para o usuário
    """
    try:
        from rondonopolis.models import GrupoUsuario, GrupoAba
        grupos_usuario = GrupoUsuario.objects.filter(usuarios=user, ativo=True)
        
        # Abas do menu mobile em ordem de prioridade
        abas_mobile = ['portaria', 'checklist', 'onda', 'armazem', 'liberacao_documentos', 'processos']
        
        # Buscar primeira aba disponível
        for aba_nome in abas_mobile:
            if user.is_superuser or user.is_staff:
                # Superusuários têm acesso a todas
                url_map = {
                    'portaria': 'rondonopolis:portaria_agendamentos',
                    'checklist': 'rondonopolis:checklist',
                    'onda': 'rondonopolis:liberacao_onda',
                    'armazem': 'rondonopolis:armazem',
                    'liberacao_documentos': 'rondonopolis:liberacao_documentos',
                    'processos': 'rondonopolis:visualizacao_processos',
                }
                return url_map.get(aba_nome, 'rondonopolis:portaria_agendamentos')
            
            # Verificar se algum grupo do usuário tem acesso à aba
            tem_acesso = GrupoAba.objects.filter(
                grupo__in=grupos_usuario,
                aba=aba_nome,
                ativa=True
            ).exists()
            
            if tem_acesso:
                url_map = {
                    'portaria': 'rondonopolis:portaria_agendamentos',
                    'checklist': 'rondonopolis:checklist',
                    'onda': 'rondonopolis:liberacao_onda',
                    'armazem': 'rondonopolis:armazem',
                    'liberacao_documentos': 'rondonopolis:liberacao_documentos',
                    'processos': 'rondonopolis:visualizacao_processos',
                }
                return url_map.get(aba_nome, 'rondonopolis:portaria_agendamentos')
        
        # Se não encontrou nenhuma, usar Portaria como padrão
        return 'rondonopolis:portaria_agendamentos'
    except Exception:
        # Em caso de erro, usar Portaria como padrão
        return 'rondonopolis:portaria_agendamentos'

def cadastro(request):
    if request.method == "GET":
        return render(request, 'cadastro.html')
    else:
        username = request.POST.get('username')
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        user = User.objects.filter(username=username).first()

        if user:
            return HttpResponse('Já existe um usuario cadastrado com esse nome')
        
        user = User.objects.create_user(username=username, email=email, password=senha)
        user.save()
        
        # Cria UserProfile para o novo usuário
        profile = UserProfile.objects.create(user=user)
        
        # Adiciona filial padrão (Ibiporã)
        try:
            filial_ibipora = Filial.objects.get(codigo='ibipora')
            profile.filiais.add(filial_ibipora)
            profile.filial_selecionada = filial_ibipora
            profile.save()
        except Filial.DoesNotExist:
            pass
        
        return HttpResponse('Usuario cadastrado com sucesso!')

def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    
    username = request.POST.get('username')
    senha = request.POST.get('senha')

    user = authenticate(request, username=username, password=senha)

    if user:
        login_django(request, user)
        
        # Verificar se o usuário está no grupo "Monitores" e redirecionar adequadamente
        try:
            from rondonopolis.models import GrupoUsuario
            grupo_monitores = GrupoUsuario.objects.filter(nome='monitores', ativo=True).first()
            if grupo_monitores and grupo_monitores.usuarios.filter(id=user.id).exists():
                # Detectar se é mobile
                user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
                is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
                
                if is_mobile:
                    # No mobile, redirecionar para uma das abas do menu mobile (Portaria por padrão)
                    return redirect('rondonopolis:portaria_agendamentos')
                else:
                    # No desktop, redirecionar para o painel de movimentações
                    return redirect('rondonopolis:processos_painel')
        except Exception as e:
            # Se houver erro ao verificar grupo, continuar com o fluxo normal
            pass
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if not profile.filial_selecionada:
            try:
                filial_ibipora = Filial.objects.get(codigo='ibipora')
                profile.filial_selecionada = filial_ibipora
                if filial_ibipora not in profile.filiais.all():  # Usando related_name correto
                    profile.filiais.add(filial_ibipora)
                profile.save()
            except Filial.DoesNotExist:
                pass
        
        if profile.filial_selecionada:
            # Detectar se é mobile
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
            
            if is_mobile and profile.filial_selecionada.codigo == 'rondonopolis':
                # No mobile para Rondonópolis, redirecionar para primeira aba disponível do menu mobile
                return redirect(obter_primeira_aba_mobile(user))
            else:
                # Desktop ou outras filiais: usar URL inicial normal
                return redirect(profile.filial_selecionada.url_inicial)
        else:
            return redirect('lancamento_list')
    else:
        messages.error(request, 'Usuário ou senha inválidos.')
        return redirect('login')


@login_required(login_url="/auth/login/")
def core(request):
    # Verificar se o usuário está no grupo "Monitores" e redirecionar para o painel de movimentações
    try:
        from rondonopolis.models import GrupoUsuario
        grupo_monitores = GrupoUsuario.objects.filter(nome='monitores', ativo=True).first()
        if grupo_monitores and grupo_monitores.usuarios.filter(id=request.user.id).exists():
            # Detectar se é mobile
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
            
            if is_mobile:
                # No mobile, redirecionar para uma das abas do menu mobile (Portaria por padrão)
                return redirect('rondonopolis:portaria_agendamentos')
            else:
                # No desktop, redirecionar para o painel de movimentações
                return redirect('rondonopolis:processos_painel')
    except Exception:
        # Se houver erro ao verificar grupo, continuar com o fluxo normal
        pass
    
    # Redireciona para a filial selecionada do usuário
    try:
        profile = request.user.userprofile
        if profile.filial_selecionada:
            # Detectar se é mobile
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
            
            if is_mobile and profile.filial_selecionada.codigo == 'rondonopolis':
                # No mobile para Rondonópolis, redirecionar para primeira aba disponível do menu mobile
                return redirect(obter_primeira_aba_mobile(request.user))
            else:
                # Desktop ou outras filiais: usar URL inicial normal
                return redirect(profile.filial_selecionada.url_inicial)
    except:
        pass
    
    # Fallback para Ibiporã
    return redirect('/')

def logout(request):
    logout_django(request)
    return redirect('login')

@login_required
def selecionar_filial(request, filial_id):
    filial = Filial.objects.get(id=filial_id)
    
    # Usando o related_name correto
    if filial in request.user.userprofile.filiais.all():
        request.user.userprofile.filial_selecionada = filial
        request.user.userprofile.save()
        messages.success(request, f'Filial alterada para {filial.nome}')
        return redirect(filial.url_inicial)
    else:
        messages.error(request, 'Você não tem acesso a esta filial')
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

# Mantenha sua classe CustomPasswordResetForm existente
class CustomPasswordResetForm(PasswordResetForm):
    def save(self, domain_override=None, subject_template_name='registration/password_reset_subject.txt', 
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=None, from_email=None, 
             request=None, html_email_template_name=None, extra_email_context=None):
        
        UserModel = get_user_model()
        email = self.cleaned_data["email"]
        users = UserModel._default_manager.filter(email__iexact=email)
        
        request_time = timezone.now()
        
        for user in users:
            context = {
                'email': user.email,
                'domain': domain_override or request.get_host(),
                'site_name': 'Portal Transcamila',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                'request_time': request_time,
                **(extra_email_context or {}),
            }
            self.send_mail(
                subject_template_name, 
                email_template_name, 
                context, 
                from_email,
                user.email, 
                html_email_template_name=html_email_template_name
            )

# usuarios/views.py
@login_required
def configuracoes_filial(request):
    """Página para selecionar filial - COM VERIFICAÇÃO"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # Se já tem filial selecionada, redireciona para ela
    if profile.filial_selecionada and request.method != 'POST':
        # Detectar se é mobile
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
        
        if is_mobile and profile.filial_selecionada.codigo == 'rondonopolis':
            # No mobile para Rondonópolis, redirecionar para primeira aba disponível do menu mobile
            return redirect(obter_primeira_aba_mobile(request.user))
        else:
            return redirect(profile.filial_selecionada.url_inicial)
    
    if request.method == 'POST':
        filial_id = request.POST.get('filial')
        if filial_id:
            try:
                filial = Filial.objects.get(id=filial_id)
                if filial in profile.filiais.all():
                    profile.filial_selecionada = filial
                    profile.save()
                    messages.success(request, f'Filial {filial.nome} selecionada!')
                    
                    # Detectar se é mobile
                    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
                    is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'])
                    
                    if is_mobile and filial.codigo == 'rondonopolis':
                        # No mobile para Rondonópolis, redirecionar para primeira aba disponível do menu mobile
                        return redirect(obter_primeira_aba_mobile(request.user))
                    else:
                        return redirect(filial.url_inicial)
                else:
                    messages.error(request, 'Você não tem acesso a esta filial')
            except:
                messages.error(request, 'Filial não encontrada')
    
    return render(request, 'usuarios/selecionar_filial.html', {
        'filiais_disponiveis': profile.filiais.all()
    })