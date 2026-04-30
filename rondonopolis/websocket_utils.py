"""
Utilitários para atualizações em tempo real (usando polling)
Nota: Sistema usa polling, mas mantém funções para compatibilidade
"""
from django.utils import timezone
from django.core.cache import cache


def enviar_atualizacao_tela(tela, action, agendamento_id=None, agendamento=None):
    """
    Marca no cache que há uma atualização (para que o polling detecte mudanças).
    
    Args:
        tela: 'portaria', 'checklist', 'armazem', 'onda', 'documentos'
        action: 'created', 'updated', ou 'deleted'
        agendamento_id: ID do agendamento (obrigatório se agendamento não for fornecido)
        agendamento: Instância do Agendamento (opcional)
    """
    try:
        # Marcar no cache que há atualização (o polling vai detectar)
        cache_key = f'atualizacao_{tela}_{timezone.now().timestamp()}'
        cache.set(cache_key, {
            'tela': tela,
            'action': action,
            'agendamento_id': agendamento_id or (agendamento.id if agendamento else None),
            'timestamp': timezone.now().isoformat()
        }, timeout=300)  # 5 minutos
    except Exception as e:
        # Não falhar silenciosamente
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao marcar atualização para {tela}: {str(e)}")


# Função de compatibilidade para manter código existente funcionando
def enviar_atualizacao_portaria(action, agendamento_id=None, agendamento=None):
    """Compatibilidade: redireciona para enviar_atualizacao_tela"""
    enviar_atualizacao_tela('portaria', action, agendamento_id, agendamento)

