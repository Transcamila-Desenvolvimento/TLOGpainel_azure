from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Agendamento, ControleAtualizacao

@receiver(post_save, sender=Agendamento)
def agendamento_post_save(sender, instance, created, **kwargs):
    """
    Sinal disparado sempre que um agendamento é salvo.
    Atualiza os timestamps das telas relevantes.
    """
    telas_afetadas = set()
    
    # Se foi criado agora, afeta Portaria (e Lista de Agendamentos)
    if created:
        telas_afetadas.add('portaria')
        telas_afetadas.add('agendamentos')
    # Lógica "Generosa": Se o objeto está em determinada etapa, avisa a tela correspondente.
    # Isso garante que qualquer edição (mesmo que não mude o status) reflita na tela.

    agora = timezone.now()
    hoje = timezone.localdate(agora)

    # REGRAS DE OTIMIZAÇÃO:
    # A maioria das telas operacionais (Portaria, Armazém, Onda, CheckList) filtra por "hoje".
    # Se o agendamento não é de hoje, não precisamos forçar atualização nessas telas.
    eh_hoje = (instance.data_agendada == hoje)

    # 1. Regras Globais
    # Lista Geral de Agendamentos (pode mostrar outros dias, então mantém)
    telas_afetadas.add('agendamentos')

    if eh_hoje:
        telas_afetadas.add('portaria')       # Sempre impacta portaria (liberados/agendados) do dia

        # 2. Se é coleta, sempre avisa a onda (para pegar imports/criações novas)
        if instance.tipo == 'coleta':
            telas_afetadas.add('onda')

        # 3. Se já passou pela portaria
        if instance.portaria_liberacao:
            telas_afetadas.add('checklist')
            if instance.tipo == 'entrega':
                telas_afetadas.add('armazem') # Entrega vai direto pro armazem

        # 4. Se já fez checklist (Coleta)
        if instance.checklist_data:
            telas_afetadas.add('checklist')  # Atualiza para mover para concluídos
            telas_afetadas.add('onda')       # Entra na fila de onda
            telas_afetadas.add('armazem')    # Pode ser visivel no armazem (se onda liberada)

        # 5. Se onda liberada
        if instance.onda_liberacao:
            telas_afetadas.add('onda')
            telas_afetadas.add('armazem')    # Libera para entrada no armazem

        # 6. Se entrou no armazém
        if instance.armazem_chegada:
            telas_afetadas.add('armazem')            # Atualiza para mover para concluídos/trânsito
            telas_afetadas.add('liberacao-documentos') # Entra na fila de documentos

        # 7. Se documentos liberados
        if instance.documentos_liberacao:
            telas_afetadas.add('liberacao-documentos') # Move para concluídos

    # Atualizar timestamps no banco (transacional e seguro para multi-worker)
    for tela in telas_afetadas:
        ControleAtualizacao.objects.update_or_create(
            tela=tela,
            defaults={'ultima_atualizacao': agora}
        )

@receiver(post_delete, sender=Agendamento)
def agendamento_post_delete(sender, instance, **kwargs):
    """
    Se algo for excluído, força atualização em tudo para garantir limpeza
    """
    telas = ['portaria', 'checklist', 'onda', 'armazem', 'liberacao-documentos', 'agendamentos']
    agora = timezone.now()
    for tela in telas:
        ControleAtualizacao.objects.update_or_create(
            tela=tela,
            defaults={'ultima_atualizacao': agora}
        )
