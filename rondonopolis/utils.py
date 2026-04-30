import pandas as pd
from django.db import transaction
from .models import Agendamento, Transportadora, Motorista, GrupoUsuario, ConfiguracaoNotificacao, PreferenciaNotificacaoUsuario
import logging
import requests
from django.conf import settings
from django.utils import timezone as django_timezone
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
import pytz

logger = logging.getLogger(__name__)

# Fuso horário de Rondonópolis (Mato Grosso - America/Cuiaba)
TIMEZONE_RONDONOPOLIS = pytz.timezone('America/Cuiaba')


def timezone_now():
    """
    Retorna o datetime atual no fuso horário de Rondonópolis como datetime naive.
    Usa America/Cuiaba (UTC-4) que é o fuso horário de Mato Grosso.
    Retorna como naive para ser salvo diretamente no banco no horário de Rondonópolis.
    """
    import pytz
    # Obter o datetime atual em UTC
    now_utc = django_timezone.now()
    
    # Se não estiver em UTC, converter para UTC primeiro
    if now_utc.tzinfo != pytz.UTC:
        if now_utc.tzinfo is None:
            # Se for naive, assumir que está no timezone padrão e converter para UTC
            from django.conf import settings
            default_tz = pytz.timezone(settings.TIME_ZONE)
            now_utc = default_tz.localize(now_utc).astimezone(pytz.UTC)
        else:
            now_utc = now_utc.astimezone(pytz.UTC)
    
    # Converter de UTC para o fuso horário de Rondonópolis
    now_rdn = now_utc.astimezone(TIMEZONE_RONDONOPOLIS)
    
    # Retornar como aware no fuso horário de Rondonópolis
    return now_rdn


def timezone_today():
    """
    Retorna a data de hoje no fuso horário de Rondonópolis.
    """
    return timezone_now().date()


def converter_para_timezone_rdn(datetime_value):
    """
    Converte um datetime para o fuso horário de Rondonópolis.
    Útil para converter datetimes antes de passar para templates.
    Os horários são salvos no banco como naive no horário de Rondonópolis.
    Se vier aware do Django, converte para Rondonópolis.
    Se vier naive, assume que já está em Rondonópolis e retorna aware em Rondonópolis.
    """
    if not datetime_value:
        return datetime_value
    
    try:
        import pytz
        
        if django_timezone.is_aware(datetime_value):
            # Se já for aware, pode estar em UTC ou no timezone padrão do Django
            # Converter para Rondonópolis
            if datetime_value.tzinfo == pytz.UTC:
                # Já está em UTC, converter diretamente para Rondonópolis
                return datetime_value.astimezone(TIMEZONE_RONDONOPOLIS)
            else:
                # Está em outro timezone, converter para UTC primeiro, depois para Rondonópolis
                utc_value = datetime_value.astimezone(pytz.UTC)
                return utc_value.astimezone(TIMEZONE_RONDONOPOLIS)
        else:
            # Se for naive, assumir que está salvo no horário de Rondonópolis
            # Localizar no timezone de Rondonópolis
            return TIMEZONE_RONDONOPOLIS.localize(datetime_value)
    except Exception as e:
        logger.error(f"Erro ao converter datetime para Rondonópolis: {str(e)}")
        return datetime_value

