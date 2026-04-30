from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.db import close_old_connections
from .utils import enviar_whatsapp_api
from .models import (
    ConfiguracaoNotificacao, NotificacaoProcesso, GrupoUsuario,
    Agendamento, PreferenciaNotificacaoUsuario
)
import logging
import threading

logger = logging.getLogger(__name__)

def enviar_confirmacao_chegada(agendamento, usuario, numero_whatsapp=None):
    try:
        context = {'usuario': usuario, 'agendamento': agendamento}
        html_content = render_to_string('emails/confirmacao_chegada.html', context)
        text_content = strip_tags(html_content)

        subject = f'Chegada Confirmada - {agendamento.motorista} - {agendamento.placa_veiculo}'
        recipient_list = ['adm.ibi@transcamila.com.br']

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        print(f"Email enviado para {recipient_list}")

        if numero_whatsapp:
            mensagem_whatsapp = (
                f"🚛 Chegada Confirmada!\n\n"
                f"Usuário: {usuario.first_name} {usuario.last_name}\n"
                f"Motorista: {agendamento.motorista}\n"
                f"Placa: {agendamento.placa_veiculo}\n"
                f"Tipo: {'Coleta' if agendamento.tipo == 'coleta' else 'Entrega'}\n"
                f"Agendado para: {agendamento.data_agendada.strftime('%d/%m/%Y')} às {agendamento.horario_agendado.strftime('%H:%M')}\n"
                f"Horário de chegada: {agendamento.horario_chegada.strftime('%H:%M')}\n\n"
                f"TLOGpainel — Transcamila"
            )
            enviar_whatsapp_api(numero_whatsapp, mensagem_whatsapp)

        return True
    except Exception as e:
        print(f"Erro ao enviar confirmação: {e}")
        return False


def get_etapas_processo(agendamento):
    """
    Retorna as etapas do processo com status atualizado
    Filtra etapas baseado no tipo (Coleta vs Entrega)
    
    Fluxo COLETA: Portaria → Checklist → Armazém → Onda → Documentos
    Fluxo ENTREGA: Portaria → Armazém → Documentos
    """
    from django.utils import timezone as tz
    
    etapas = []
    
    # Portaria - sempre presente
    etapas.append({
        'nome': 'Portaria',
        'concluida': bool(agendamento.portaria_liberacao),
        'data': agendamento.portaria_liberacao,
        'usuario': (agendamento.portaria_liberado_por.get_full_name() or agendamento.portaria_liberado_por.username) if agendamento.portaria_liberado_por else None,
    })
    
    # Checklist - APENAS PARA COLETA
    if agendamento.tipo == 'coleta':
        etapas.append({
            'nome': 'CheckList',
            'concluida': bool(agendamento.checklist_data),
            'data': agendamento.checklist_data,
            'usuario': (agendamento.checklist_preenchido_por.get_full_name() or agendamento.checklist_preenchido_por.username) if agendamento.checklist_preenchido_por else None,
            'numero': agendamento.checklist_numero,
        })
    
    # Onda / OD - Agora ambos têm esta etapa
    etapas.append({
        'nome': 'Onda' if agendamento.tipo == 'coleta' else 'OD',
        'concluida': bool(agendamento.onda_liberacao),
        'data': agendamento.onda_liberacao,
        'usuario': (agendamento.onda_liberado_por.get_full_name() or agendamento.onda_liberado_por.username) if agendamento.onda_liberado_por else None,
        'status': agendamento.get_onda_status_display(),
    })
    
    # Armazém - sempre presente
    etapas.append({
        'nome': 'Armazém',
        'concluida': bool(agendamento.armazem_chegada),
        'data': agendamento.armazem_chegada,
        'usuario': (agendamento.armazem_confirmado_por.get_full_name() or agendamento.armazem_confirmado_por.username) if agendamento.armazem_confirmado_por else None,
    })
    
    # Documentos - sempre presente
    etapas.append({
        'nome': 'Documentos',
        'concluida': bool(agendamento.documentos_liberacao),
        'data': agendamento.documentos_liberacao,
        'usuario': (agendamento.documentos_liberado_por.get_full_name() or agendamento.documentos_liberado_por.username) if agendamento.documentos_liberado_por else None,
    })
    
    # Identificar a primeira etapa pendente (não concluída) após todas as anteriores estarem concluídas
    primeira_pendente_encontrada = False
    todas_anteriores_concluidas = True
    
    for etapa in etapas:
        # Se a etapa já foi concluída, continua
        if etapa['concluida']:
            etapa['is_proxima_pendente'] = False
            continue
            
        # Se a etapa não foi concluída
        if not primeira_pendente_encontrada and todas_anteriores_concluidas:
            etapa['is_proxima_pendente'] = True
            primeira_pendente_encontrada = True
            todas_anteriores_concluidas = False
        else:
            etapa['is_proxima_pendente'] = False
            todas_anteriores_concluidas = False

    return etapas


