# rondonopolis/templatetags/timezone_tags.py
from django import template
from django.utils import timezone as django_timezone
import pytz

register = template.Library()

# Fuso horário de Rondonópolis (Mato Grosso - America/Cuiaba)
TIMEZONE_RONDONOPOLIS = pytz.timezone('America/Cuiaba')


@register.filter
def timezone_rdn(value):
    """
    Converte um datetime para o fuso horário de Rondonópolis.
    Os horários são salvos no banco como naive no horário de Rondonópolis.
    Se vier aware do Django, converte para Rondonópolis.
    Se vier naive, assume que já está em Rondonópolis e retorna aware em Rondonópolis.
    
    Uso: {{ agendamento.portaria_liberacao|timezone_rdn|date:"d/m/Y H:i" }}
    """
    if not value:
        return value
    
    try:
        import pytz
        
        # Se já for timezone aware, converter para Rondonópolis
        if django_timezone.is_aware(value):
            # Pode estar em UTC ou no timezone padrão do Django
            if value.tzinfo == pytz.UTC:
                # Já está em UTC, converter diretamente para Rondonópolis
                return value.astimezone(TIMEZONE_RONDONOPOLIS)
            else:
                # Está em outro timezone, converter para UTC primeiro, depois para Rondonópolis
                utc_value = value.astimezone(pytz.UTC)
                return utc_value.astimezone(TIMEZONE_RONDONOPOLIS)
        
        # Se for naive, assumir que está salvo no horário de Rondonópolis
        # Localizar no timezone de Rondonópolis
        return TIMEZONE_RONDONOPOLIS.localize(value)
    except Exception:
        # Em caso de erro, retornar o valor original
        return value


@register.filter
def horario_ou_encaixe(value):
    """
    Retorna "ENCAIXE" se o horário for 00:00, caso contrário retorna o horário formatado.
    Uso: {{ agendamento.horario_agendado|horario_ou_encaixe }}
    """
    if not value:
        return value
    
    try:
        # Verificar se é 00:00
        if hasattr(value, 'hour') and hasattr(value, 'minute'):
            if value.hour == 0 and value.minute == 0:
                return 'ENCAIXE'
            # Retornar formato H:i
            return value.strftime('%H:%M')
        return value
    except Exception:
        return value
