# usuarios/context_processors.py
from .models import UserProfile

def filiais_context(request):
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            filiais = profile.filiais.all()
            filial_atual = profile.filial_selecionada
        except UserProfile.DoesNotExist:
            filiais = []
            filial_atual = None
    else:
        filiais = []
        filial_atual = None
    
    return {
        'filiais_usuario': filiais,
        'filial_atual': filial_atual
    }