def gerar_email_processo(agendamento, etapa_concluida=None, usuario_acao=None):
    """
    Gera o conteúdo do email com todas as etapas do processo
    etapa_concluida: 'portaria', 'checklist', 'armazem', 'onda' - indica qual etapa foi concluída
    usuario_acao: usuário que realizou a ação
    """
    etapas = get_etapas_processo(agendamento)
    
    context = {
        'agendamento': agendamento,
        'etapas': etapas,
        'status_geral': agendamento.get_status_geral_display(),
        'etapa_concluida': etapa_concluida,
        'usuario_acao': usuario_acao,
    }
    
    html_content = render_to_string('emails/processo_atualizado.html', context)
    text_content = strip_tags(html_content)
    
    # Título: Nome do motorista e placa
    assunto = f'{agendamento.motorista.nome} - {agendamento.placa_veiculo}'
    
    # Se a etapa concluída for documentos, adicionar "(Concluído)" ao título
    if etapa_concluida == 'documentos':
        assunto = f'{agendamento.motorista.nome} - {agendamento.placa_veiculo} (Concluído)'
    
    return {
        'subject': assunto,
        'html_content': html_content,
        'text_content': text_content,
    }


def _enviar_notificacao_etapa_sync(agendamento_id, etapa_nome, usuario_acao=None):
    """
    Função interna que faz o envio real de notificações (síncrona)
    Recebe o ID do agendamento para evitar problemas com objetos Django em threads
    """
    # Fechar conexões antigas e abrir nova conexão para esta thread
    close_old_connections()
    
    try:
        # Buscar o agendamento novamente na thread para garantir acesso ao banco
        agendamento = Agendamento.objects.select_related('motorista', 'transportadora').get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        logger.error(f"Agendamento {agendamento_id} não encontrado para envio de notificação")
        return
    except Exception as e:
        logger.error(f"Erro ao buscar agendamento {agendamento_id}: {e}")
        return
    
    try:
        # Variável para armazenar o grupo da próxima etapa (usado nas notificações push)
        grupo_proxima_etapa = None
        grupo = None
        
        # Se for a etapa de documentos (processo concluído), enviar para todos os grupos
        if etapa_nome == 'documentos':
            # Buscar todos os usuários únicos de todos os grupos ativos
            from django.contrib.auth import get_user_model
            User = get_user_model()
            usuarios_grupo = User.objects.filter(
                grupos_rondonopolis__ativo=True,
                is_active=True
            ).distinct()
            
            if not usuarios_grupo.exists():
                logger.info(f"Nenhum usuário encontrado para notificação de processo concluído")
                return
        else:
            # Mapear etapa para grupo correspondente
            if agendamento.tipo == 'entrega':
                # Fluxo ENTREGA: Portaria -> OD -> Armazém -> Documentos
                etapa_para_grupo = {
                    'portaria': 'armazem',                # Portaria libera -> vai para Armazém (CORRIGIDO)
                    'onda': 'armazem',                    # OD liberada (onda) -> vai para Armazém
                    'armazem': 'documentos',              # Armazém libera -> vai para Documentos (MANTIDO)
                    'armazem_saida': 'documentos',        # Armazém SAI -> vai para Documentos (NOVO)
                }
            else:
                # Fluxo COLETA: Portaria -> Checklist -> Armazém -> Documentos
                etapa_para_grupo = {
                    'portaria': 'checklist',              # Quando libera portaria, notifica grupo checklist
                    'checklist': 'armazem',               # Quando completa checklist, notifica grupo armazém
                    'armazem': 'documentos',              # Quando entra no armazém, notifica grupo documentos (MANTIDO POR COMPATIBILIDADE)
                    'armazem_saida': 'documentos',        # Quando SAI do armazém, notifica grupo documentos (NOVO FLUXO)
                }
            
            grupo_proxima_etapa = etapa_para_grupo.get(etapa_nome)
            
            if not grupo_proxima_etapa:
                # Não há próxima etapa
                return
            
            # Buscar grupo correspondente
            try:
                grupo = GrupoUsuario.objects.get(nome=grupo_proxima_etapa, ativo=True)
            except GrupoUsuario.DoesNotExist:
                logger.info(f"Grupo {grupo_proxima_etapa} não encontrado ou inativo")
                return
            
            # Buscar usuários do grupo que estão ativos
            usuarios_grupo = grupo.usuarios.filter(is_active=True)
            
            if not usuarios_grupo.exists():
                logger.info(f"Nenhum usuário ativo no grupo {grupo.get_nome_display()}")
                return
        
        # --- LÓGICA DE ADMINS ---
        # Buscar admins (superusers) ativos para receberem TODAS as notificações
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(is_superuser=True, is_active=True)
            
            # Combinar usuários do grupo com admins de forma segura
            user_ids = set()
            
            if usuarios_grupo is not None:
                user_ids.update(usuarios_grupo.values_list('id', flat=True))
                
            user_ids.update(admins.values_list('id', flat=True))
            
            # Re-consultar usuários para ter um QuerySet limpo e único
            usuarios_grupo = User.objects.filter(id__in=user_ids)
        except Exception as e:
            logger.error(f"Erro ao incluir admins na notificação: {e}")
            # Em caso de erro, continua apenas com o grupo original
            pass
        # ------------------------
        
        # Gerar conteúdo do email passando a etapa concluída e usuário que fez a ação
        email_data = gerar_email_processo(agendamento, etapa_concluida=etapa_nome, usuario_acao=usuario_acao)
        
        # Preparar mensagem para WhatsApp (apenas para etapas intermediárias, não para documentos)
        mensagem_whatsapp = None
        if etapa_nome != 'documentos':
            if etapa_nome == 'portaria':
                proxima_etapa_nome = "Armazém" if agendamento.tipo == 'entrega' else "Checklist"
                
                mensagem_whatsapp = (
                    f"Nova pendência identificada\n\n"
                    f"O motorista {agendamento.motorista.nome} foi liberado na portaria e encontra-se pendente na etapa de {proxima_etapa_nome}.\n\n"
                    f"Detalhes do veículo e serviço:\n\n"
                    f"Placa: {agendamento.placa_veiculo}\n"
                    f"Tipo de veículo: {agendamento.get_tipo_veiculo_display()}\n"
                    f"Serviço: {agendamento.get_tipo_display()}\n"
                    f"Transportadora: {agendamento.transportadora.nome}\n\n"
                    f"TLOGpainel\n"
                    f"Transcamila Cargas e Armazéns Gerais LTDA"
                )
            elif etapa_nome == 'checklist':
                # Determinar status da onda
                if agendamento.onda_liberacao:
                    status_onda = "LIBERADA"
                else:
                    status_onda = "PENDENTE"
                
                mensagem_whatsapp = (
                    f"Nova pendência identificada\n\n"
                    f"O motorista {agendamento.motorista.nome} concluiu o Checklist e encontra-se pendente na etapa de Armazém.\n\n"
                    f"Detalhes do veículo e serviço:\n\n"
                    f"Placa: {agendamento.placa_veiculo}\n"
                    f"Tipo de veículo: {agendamento.get_tipo_veiculo_display()}\n"
                    f"Serviço: {agendamento.get_tipo_display()}\n"
                    f"Transportadora: {agendamento.transportadora.nome}\n"
                    f"Status da Onda: {status_onda}\n\n"
                    f"TLOGpainel\n"
                    f"Transcamila Cargas e Armazéns Gerais LTDA"
                )
            elif etapa_nome == 'armazem':
                # Determinar status da onda (apenas para coleta)
                status_onda_linha = ""
                if agendamento.tipo == 'coleta':
                    if agendamento.onda_liberacao:
                        status_onda = "LIBERADA"
                    else:
                        status_onda = "PENDENTE"
                    status_onda_linha = f"Status da Onda: {status_onda}\n"
                
                mensagem_whatsapp = (
                    f"Nova pendência identificada\n\n"
                    f"O motorista {agendamento.motorista.nome} entrou no Armazém e encontra-se pendente na etapa de Documentos.\n\n"
                    f"Detalhes do veículo e serviço:\n\n"
                    f"Placa: {agendamento.placa_veiculo}\n"
                    f"Tipo de veículo: {agendamento.get_tipo_veiculo_display()}\n"
                    f"Serviço: {agendamento.get_tipo_display()}\n"
                    f"Transportadora: {agendamento.transportadora.nome}\n"
                    f"{status_onda_linha}\n"
                    f"TLOGpainel\n"
                    f"Transcamila Cargas e Armazéns Gerais LTDA"
                )
            elif etapa_nome == 'armazem_saida':
                # Determinar status da onda (apenas para coleta)
                status_onda_linha = ""
                if agendamento.tipo == 'coleta':
                    if agendamento.onda_liberacao:
                        status_onda = "LIBERADA"
                    else:
                        status_onda = "PENDENTE"
                    status_onda_linha = f"Status da Onda: {status_onda}\n"
                else:
                    # Para entrega (OD)
                    if agendamento.onda_liberacao:
                        status_onda = "LIBERADA"
                    else:
                        status_onda = "PENDENTE"
                    status_onda_linha = f"Status da OD: {status_onda}\n"
                
                mensagem_whatsapp = (
                    f"Nova pendência identificada\n\n"
                    f"O motorista {agendamento.motorista.nome} SAIU do Armazém e encontra-se pendente na etapa de Documentos.\n\n"
                    f"Detalhes do veículo e serviço:\n\n"
                    f"Placa: {agendamento.placa_veiculo}\n"
                    f"Tipo de veículo: {agendamento.get_tipo_veiculo_display()}\n"
                    f"Serviço: {agendamento.get_tipo_display()}\n"
                    f"Transportadora: {agendamento.transportadora.nome}\n"
                    f"{status_onda_linha}\n"
                    f"TLOGpainel\n"
                    f"Transcamila Cargas e Armazéns Gerais LTDA"
                )
        
        # Conjunto para rastrear emails já enviados (evitar duplicatas)
        emails_enviados = set()
        whatsapp_enviados = set()
        
        # Enviar notificações para cada usuário
        for usuario in usuarios_grupo:
            # Buscar configuração de notificação do usuário (email/whatsapp configurados pelo admin)
            try:
                config = ConfiguracaoNotificacao.objects.get(usuario=usuario)
            except ConfiguracaoNotificacao.DoesNotExist:
                config = None
                logger.info(f"Usuário {usuario.username} não tem configuração de notificação (email/whatsapp)")
            
            # Buscar preferências do usuário (se quer receber ou não)
            try:
                preferencias = PreferenciaNotificacaoUsuario.objects.get(usuario=usuario)
            except PreferenciaNotificacaoUsuario.DoesNotExist:
                # Se não tem preferências, criar com padrão True
                preferencias = PreferenciaNotificacaoUsuario.objects.create(
                    usuario=usuario,
                    receber_email=True,
                    receber_whatsapp=True,
                    receber_navegador=True
                )
            
            # Enviar email se configurado e usuário quer receber (evitar duplicatas)
            if config and config.email_destinatario and preferencias.receber_email:
                # Verificar se já foi enviado para este email
                email_destinatario_lower = config.email_destinatario.lower()
                if email_destinatario_lower not in emails_enviados:
                    emails_enviados.add(email_destinatario_lower)
                    try:
                        email = EmailMultiAlternatives(
                            subject=email_data['subject'],
                            body=email_data['text_content'],
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[config.email_destinatario],
                            reply_to=[settings.DEFAULT_FROM_EMAIL]
                        )
                        email.attach_alternative(email_data['html_content'], "text/html")
                        email.send(fail_silently=False)
                        
                        # Registrar notificação
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='email',
                            destinatario=config.email_destinatario,
                            assunto=email_data['subject'],
                            mensagem=email_data['text_content'],
                            enviado_com_sucesso=True,
                            etapa_quando_enviado=etapa_nome
                        )
                        logger.info(f"Email enviado para {config.email_destinatario} ({usuario.username}) - Processo {agendamento.ordem}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar email para {usuario.username}: {e}")
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='email',
                            destinatario=config.email_destinatario,
                            assunto=email_data['subject'],
                            mensagem=email_data['text_content'],
                            enviado_com_sucesso=False,
                            erro=str(e),
                            etapa_quando_enviado=etapa_nome
                        )
                else:
                    logger.info(f"Email já enviado para {config.email_destinatario} ({usuario.username}) - Processo {agendamento.ordem} - Pulando duplicata")
            
            # Enviar WhatsApp se configurado e usuário quer receber (não enviar para processo concluído)
            if etapa_nome != 'documentos' and config and config.whatsapp_destinatario and preferencias.receber_whatsapp and mensagem_whatsapp:
                # Limpar e formatar número para comparação (evitar duplicatas)
                whatsapp_limpo = config.whatsapp_destinatario.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if whatsapp_limpo not in whatsapp_enviados:
                    whatsapp_enviados.add(whatsapp_limpo)
                    try:
                        resultado = enviar_whatsapp_api(config.whatsapp_destinatario, mensagem_whatsapp)
                        
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='whatsapp',
                            destinatario=config.whatsapp_destinatario,
                            mensagem=mensagem_whatsapp,
                            enviado_com_sucesso=resultado.get('success', False),
                            erro=resultado.get('error'),
                            etapa_quando_enviado=etapa_nome
                        )
                        
                        if resultado.get('success'):
                            logger.info(f"WhatsApp enviado para {config.whatsapp_destinatario} ({usuario.username}) - Processo {agendamento.ordem}")
                        else:
                            logger.warning(f"Erro ao enviar WhatsApp para {usuario.username}: {resultado.get('error')}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar WhatsApp para {usuario.username}: {e}")
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='whatsapp',
                            destinatario=config.whatsapp_destinatario,
                            mensagem=mensagem_whatsapp,
                            enviado_com_sucesso=False,
                            erro=str(e),
                            etapa_quando_enviado=etapa_nome
                        )
                else:
                    logger.info(f"WhatsApp já enviado para {config.whatsapp_destinatario} ({usuario.username}) - Processo {agendamento.ordem} - Pulando duplicata")
            
            # Enviar notificação push se usuário quiser receber
            if preferencias.receber_navegador and preferencias.push_subscription:
                try:
                    # Importar função de forma segura para evitar import circular
                    import sys
                    import importlib
                    if 'rondonopolis.views' in sys.modules:
                        views_module = sys.modules['rondonopolis.views']
                        enviar_push_notification = getattr(views_module, 'enviar_push_notification', None)
                    else:
                        views_module = importlib.import_module('rondonopolis.views')
                        enviar_push_notification = getattr(views_module, 'enviar_push_notification', None)
                    
                    if enviar_push_notification:
                        # Determinar mensagem, título, URL e tag baseado na etapa
                        if etapa_nome == 'documentos':
                            mensagem_push = f"Processo concluído: {agendamento.motorista.nome} - {agendamento.placa_veiculo}"
                            titulo_push = "Processo Concluído"
                            url_push = '/rondonopolis/dashboard/'
                            tag_push = 'processo-concluido'
                            etapa_enviado = 'documentos'
                        elif etapa_nome == 'portaria':
                            if agendamento.tipo == 'entrega':
                                mensagem_push = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Armazém"
                                titulo_push = "Pendência de Armazém"
                                url_push = '/rondonopolis/armazem/'
                                tag_push = 'pendencia-armazem'
                                etapa_enviado = 'armazem'
                            else:
                                mensagem_push = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Checklist"
                                titulo_push = "Pendência de Checklist"
                                url_push = '/rondonopolis/checklist/'
                                tag_push = 'pendencia-checklist'
                                etapa_enviado = 'checklist'
                        elif etapa_nome == 'checklist' and grupo_proxima_etapa == 'armazem':
                            mensagem_push = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Armazém"
                            titulo_push = "Pendência de Armazém"
                            url_push = '/rondonopolis/armazem/'
                            tag_push = 'pendencia-armazem'
                            etapa_enviado = 'armazem'
                        elif etapa_nome == 'armazem' and grupo_proxima_etapa == 'liberacao_documentos':
                            mensagem_push = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Liberação de Documentos"
                            titulo_push = "Pendência de Documentos"
                            url_push = '/rondonopolis/documentos/'
                            tag_push = 'pendencia-documentos'
                            etapa_enviado = 'liberacao_documentos'
                        else:
                            # Fallback para outros casos
                            if grupo:
                                grupo_display = grupo.get_nome_display() if hasattr(grupo, 'get_nome_display') else 'próxima etapa'
                            else:
                                grupo_display = 'próxima etapa'
                            mensagem_push = f"Novo processo {agendamento.ordem} aguardando {grupo_display}"
                            titulo_push = f"Processo {agendamento.ordem}"
                            url_push = '/rondonopolis/dashboard/'
                            tag_push = 'processo-atualizado'
                            etapa_enviado = grupo_proxima_etapa if grupo_proxima_etapa else etapa_nome
                        
                        # Enviar push notification real do sistema operacional
                        sucesso = enviar_push_notification(usuario, mensagem_push, titulo_push, url=url_push, tag=tag_push)
                        
                        if sucesso:
                            logger.info(f"Push notification enviada para {usuario.username} - Processo {agendamento.ordem} - Etapa: {etapa_nome}")
                        else:
                            logger.warning(f"Falha ao enviar push notification para {usuario.username}")
                        
                        # Registrar notificação para histórico/logs
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='navegador',
                            destinatario=usuario.email or usuario.username,
                            mensagem=mensagem_push,
                            enviado_com_sucesso=sucesso,
                            etapa_quando_enviado=etapa_enviado
                        )
                except Exception as e:
                    logger.error(f"Erro ao enviar push notification para {usuario.username}: {e}")
                    # Registrar como falha apenas para logs
                    try:
                        # Determinar mensagem para registro histórico em caso de erro
                        if etapa_nome == 'documentos':
                            mensagem_erro = f"Processo concluído: {agendamento.motorista.nome} - {agendamento.placa_veiculo}"
                            etapa_enviado = 'documentos'
                        elif etapa_nome == 'portaria':
                            if agendamento.tipo == 'entrega':
                                mensagem_erro = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Armazém"
                                etapa_enviado = 'armazem'
                            else:
                                mensagem_erro = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Checklist"
                                etapa_enviado = 'checklist'
                        elif etapa_nome == 'checklist':
                            mensagem_erro = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Armazém"
                            etapa_enviado = 'armazem'
                        elif etapa_nome == 'armazem':
                            mensagem_erro = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Liberação de Documentos"
                            etapa_enviado = 'liberacao_documentos'
                        elif etapa_nome == 'armazem_saida':
                            mensagem_erro = f"Nova pendência: {agendamento.motorista.nome} - {agendamento.placa_veiculo} aguardando Liberação de Documentos (Saída Armazém)"
                            etapa_enviado = 'liberacao_documentos'
                        else:
                            mensagem_erro = f"Novo processo {agendamento.ordem} atualizado"
                            etapa_enviado = etapa_nome
                        
                        NotificacaoProcesso.objects.create(
                            agendamento=agendamento,
                            tipo='navegador',
                            destinatario=usuario.email or usuario.username,
                            mensagem=mensagem_erro,
                            enviado_com_sucesso=False,
                            erro=str(e),
                            etapa_quando_enviado=etapa_enviado
                        )
                    except:
                        pass
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificações da etapa {etapa_nome}: {e}")
    finally:
        # Fechar conexões do banco de dados ao final da thread
        close_old_connections()