def importar_agendamentos(arquivo_excel):
    """
    Importa agendamentos de planilha Excel, criando transportadoras E motoristas se necessário
    """
    try:
        # Ler a planilha
        df = pd.read_excel(arquivo_excel, sheet_name='Lista Operação')
        
        # Log para debug: verificar colunas disponíveis
        logger.info(f"Colunas encontradas no Excel: {list(df.columns)}")
        
        # Contadores para relatório
        total_linhas = len(df)
        agendamentos_criados = 0
        agendamentos_atualizados = 0
        transportadoras_criadas = 0
        motoristas_criados = 0
        erros = 0
        agendamentos_criados_ids = []  # Para notificação
        agendamentos_cancelados = 0  # Contador de agendamentos cancelados ignorados
        
        # Procurar pela coluna U/STATUS uma vez antes do loop (otimização)
        # Pode estar com diferentes nomes: 'U/STATUS', 'U-STATUS', 'STATUS', etc
        status_coluna_nome = None
        for col in df.columns:
            col_limpo = str(col).strip().upper()
            # Preferir coluna que contenha 'U/STATUS' ou 'U-STATUS'
            if 'U/STATUS' in col_limpo or 'U-STATUS' in col_limpo:
                status_coluna_nome = col
                logger.info(f"Coluna U/STATUS encontrada: '{col}' (normalizada: '{col_limpo}')")
                break
            elif col_limpo == 'STATUS' and not status_coluna_nome:
                # Guardar como alternativa se não encontrou U/STATUS
                status_coluna_nome = col
                logger.info(f"Coluna STATUS encontrada: '{col}' (usada como alternativa)")
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Pular linhas vazias ou com dados inválidos
                    if pd.isna(row.get('ORDEM')) or pd.isna(row.get('MOTORISTA')):
                        continue
                    
                    # Verificar se o agendamento está cancelado (coluna U/STATUS = "CANCELADO")
                    if status_coluna_nome:
                        try:
                            status_raw = row.get(status_coluna_nome)
                            if not pd.isna(status_raw) and status_raw is not None:
                                status_value = str(status_raw).strip().upper()
                                # Se o status for "CANCELADO", pular esta linha
                                if status_value == 'CANCELADO':
                                    ordem_atual = str(row.get('ORDEM', 'N/A')).strip()
                                    logger.debug(f"Agendamento {ordem_atual} ignorado - Status: CANCELADO")
                                    agendamentos_cancelados += 1
                                    continue
                        except Exception as e:
                            logger.warning(f"Erro ao verificar status para ordem {row.get('ORDEM', 'N/A')}: {str(e)}")
                            # Se houver erro ao ler o status, continuar processando (não bloquear)
                    
                    # Buscar ou criar transportadora
                    nome_transportadora = str(row.get('TRANSPORTADORA', '')).strip().upper()
                    if not nome_transportadora:
                        nome_transportadora = 'TRANSPORTADORA NÃO INFORMADA'
                    
                    transportadora, created = Transportadora.objects.get_or_create(
                        nome=nome_transportadora,
                        defaults={
                            'cnpj': str(row.get('CNPJ', ''))[:18] if 'CNPJ' in df.columns else '',
                            'telefone': str(row.get('TELEFONE', ''))[:15] if 'TELEFONE' in df.columns else ''
                        }
                    )
                    
                    if created:
                        transportadoras_criadas += 1
                    
                    # Buscar ou criar motorista (SEM telefone - campo em branco)
                    nome_motorista = str(row.get('MOTORISTA', '')).strip().upper()
                    if not nome_motorista:
                        continue
                    
                    motorista, created = Motorista.objects.get_or_create(
                        nome=nome_motorista,
                        defaults={
                            'telefone': None  # Telefone em branco inicialmente
                        }
                    )
                    
                    if created:
                        motoristas_criados += 1
                    
                    # Converter data e hora
                    data_agendamento = row.get('DATA AGENDAMENTO')
                    if pd.isna(data_agendamento):
                        continue
                    
                    # Se for timestamp do pandas, converter para datetime
                    if isinstance(data_agendamento, pd.Timestamp):
                        data_agendamento = data_agendamento.to_pydatetime()
                    
                    # Extrair data e hora separadamente
                    data_agendada = data_agendamento.date()
                    horario_agendado = data_agendamento.time()
                    
                    # Mapear tipo (COLETA/ENTREGA)
                    tipo_raw = str(row.get('TIPO', '')).strip().upper()
                    if tipo_raw == 'COLETA':
                        tipo = 'coleta'
                    elif tipo_raw == 'ENTREGA':
                        tipo = 'entrega'
                    else:
                        tipo = 'coleta'  # default
                    
                    # Mapear tipo de veículo
                    veiculo_raw = str(row.get('VEICULO', '')).strip().upper()
                    tipo_veiculo_map = {
                        'BAU TRUCK': 'truck',
                        'SIDER CARRETA': 'carreta', 
                        'GRANELEIRO CARRETA': 'carreta',
                        'GRANELEIRO BITREM': 'bitrem',
                        'BITREM': 'bitrem',
                        'RODOTREM': 'rodotrem',
                        'VUC': 'vuc',
                        'TOCO': 'toco',
                        'LS': 'ls'
                    }
                    tipo_veiculo = tipo_veiculo_map.get(veiculo_raw, 'truck')
                    
                    # Tratar peso (pode ser string ou número)
                    peso_raw = row.get('PESO', 0)
                    if pd.isna(peso_raw):
                        peso = 0
                    else:
                        try:
                            peso = float(peso_raw)
                        except (ValueError, TypeError):
                            peso = 0
                    
                    # Verificar se agendamento já existe pelo campo ORDEM
                    ordem = str(row.get('ORDEM', '')).strip()
                    
                    # Ler coluna AD/Documentos (pode estar vazia e pode conter valores grandes separados por vírgula)
                    coluna_ad = None
                    # Verificar se a coluna AD/DOCUMENTOS existe (pode estar como 'AD', 'DOCUMENTOS', 'AD/DOCUMENTOS', etc)
                    coluna_ad_nome = None
                    for col in df.columns:
                        col_limpo = str(col).strip().upper()
                        # Aceitar variações: 'AD', 'DOCUMENTOS', 'AD/DOCUMENTOS', 'AD / DOCUMENTOS', etc
                        if col_limpo == 'AD' or col_limpo == 'DOCUMENTOS' or col_limpo == 'AD/DOCUMENTOS' or col_limpo == 'AD / DOCUMENTOS':
                            coluna_ad_nome = col
                            logger.info(f"Coluna AD/DOCUMENTOS encontrada: '{col}' (normalizada: '{col_limpo}')")
                            break
                    
                    # Se não encontrou com nome exato, procurar por qualquer coluna que contenha 'DOCUMENTOS' ou 'AD'
                    if not coluna_ad_nome:
                        for col in df.columns:
                            col_limpo = str(col).strip().upper()
                            if 'DOCUMENTOS' in col_limpo or (col_limpo == 'AD'):
                                coluna_ad_nome = col
                                logger.info(f"Coluna AD/DOCUMENTOS encontrada (busca parcial): '{col}' (normalizada: '{col_limpo}')")
                                break
                    
                    if coluna_ad_nome:
                        try:
                            ad_raw = row.get(coluna_ad_nome)
                            if not pd.isna(ad_raw) and ad_raw is not None:
                                coluna_ad = str(ad_raw).strip()
                                # Se a string estiver vazia após strip, definir como None
                                if not coluna_ad or coluna_ad == 'nan':
                                    coluna_ad = None
                                else:
                                    logger.debug(f"Valor AD encontrado para ordem {ordem}: {coluna_ad[:50]}...")
                            else:
                                coluna_ad = None
                        except Exception as e:
                            logger.warning(f"Erro ao ler coluna AD para ordem {ordem}: {str(e)}")
                            coluna_ad = None
                    else:
                        # Se a coluna AD não existir no Excel, definir como None
                        coluna_ad = None
                        if index == 0:  # Log apenas na primeira linha para não poluir
                            logger.info(f"Coluna AD/Documentos não encontrada no Excel. Colunas disponíveis: {list(df.columns)}")
                    agendamento_existente = Agendamento.objects.filter(ordem=ordem).first()
                    
                    if agendamento_existente:
                        # Atualizar agendamento existente
                        agendamento_existente.motorista = motorista
                        agendamento_existente.data_agendada = data_agendada
                        agendamento_existente.horario_agendado = horario_agendado
                        agendamento_existente.tipo = tipo
                        agendamento_existente.placa_veiculo = str(row.get('PLACA', ''))[:8]
                        agendamento_existente.transportadora = transportadora
                        agendamento_existente.peso = peso
                        agendamento_existente.tipo_veiculo = tipo_veiculo
                        agendamento_existente.coluna_ad = coluna_ad
                        agendamento_existente.save()
                        agendamentos_atualizados += 1
                        
                    else:
                        # Criar novo agendamento
                        agendamento = Agendamento.objects.create(
                            ordem=ordem,
                            motorista=motorista,
                            data_agendada=data_agendada,
                            horario_agendado=horario_agendado,
                            tipo=tipo,
                            placa_veiculo=str(row.get('PLACA', ''))[:8],
                            transportadora=transportadora,
                            peso=peso,
                            tipo_veiculo=tipo_veiculo,
                            coluna_ad=coluna_ad
                        )
                        agendamentos_criados += 1
                        agendamentos_criados_ids.append(agendamento.id)
                        
                        # Enviar atualização para todas as telas (apenas se for para hoje)
                        try:
                            from django.utils import timezone
                            if agendamento.data_agendada == timezone.now().date():
                                from .websocket_utils import enviar_atualizacao_tela
                                enviar_atualizacao_tela('portaria', 'created', agendamento=agendamento)
                                enviar_atualizacao_tela('onda', 'created', agendamento=agendamento)
                        except Exception as e:
                            logger.error(f"Erro ao enviar atualização na importação: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Erro na linha {index + 2}: {str(e)}")
                    erros += 1
                    continue
        
        # Notificar grupo de porteiros sobre os agendamentos criados (assíncrono)
        if agendamentos_criados_ids:
            try:
                from .mensagens import notificar_agendamentos_criados
                notificar_agendamentos_criados(agendamentos_criados_ids, agendamentos_criados)
            except Exception as e:
                logger.error(f"Erro ao notificar agendamentos criados: {str(e)}")
                # Não falhar a importação se a notificação falhar
        
        # Enviar email com pendências de ondas após importação (assíncrono para não bloquear)
        try:
            import threading
            thread = threading.Thread(target=enviar_email_pendencias_ondas)
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"Erro ao iniciar thread de envio de email: {str(e)}")
            # Não falhar a importação se o email falhar
        
        # Retornar relatório da importação
        return {
            'success': True,
            'total_linhas': total_linhas,
            'agendamentos_criados': agendamentos_criados,
            'agendamentos_atualizados': agendamentos_atualizados,
            'agendamentos_cancelados': agendamentos_cancelados,  # Agendamentos com status CANCELADO ignorados
            'transportadoras_criadas': transportadoras_criadas,
            'motoristas_criados': motoristas_criados,
            'erros': erros
        }
        
    except Exception as e:
        logger.error(f"Erro geral na importação: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def criar_agendamento_manual(dados_formulario):
    """
    Cria um agendamento manualmente a partir dos dados do formulário.
    Similar à importação, mas recebe dados diretamente do formulário.
    """
    try:
        from django.db import transaction
        from datetime import datetime
        
        # Extrair dados do formulário
        motorista_id = dados_formulario.get('motorista')
        data_agendada_str = dados_formulario.get('data_agendada', '')
        horario_agendado_str = dados_formulario.get('horario_agendado', '')
        tipo = dados_formulario.get('tipo', '').strip()
        placa_veiculo = dados_formulario.get('placa_veiculo', '').strip().upper()[:8]
        transportadora_id = dados_formulario.get('transportadora')
        peso = dados_formulario.get('peso', 0)
        tipo_veiculo_raw = dados_formulario.get('tipo_veiculo', '').strip().upper()
        observacoes = dados_formulario.get('observacoes', '').strip()
        ordem = dados_formulario.get('ordem', '').strip()
        is_encaixe = dados_formulario.get('encaixe') == 'on' or dados_formulario.get('encaixe') == True
        
        # Validações básicas
        if not motorista_id:
            return {'success': False, 'error': 'Motorista é obrigatório'}
        
        if not data_agendada_str:
            return {'success': False, 'error': 'Data agendada é obrigatória'}
        
        # Se for encaixe, não precisa de horário
        if not is_encaixe and not horario_agendado_str:
            return {'success': False, 'error': 'Horário agendado é obrigatório'}
        
        if not tipo or tipo not in ['coleta', 'entrega']:
            return {'success': False, 'error': 'Tipo inválido'}
        
        if not placa_veiculo:
            return {'success': False, 'error': 'Placa do veículo é obrigatória'}
        
        if not transportadora_id:
            return {'success': False, 'error': 'Transportadora é obrigatória'}
        
        try:
            peso = float(peso)
            if peso <= 0:
                return {'success': False, 'error': 'Peso deve ser maior que zero'}
        except (ValueError, TypeError):
            return {'success': False, 'error': 'Peso inválido'}
        
        # Mapear tipo de veículo (formulário usa maiúsculas, modelo usa minúsculas)
        tipo_veiculo_map = {
            'VUC': 'vuc',
            'TOCO': 'toco',
            'TRUCK': 'truck',
            'CARRETA': 'carreta',
            'BITREM': 'bitrem',
            'RODOTREM': 'rodotrem',
            'LS': 'ls'
        }
        tipo_veiculo = tipo_veiculo_map.get(tipo_veiculo_raw, tipo_veiculo_raw.lower())
        
        if not tipo_veiculo or tipo_veiculo not in ['truck', 'carreta', 'bitrem', 'rodotrem', 'vuc', 'toco', 'ls']:
            return {'success': False, 'error': 'Tipo de veículo inválido'}
        
        with transaction.atomic():
            # Buscar motorista
            try:
                motorista = Motorista.objects.get(id=motorista_id)
            except Motorista.DoesNotExist:
                return {'success': False, 'error': 'Motorista não encontrado'}
            
            # Buscar transportadora
            try:
                transportadora = Transportadora.objects.get(id=transportadora_id)
            except Transportadora.DoesNotExist:
                return {'success': False, 'error': 'Transportadora não encontrada'}
            
            # Converter data e hora
            try:
                data_agendada = datetime.strptime(data_agendada_str, '%Y-%m-%d').date()
                # Se for encaixe, usar horário padrão (00:00)
                if is_encaixe:
                    horario_agendado = datetime.strptime('00:00', '%H:%M').time()
                else:
                    horario_agendado = datetime.strptime(horario_agendado_str, '%H:%M').time()
            except ValueError as e:
                return {'success': False, 'error': f'Erro ao converter data/hora: {str(e)}'}
            
            # Gerar ordem única se não fornecida
            if not ordem:
                # Formato: MAN-YYYYMMDD-HHMMSS
                agora = datetime.now()
                ordem = f"MAN-{agora.strftime('%Y%m%d-%H%M%S')}"
            
            # Verificar se ordem já existe
            if Agendamento.objects.filter(ordem=ordem).exists():
                # Se existir, adicionar sufixo numérico
                contador = 1
                ordem_original = ordem
                while Agendamento.objects.filter(ordem=ordem).exists():
                    ordem = f"{ordem_original}-{contador}"
                    contador += 1
            
            # Criar agendamento
            agendamento = Agendamento.objects.create(
                ordem=ordem,
                motorista=motorista,
                data_agendada=data_agendada,
                horario_agendado=horario_agendado,
                tipo=tipo,
                placa_veiculo=placa_veiculo,
                transportadora=transportadora,
                peso=peso,
                tipo_veiculo=tipo_veiculo,
                observacoes=observacoes
            )
            
            # Enviar atualização via WebSocket para a portaria
            try:
                from .websocket_utils import enviar_atualizacao_portaria
                enviar_atualizacao_portaria('created', agendamento=agendamento)
            except Exception as e:
                logger.error(f"Erro ao enviar atualização WebSocket: {str(e)}")
                # Não falhar a criação se a atualização WebSocket falhar
            
            # Notificar grupo de porteiros sobre o agendamento criado (assíncrono)
            try:
                from .mensagens import notificar_agendamentos_criados
                notificar_agendamentos_criados([agendamento.id], 1)
            except Exception as e:
                logger.error(f"Erro ao notificar agendamento criado: {str(e)}")
                # Não falhar a criação se a notificação falhar
            
            # Enviar email com pendências de ondas após criação (assíncrono para não bloquear)
            try:
                import threading
                thread = threading.Thread(target=enviar_email_pendencias_ondas)
                thread.daemon = True
                thread.start()
            except Exception as e:
                logger.error(f"Erro ao iniciar thread de envio de email: {str(e)}")
                # Não falhar a criação se o email falhar
            
            return {
                'success': True,
                'message': 'Agendamento criado com sucesso!',
                'agendamento_id': agendamento.id,
                'ordem': agendamento.ordem
            }
            
    except Exception as e:
        logger.error(f"Erro ao criar agendamento manual: {str(e)}")
        return {
            'success': False,
            'error': f'Erro ao criar agendamento: {str(e)}'
        }


def editar_agendamento_manual(agendamento_id, dados_formulario):
    """
    Edita um agendamento existente a partir dos dados do formulário.
    """
    try:
        from django.db import transaction
        from datetime import datetime
        
        # Buscar agendamento existente
        try:
            agendamento = Agendamento.objects.get(id=agendamento_id)
        except Agendamento.DoesNotExist:
            return {'success': False, 'error': 'Agendamento não encontrado'}
        
        # Extrair dados do formulário
        motorista_id = dados_formulario.get('motorista')
        data_agendada_str = dados_formulario.get('data_agendada', '')
        horario_agendado_str = dados_formulario.get('horario_agendado', '')
        tipo = dados_formulario.get('tipo', '').strip()
        placa_veiculo = dados_formulario.get('placa_veiculo', '').strip().upper()[:8]
        transportadora_id = dados_formulario.get('transportadora')
        peso = dados_formulario.get('peso', 0)
        tipo_veiculo_raw = dados_formulario.get('tipo_veiculo', '').strip().upper()
        observacoes = dados_formulario.get('observacoes', '').strip()
        is_encaixe = dados_formulario.get('encaixe') == 'on' or dados_formulario.get('encaixe') == True
        
        # Validações básicas
        if not motorista_id:
            return {'success': False, 'error': 'Motorista é obrigatório'}
        
        if not data_agendada_str:
            return {'success': False, 'error': 'Data agendada é obrigatória'}
        
        # Se for encaixe, não precisa de horário
        if not is_encaixe and not horario_agendado_str:
            return {'success': False, 'error': 'Horário agendado é obrigatório'}
        
        if not tipo or tipo not in ['coleta', 'entrega']:
            return {'success': False, 'error': 'Tipo inválido'}
        
        if not placa_veiculo:
            return {'success': False, 'error': 'Placa do veículo é obrigatória'}
        
        if not transportadora_id:
            return {'success': False, 'error': 'Transportadora é obrigatória'}
        
        try:
            peso = float(peso)
            if peso <= 0:
                return {'success': False, 'error': 'Peso deve ser maior que zero'}
        except (ValueError, TypeError):
            return {'success': False, 'error': 'Peso inválido'}
        
        # Mapear tipo de veículo (formulário usa maiúsculas, modelo usa minúsculas)
        tipo_veiculo_map = {
            'VUC': 'vuc',
            'TOCO': 'toco',
            'TRUCK': 'truck',
            'CARRETA': 'carreta',
            'BITREM': 'bitrem',
            'RODOTREM': 'rodotrem',
            'LS': 'ls'
        }
        tipo_veiculo = tipo_veiculo_map.get(tipo_veiculo_raw, tipo_veiculo_raw.lower())
        
        if not tipo_veiculo or tipo_veiculo not in ['truck', 'carreta', 'bitrem', 'rodotrem', 'vuc', 'toco', 'ls']:
            return {'success': False, 'error': 'Tipo de veículo inválido'}
        
        with transaction.atomic():
            # Buscar motorista
            try:
                motorista = Motorista.objects.get(id=motorista_id)
            except Motorista.DoesNotExist:
                return {'success': False, 'error': 'Motorista não encontrado'}
            
            # Buscar transportadora
            try:
                transportadora = Transportadora.objects.get(id=transportadora_id)
            except Transportadora.DoesNotExist:
                return {'success': False, 'error': 'Transportadora não encontrada'}
            
            # Converter data e hora
            try:
                data_agendada = datetime.strptime(data_agendada_str, '%Y-%m-%d').date()
                # Se for encaixe, usar horário padrão (00:00)
                if is_encaixe:
                    horario_agendado = datetime.strptime('00:00', '%H:%M').time()
                else:
                    horario_agendado = datetime.strptime(horario_agendado_str, '%H:%M').time()
            except ValueError as e:
                return {'success': False, 'error': f'Erro ao converter data/hora: {str(e)}'}
            
            # Atualizar agendamento
            agendamento.motorista = motorista
            agendamento.data_agendada = data_agendada
            agendamento.horario_agendado = horario_agendado
            agendamento.tipo = tipo
            agendamento.placa_veiculo = placa_veiculo
            agendamento.transportadora = transportadora
            agendamento.peso = peso
            agendamento.tipo_veiculo = tipo_veiculo
            agendamento.observacoes = observacoes
            agendamento.save()
            
            # Enviar atualização via WebSocket para a portaria
            try:
                from .websocket_utils import enviar_atualizacao_portaria
                enviar_atualizacao_portaria('updated', agendamento=agendamento)
            except Exception as e:
                logger.error(f"Erro ao enviar atualização WebSocket: {str(e)}")
                # Não falhar a edição se a atualização WebSocket falhar
            
            return {
                'success': True,
                'message': 'Agendamento atualizado com sucesso!',
                'agendamento_id': agendamento.id,
                'ordem': agendamento.ordem
            }
            
    except Exception as e:
        logger.error(f"Erro ao editar agendamento manual: {str(e)}")
        return {
            'success': False,
            'error': f'Erro ao editar agendamento: {str(e)}'
        }


def enviar_whatsapp_api(numero, mensagem):
    """
    Envia mensagem via WhatsApp usando API configurada nas variáveis de ambiente.
    Suporta múltiplos formatos de API (Evolution API, Whapi.Cloud, SendZapi, etc).
    
    Args:
        numero: Número do telefone (formato: 5511999999999)
        mensagem: Texto da mensagem a ser enviada
    
    Returns:
        dict: {'success': bool, 'message': str, 'error': str}
    """
    try:
        # Obter configurações da API
        api_url = getattr(settings, 'WHATSAPP_API_URL', None)
        api_key = getattr(settings, 'WHATSAPP_API_KEY', None)
        api_instance = getattr(settings, 'WHATSAPP_API_INSTANCE', 'default')
        
        if not api_url or not api_key:
            error_msg = "WhatsApp API não configurada. Verifique as variáveis de ambiente."
            logger.warning(error_msg)
            print(f"[WHATSAPP API] {error_msg}")
            print(f"[WHATSAPP API] URL: {api_url or 'NÃO DEFINIDA'}")
            print(f"[WHATSAPP API] KEY: {'DEFINIDA' if api_key else 'NÃO DEFINIDA'}")
            return {
                'success': False,
                'error': 'API do WhatsApp não configurada'
            }
        
        # Limpar e formatar número (remover espaços, traços, parênteses)
        numero_limpo = numero.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Garantir que o número começa com 55 (código do Brasil)
        if not numero_limpo.startswith('55'):
            if numero_limpo.startswith('0'):
                numero_limpo = '55' + numero_limpo[1:]
            else:
                numero_limpo = '55' + numero_limpo
        
        print(f"[WHATSAPP API] Tentando enviar mensagem para {numero}")
        print(f"[WHATSAPP API] URL: {api_url}")
        print(f"[WHATSAPP API] Número formatado: {numero_limpo}")
        
        # Detectar tipo de API baseado na URL
        api_url_lower = api_url.lower()
        is_whapi = 'whapi' in api_url_lower or 'gate.whapi' in api_url_lower
        
        # Tentar diferentes formatos de API
        resultados = []
        
        TIMEOUT_SECONDS = 5
        
        # Formato 1: Whapi.Cloud (prioridade se detectado)
        if is_whapi:
            try:
                # Whapi.Cloud usa /messages/text com Bearer token
                url = f"{api_url.rstrip('/')}/messages/text"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                payload = {
                    "to": numero_limpo,
                    "body": mensagem
                }
                print(f"[WHATSAPP API] Tentativa 1 - Whapi.Cloud: {url}")
                response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
                print(f"[WHATSAPP API] Resposta Whapi.Cloud: {response.status_code}")
                resultados.append(('Whapi.Cloud', response))
                return {
                    'success': response.status_code in [200, 201],
                    'message': 'Enviado via Whapi',
                    'error': response.text if response.status_code not in [200, 201] else None
                }
            except Exception as e:
                error_msg = f"Tentativa Whapi.Cloud falhou: {e}"
                logger.warning(error_msg)
                print(f"[WHATSAPP API] {error_msg}")
                # Se foi detectado como Whapi e falhou, provavelmente não adianta tentar Evolution
                return {'success': False, 'error': error_msg}
        
        # Formato 2: Evolution API (padrão)
        sucesso_anterior = False
        try:
            url = f"{api_url.rstrip('/')}/message/sendText/{api_instance}"
            headers = {
                'Content-Type': 'application/json',
                'apikey': api_key
            }
            payload = {
                "number": numero_limpo,
                "text": mensagem
            }
            print(f"[WHATSAPP API] Tentativa 2 - Evolution API: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            print(f"[WHATSAPP API] Resposta Evolution API: {response.status_code}")
            resultados.append(('Evolution API', response))
            if response.status_code in [200, 201]:
                sucesso_anterior = True
        except Exception as e:
            error_msg = f"Tentativa Evolution API falhou: {e}"
            logger.warning(error_msg)
            print(f"[WHATSAPP API] {error_msg}")
        
        # Formato 3: Outros serviços (fallback apenas se não for Whapi e Evolution falhar)
        if not sucesso_anterior and not is_whapi:
            # Bearer Token API
            try:
                url = f"{api_url.rstrip('/')}/messages/text"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                payload = {
                    "to": numero_limpo,
                    "body": mensagem
                }
                print(f"[WHATSAPP API] Tentativa 3 - Bearer Token API: {url}")
                response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
                print(f"[WHATSAPP API] Resposta Bearer Token: {response.status_code}")
                resultados.append(('Bearer Token API', response))
                if response.status_code in [200, 201]:
                    sucesso_anterior = True
            except Exception as e:
                logger.warning(f"Tentativa Bearer Token falhou: {e}")
            
            # X-API-Key API (se anterior falhou)
            if not sucesso_anterior:
                 try:
                    url = f"{api_url.rstrip('/')}/send"
                    headers = {
                        'Content-Type': 'application/json',
                        'X-API-Key': api_key
                    }
                    payload = {
                        "phone": numero_limpo,
                        "message": mensagem
                    }
                    response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
                    resultados.append(('X-API-Key API', response))
                    if response.status_code in [200, 201]:
                        sucesso_anterior = True
                 except Exception as e:
                     logger.warning(f"Tentativa X-API-Key falhou: {e}")

        
        # Verificar qual formato funcionou
        for formato, response in resultados:
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    # Verificar diferentes formatos de resposta de sucesso
                    if (result.get('key') or result.get('messageId') or 
                        result.get('success') or result.get('status') == 'sent' or
                        result.get('message') or 'id' in result):
                        logger.info(f"Mensagem WhatsApp enviada com sucesso via {formato} para {numero_limpo}")
                        return {
                            'success': True,
                            'message': 'Mensagem enviada com sucesso'
                        }
                except:
                    # Se não for JSON, mas status 200, considerar sucesso
                    logger.info(f"Mensagem WhatsApp enviada com sucesso via {formato} para {numero_limpo}")
                    return {
                        'success': True,
                        'message': 'Mensagem enviada com sucesso'
                    }
        
        # Se nenhum formato funcionou, retornar o último erro
        if resultados:
            ultimo_response = resultados[-1][1]
            try:
                error_text = ultimo_response.text[:500] if hasattr(ultimo_response, 'text') else str(ultimo_response)
                error_msg = f"Erro HTTP {ultimo_response.status_code}: {error_text}"
                logger.error(f"Erro ao enviar WhatsApp: {error_msg}")
                logger.error(f"URL tentada: {api_url}")
                logger.error(f"Formato usado: {resultados[-1][0]}")
                
                try:
                    error_json = ultimo_response.json()
                    error_detail = (error_json.get('message') or 
                                   error_json.get('error') or 
                                   error_json.get('detail') or 
                                   error_json.get('errorMessage') or
                                   str(error_json))
                    return {
                        'success': False,
                        'error': f'Erro {ultimo_response.status_code}: {error_detail}'
                    }
                except:
                    return {
                        'success': False,
                        'error': f'Erro {ultimo_response.status_code}: {error_text[:200]}'
                    }
            except Exception as e:
                logger.error(f"Erro ao processar resposta: {e}")
                return {
                    'success': False,
                    'error': f'Erro ao processar resposta da API: {str(e)}'
                }
        else:
            logger.error("Nenhuma tentativa de conexão foi bem-sucedida")
            logger.error(f"URL configurada: {api_url}")
            return {
                'success': False,
                'error': 'Não foi possível conectar à API. Verifique a URL e a chave de API no arquivo .env'
            }
            
    except requests.exceptions.RequestException as e:
        error_detail = str(e)
        logger.error(f"Erro de conexão ao enviar WhatsApp: {error_detail}")
        return {
            'success': False,
            'error': f'Erro de conexão: {error_detail}'
        }
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Erro inesperado ao enviar WhatsApp: {error_detail}")
        return {
            'success': False,
            'error': f'Erro inesperado: {error_detail}'
        }


def enviar_email_pendencias_ondas():
    """
    Envia email para o grupo de logística com pendências de liberação (Onda/OD)
    Lista agendamentos que ainda não tiveram a liberação registrada
    """
    try:
        # Buscar agendamentos com pendências de liberação (Onda/OD)
        # Agora inclui Coleta (Onda) e Entrega (OD)
        hoje = timezone_today()
        pendencias = Agendamento.objects.filter(
            data_agendada=hoje,
            onda_liberacao__isnull=True
        ).select_related('motorista', 'transportadora').order_by('tipo', 'horario_agendado')
        
        # Se não houver pendências, não enviar email
        if not pendencias.exists():
            logger.info("Nenhuma pendência de liberação (Onda/OD) encontrada para hoje")
            return
        
        # Buscar grupo de logística
        try:
            grupo_logistica = GrupoUsuario.objects.get(nome='logistica', ativo=True)
        except GrupoUsuario.DoesNotExist:
            logger.warning("Grupo de logística não encontrado")
            return
        
        # Buscar emails dos usuários do grupo que têm configuração de notificação
        # e que querem receber emails (respeitando preferências)
        # Também preparar lista de usuários para notificações push
        emails_destinatarios = []
        usuarios_notificacao = []
        for usuario in grupo_logistica.usuarios.filter(is_active=True):
            try:
                # Verificar se tem configuração de notificação
                try:
                    config = ConfiguracaoNotificacao.objects.get(usuario=usuario)
                except ConfiguracaoNotificacao.DoesNotExist:
                    config = None
                
                # Verificar preferências do usuário
                try:
                    preferencias = PreferenciaNotificacaoUsuario.objects.get(usuario=usuario)
                except PreferenciaNotificacaoUsuario.DoesNotExist:
                    # Se não tem preferências, criar com padrão True (receber)
                    preferencias = PreferenciaNotificacaoUsuario.objects.create(
                        usuario=usuario,
                        receber_email=True,
                        receber_whatsapp=True,
                        receber_navegador=True
                    )
                
                # Adicionar email se configurado e usuário quer receber
                if config and config.email_destinatario and preferencias.receber_email:
                    emails_destinatarios.append(config.email_destinatario)
                
                # Adicionar usuário para notificações push se quiser receber
                if preferencias.receber_navegador and preferencias.push_subscription:
                    usuarios_notificacao.append(usuario)
            except Exception as e:
                logger.error(f"Erro ao processar usuário {usuario.username} para notificações: {e}")
                continue
        
        if not emails_destinatarios:
            logger.warning("Nenhum email configurado para o grupo de logística")
            return
        
        # Criar tabela HTML com as pendências
        tabela_html = """
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-family: Arial, sans-serif;">
            <thead>
                <tr style="background-color: #0ea5e9; color: white;">
                    <th style="padding: 12px; text-align: left; border: 1px solid #0284c7;">Tipo</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #0284c7;">Motorista</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #0284c7;">Data/Horário Agendado</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #0284c7;">Documentos</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for agendamento in pendencias:
            documentos = agendamento.coluna_ad if agendamento.coluna_ad else "—"
            # Limitar tamanho dos documentos para não quebrar o layout
            if len(documentos) > 100:
                documentos = documentos[:100] + "..."
            
            # Combinar data e horário
            data_horario = f"{agendamento.data_agendada.strftime('%d/%m/%Y')} às {agendamento.horario_agendado.strftime('%H:%M')}"
            
            # Label do tipo
            tipo_label = "ONDA" if agendamento.tipo == 'coleta' else "OD"
            bg_color = "#f0f9ff" if agendamento.tipo == 'coleta' else "#fdf2f8" # Azul vs Rosa claro
            
            tabela_html += f"""
                <tr style="border-bottom: 1px solid #e2e8f0; background-color: {bg_color};">
                    <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">{tipo_label}</td>
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">{agendamento.motorista.nome}</td>
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">{data_horario}</td>
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">{documentos}</td>
                </tr>
            """
        
        tabela_html += """
            </tbody>
        </table>
        """
        
        # Criar conteúdo HTML do email
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pendências de Liberação de Onda</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: Arial, sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8fafc; padding: 32px 0;">
                <tr>
                    <td align="center">
                        <table width="640" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                            <!-- Logo -->
                            <tr>
                                <td align="center" style="padding: 40px 24px 16px;">
                                    <img src="https://res.cloudinary.com/dfh2plz7g/image/upload/v1759941217/Transcamila_Logo_Atualizada-removebg-preview_lcbfbt.png" alt="Transcamila Luft Logistics" style="max-width: 220px; height: auto;">
                                </td>
                            </tr>
                            
                            <!-- Cabeçalho -->
                            <tr>
                                <td align="center" style="padding: 0 24px 24px;">
                                    <h1 style="font-size: 24px; color: #1e293b; margin: 0; font-weight: 600;">Pendências de Liberação (Onda/OD)</h1>
                                    <p style="font-size: 14px; color: #64748b; margin: 8px 0 0;">Data: {hoje.strftime('%d/%m/%Y')}</p>
                                </td>
                            </tr>
                            
                            <!-- Conteúdo -->
                            <tr>
                                <td style="padding: 0 24px 24px;">
                                    <p style="font-size: 16px; color: #334155; margin: 0 0 16px;">
                                        Segue abaixo a relação de agendamentos com pendência de liberação (Onda para Coletas e OD para Entregas):
                                    </p>
                                    {tabela_html}
                                    <p style="font-size: 14px; color: #64748b; margin: 20px 0 0;">
                                        Total de pendências: <strong>{pendencias.count()}</strong>
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Rodapé -->
                            <tr>
                                <td align="center" style="padding: 24px; border-top: 1px solid #e2e8f0; background-color: #f8fafc;">
                                    <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                                        TLOGpainel - Transcamila Cargas e Armazéns Gerais LTDA
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Criar versão texto do email
        text_content = f"""
Pendências de Liberação (Onda/OD)
Data: {hoje.strftime('%d/%m/%Y')}

Segue abaixo a relação de agendamentos com pendência de liberação (Onda para Coletas e OD para Entregas):

"""
        for agendamento in pendencias:
            documentos = agendamento.coluna_ad if agendamento.coluna_ad else "—"
            tipo_label = "ONDA" if agendamento.tipo == 'coleta' else "OD"
            text_content += f"""
Tipo: {tipo_label}
Motorista: {agendamento.motorista.nome}
Data: {agendamento.data_agendada.strftime('%d/%m/%Y')}
Horário: {agendamento.horario_agendado.strftime('%H:%M')}
Documentos: {documentos}
---
"""
        text_content += f"\nTotal de pendências: {pendencias.count()}\n\nTLOGpainel - Transcamila Cargas e Armazéns Gerais LTDA"
        
        # Enviar email
        subject = f'Pendências de Liberação (Onda/OD) - {hoje.strftime("%d/%m/%Y")}'
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails_destinatarios,
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        try:
            email.send(fail_silently=False)
            logger.info(f"Email de pendências de ondas enviado para {len(emails_destinatarios)} destinatário(s) - {pendencias.count()} pendência(s)")
        except Exception as email_error:
            logger.error(f"Erro ao enviar email de pendências de ondas: {email_error}")
            # Não re-raise para não quebrar o fluxo da aplicação
        
        # Enviar notificações push para usuários do grupo de logística
        if usuarios_notificacao:
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
                    total_pendencias = pendencias.count()
                    mensagem_push = f"{total_pendencias} pendência(s) de liberação de onda para hoje"
                    titulo_push = "Pendências de Onda"
                    url_push = '/rondonopolis/onda/'
                    tag_push = 'pendencias-onda'
                    
                    for usuario in usuarios_notificacao:
                        try:
                            sucesso = enviar_push_notification(usuario, mensagem_push, titulo_push, url=url_push, tag=tag_push)
                            if sucesso:
                                logger.info(f"Push notification de pendências de onda enviada para {usuario.username}")
                            else:
                                logger.warning(f"Falha ao enviar push notification para {usuario.username}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar push notification para {usuario.username}: {e}")
            except Exception as e:
                logger.error(f"Erro ao enviar push notifications de pendências de ondas: {e}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de pendências de ondas: {str(e)}")
        raise


def enviar_whatsapp_twilio(mensagem, numero_whatsapp):
    """
    Função legada para compatibilidade. Redireciona para enviar_whatsapp_api
    """
    return enviar_whatsapp_api(numero_whatsapp, mensagem)