def enviar_notificacao_etapa(agendamento, etapa_nome, usuario_acao=None):
    """
    Envia notificações para usuários do grupo da próxima etapa (assíncrono)
    Apenas envia se o usuário estiver no grupo E quiser receber notificações
    etapa_nome: 'portaria', 'checklist', 'armazem', 'onda'
    
    Esta função inicia o envio em uma thread separada para não bloquear a resposta HTTP
    """
    # Passar apenas o ID do agendamento para evitar problemas com objetos Django em threads
    agendamento_id = agendamento.id
    
    # Criar uma thread para enviar notificações sem bloquear
    thread = threading.Thread(
        target=_enviar_notificacao_etapa_sync,
        args=(agendamento_id, etapa_nome, usuario_acao),
        daemon=True
    )
    thread.start()


def _notificar_agendamentos_criados_sync(agendamento_ids, quantidade_criados):
    """
    Função interna que faz o envio real de notificações quando agendamentos são criados (síncrona)
    Recebe os IDs dos agendamentos para evitar problemas com objetos Django em threads
    """
    # Fechar conexões antigas e abrir nova conexão para esta thread
    close_old_connections()
    
    try:
        # Buscar os agendamentos novamente na thread para garantir acesso ao banco
        agendamentos = Agendamento.objects.filter(id__in=agendamento_ids)
        
        if not agendamentos.exists():
            logger.info("Nenhum agendamento encontrado para notificação")
            return
        
        # Pegar a data do primeiro agendamento (todos devem ter a mesma data)
        data_agendada = agendamentos.first().data_agendada
        
        # Contar total de agendamentos do dia
        from .utils import timezone_today
        hoje = timezone_today()
        # Se a data do agendamento for diferente de hoje, usar a data do agendamento
        if data_agendada != hoje:
            data_filtro = data_agendada
        else:
            data_filtro = hoje
        
        total_agendamentos_dia = Agendamento.objects.filter(data_agendada=data_filtro).count()
        
        # Buscar grupo de porteiros
        try:
            grupo_portaria = GrupoUsuario.objects.get(nome='portaria', ativo=True)
        except GrupoUsuario.DoesNotExist:
            logger.info("Grupo de portaria não encontrado ou inativo")
            return
        
        # Buscar usuários do grupo de portaria que estão ativos
        usuarios_grupo = grupo_portaria.usuarios.filter(is_active=True)
        
        if not usuarios_grupo.exists():
            logger.info("Nenhum usuário ativo no grupo de portaria")
            return
        
        # Preparar mensagem com quantidade total do dia
        data_formatada = data_filtro.strftime('%d/%m/%Y')
        assunto = f"Agendamentos do Dia - {data_formatada}"
        
        mensagem_whatsapp = (
            f"Agendamentos adicionados\n\n"
            f"Total de {total_agendamentos_dia} agendamento(s) para o dia {data_formatada}.\n\n"
            f"TLOGpainel\n"
            f"Transcamila Cargas e Armazéns Gerais LTDA"
        )
        
        mensagem_email = (
            f"Agendamentos adicionados ao sistema.\n\n"
            f"Total de {total_agendamentos_dia} agendamento(s) para o dia {data_formatada}.\n"
        )
        
        # Conjunto para rastrear emails e WhatsApp já enviados (evitar duplicatas)
        emails_enviados = set()
        whatsapp_enviados = set()
        
        # Enviar notificações para cada usuário
        for usuario in usuarios_grupo:
            # Buscar configuração de notificação do usuário (email/whatsapp configurados pelo admin)
            try:
                config = ConfiguracaoNotificacao.objects.get(usuario=usuario)
            except ConfiguracaoNotificacao.DoesNotExist:
                config = None
                logger.info(f"Usuário {usuario.username} não tem configuração de notificação (email/whatsapp)")
            
            # Buscar preferências do usuário (se quer receber ou não)
            try:
                preferencias = PreferenciaNotificacaoUsuario.objects.get(usuario=usuario)
            except PreferenciaNotificacaoUsuario.DoesNotExist:
                # Se não tem preferências, criar com padrão True
                preferencias = PreferenciaNotificacaoUsuario.objects.create(
                    usuario=usuario,
                    receber_email=True,
                    receber_whatsapp=True,
                    receber_navegador=True
                )
            
            # Enviar email se configurado e usuário quer receber (evitar duplicatas)
            if config and config.email_destinatario and preferencias.receber_email:
                email_destinatario_lower = config.email_destinatario.lower()
                if email_destinatario_lower not in emails_enviados:
                    emails_enviados.add(email_destinatario_lower)
                    try:
                        email = EmailMultiAlternatives(
                            subject=assunto,
                            body=mensagem_email,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[config.email_destinatario],
                            reply_to=[settings.DEFAULT_FROM_EMAIL]
                        )
                        email.send(fail_silently=False)
                        
                        logger.info(f"Email enviado para {config.email_destinatario} ({usuario.username}) - Agendamentos criados")
                    except Exception as e:
                        logger.error(f"Erro ao enviar email para {usuario.username}: {e}")
                else:
                    logger.info(f"Email já enviado para {config.email_destinatario} ({usuario.username}) - Agendamentos criados - Pulando duplicata")
            
            # Enviar WhatsApp se configurado e usuário quer receber (evitar duplicatas)
            if config and config.whatsapp_destinatario and preferencias.receber_whatsapp and mensagem_whatsapp:
                whatsapp_limpo = config.whatsapp_destinatario.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if whatsapp_limpo not in whatsapp_enviados:
                    whatsapp_enviados.add(whatsapp_limpo)
                    try:
                        resultado = enviar_whatsapp_api(config.whatsapp_destinatario, mensagem_whatsapp)
                        
                        if resultado.get('success'):
                            logger.info(f"WhatsApp enviado para {config.whatsapp_destinatario} ({usuario.username}) - Agendamentos criados")
                        else:
                            logger.warning(f"Erro ao enviar WhatsApp para {usuario.username}: {resultado.get('error')}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar WhatsApp para {usuario.username}: {e}")
                else:
                    logger.info(f"WhatsApp já enviado para {config.whatsapp_destinatario} ({usuario.username}) - Agendamentos criados - Pulando duplicata")
            
            # Enviar notificação push se usuário quiser receber
            if preferencias.receber_navegador and preferencias.push_subscription:
                try:
                    # Importar função de forma segura para evitar import circular
                    import sys
                    import importlib
                    if 'rondonopolis.views' in sys.modules:
                        views_module = sys.modules['rondonopolis.views']
                        enviar_push_notification = getattr(views_module, 'enviar_push_notification', None)
                    else:
                        views_module = importlib.import_module('rondonopolis.views')
                        enviar_push_notification = getattr(views_module, 'enviar_push_notification', None)
                    
                    if enviar_push_notification:
                        mensagem_push = f"{total_agendamentos_dia} agendamento(s) para {data_formatada}"
                        titulo_push = f"Novos Agendamentos - {data_formatada}"
                        url_push = '/rondonopolis/portaria/'
                        tag_push = 'agendamentos-criados'
                        
                        # Enviar push notification
                        sucesso = enviar_push_notification(usuario, mensagem_push, titulo_push, url=url_push, tag=tag_push)
                        
                        if sucesso:
                            logger.info(f"Push notification enviada para {usuario.username} - Agendamentos criados")
                        else:
                            logger.warning(f"Falha ao enviar push notification para {usuario.username}")
                except Exception as e:
                    logger.error(f"Erro ao enviar push notification para {usuario.username}: {e}")
    
    except Exception as e:
        logger.error(f"Erro ao notificar agendamentos criados: {e}")


def notificar_agendamentos_criados(agendamento_ids, quantidade_criados):
    """
    Notifica o grupo de porteiros quando agendamentos são criados (assíncrono)
    Esta função inicia o envio em uma thread separada para não bloquear a resposta HTTP
    """
    # Criar uma thread para enviar notificações sem bloquear
    thread = threading.Thread(
        target=_notificar_agendamentos_criados_sync,
        args=(agendamento_ids, quantidade_criados),
        daemon=True
    )
    thread.start()


def atualizar_email_processo(agendamento):
    """
    Atualiza o email do processo quando uma etapa é concluída
    Envia email atualizado para usuários que têm configuração e querem receber
    """
    try:
        # Buscar todas as configurações de notificação
        configs = ConfiguracaoNotificacao.objects.all()
        
        if not configs.exists():
            return
        
        # Gerar conteúdo do email atualizado
        email_data = gerar_email_processo(agendamento)
        
        # Enviar para usuários que querem receber
        emails_enviados = set()
        for config in configs:
            # Verificar se usuário quer receber email
            try:
                preferencias = PreferenciaNotificacaoUsuario.objects.get(usuario=config.usuario)
                if not preferencias.receber_email:
                    continue
            except PreferenciaNotificacaoUsuario.DoesNotExist:
                # Se não tem preferências, assume que quer receber
                pass
            
            if config.email_destinatario and config.email_destinatario not in emails_enviados:
                emails_enviados.add(config.email_destinatario)
                try:
                    email = EmailMultiAlternatives(
                        subject=email_data['subject'],
                        body=email_data['text_content'],
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[config.email_destinatario],
                        reply_to=[settings.DEFAULT_FROM_EMAIL]
                    )
                    email.attach_alternative(email_data['html_content'], "text/html")
                    email.send(fail_silently=False)
                    
                    logger.info(f"Email atualizado enviado para {config.email_destinatario} ({config.usuario.username}) - Processo {agendamento.ordem}")
                except Exception as e:
                    logger.error(f"Erro ao enviar email atualizado para {config.usuario.username}: {e}")
    
    except Exception as e:
        logger.error(f"Erro ao atualizar email do processo: {e}")
