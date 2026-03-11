from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from datetime import datetime


class Motorista(models.Model):
    nome = models.CharField(max_length=100, db_index=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.telefone})"

    class Meta:
        verbose_name = 'Motorista'
        verbose_name_plural = 'Motoristas'
        indexes = [
            models.Index(fields=['nome']),
        ]


class Transportadora(models.Model):
    nome = models.CharField(max_length=100)
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Transportadora'
        verbose_name_plural = 'Transportadoras'


class Agendamento(models.Model):
    # ==================== CHOICES ====================
    TIPO_CHOICES = [
        ('coleta', 'Coleta'),
        ('entrega', 'Entrega'),
    ]

    TIPO_VEICULO_CHOICES = [
        ('truck', 'Truck'), ('carreta', 'Carreta'), ('bitrem', 'Bitrem'),
        ('rodotrem', 'Rodotrem'), ('vuc', 'VUC'), ('toco', 'Toco'), ('ls', 'LS'),
    ]

    STATUS_GERAL_CHOICES = [
        ('aguardando_chegada', 'Aguardando Chegada'),
        ('em_checklist', 'Em CheckList'),
        ('confirmacao_armazem', 'Confirmação Armazém'),
        ('em_operacao_armazem', 'Em Operação no Armazém'),
        ('pendente_liberacao_onda', 'Pendente de Liberação Onda'),
        ('pendente_liberacao_documentos', 'Pendente Liberação Documentos'),
        ('processo_concluido', 'Processo Concluído'),
    ]

    ONDA_STATUS_CHOICES = [
        ('aguardando', 'AGUARDANDO'),
        ('liberado', 'LIBERADO'),
    ]

    # ==================== DADOS DA IMPORTAÇÃO ====================
    ordem = models.CharField("Ordem/Nº Importação", max_length=50, unique=True, db_index=True)
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name='agendamentos')
    data_agendada = models.DateField("Data Agendada")
    horario_agendado = models.TimeField("Horário Agendado")
    tipo = models.CharField("Tipo Operação", max_length=10, choices=TIPO_CHOICES)
    placa_veiculo = models.CharField("Placa do Veículo", max_length=8, db_index=True)
    transportadora = models.ForeignKey(Transportadora, on_delete=models.PROTECT, related_name='agendamentos')
    peso = models.DecimalField("Peso (kg)", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tipo_veiculo = models.CharField("Tipo de Veículo", max_length=20, choices=TIPO_VEICULO_CHOICES)
    observacoes = models.TextField("Observações Gerais", blank=True)
    coluna_ad = models.TextField("Coluna AD", blank=True, null=True)

    # ==================== STATUS GERAL ====================
    status_geral = models.CharField(
        max_length=30,
        choices=STATUS_GERAL_CHOICES,
        default='aguardando_chegada',
        db_index=True,
        verbose_name="Status Geral"
    )

    # ==================== PORTARIA ====================
    portaria_liberacao = models.DateTimeField("Portaria - Data/Hora da Liberação", blank=True, null=True)
    portaria_liberado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='liberacoes_portaria'
    )
    portaria_chegada_armazem = models.DateTimeField("Portaria - Confirmou Chegada Armazém", blank=True, null=True)
    portaria_chegada_armazem_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmacoes_chegada_armazem_portaria'
    )

    # ==================== CHECKLIST ====================
    checklist_numero = models.CharField("Nº do CheckList", max_length=50, blank=True, null=True)
    checklist_data = models.DateTimeField("CheckList - Data/Hora do Preenchimento", blank=True, null=True)
    checklist_preenchido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='checklists_preenchidos'
    )
    checklist_observacao = models.TextField(blank=True, null=True)

    # ==================== ARMAZÉM ====================
    armazem_chegada = models.DateTimeField("Armazém - Data/Hora da Chegada", blank=True, null=True)
    armazem_confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmacoes_armazem'
    )
    armazem_saida = models.DateTimeField("Armazém - Data/Hora da Saída", blank=True, null=True)
    armazem_saida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='saidas_armazem'
    )
    armazem_saida_observacao = models.TextField("Armazém - Observação Saída", blank=True, null=True)

    # ==================== ONDA ====================
    onda_status = models.CharField(max_length=20, choices=ONDA_STATUS_CHOICES, default='aguardando')
    onda_liberacao = models.DateTimeField("Onda - Data/Hora da Liberação", blank=True, null=True)
    onda_liberado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='liberacoes_onda'
    )

    # ==================== DOCUMENTOS ====================
    documentos_liberacao = models.DateTimeField("Documentos - Data/Hora da Liberação", blank=True, null=True)
    documentos_liberado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='liberacoes_documentos'
    )
    documentos_observacao = models.TextField("Documentos - Observação Liberação", blank=True, null=True)

    # ==================== CONTROLE E AUDITORIA ====================
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='agendamentos_criados'
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ordem} - {self.motorista.nome} ({self.placa_veiculo})"

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['-data_agendada', 'horario_agendado']
        indexes = [
            models.Index(fields=['ordem']),
            models.Index(fields=['status_geral']),
            models.Index(fields=['data_agendada']),
            models.Index(fields=['placa_veiculo']),
        ]

    # ==================== MÉTODO PARA ATUALIZAR STATUS GERAL ====================
    def atualizar_status_geral(self, usuario=None):
        """
        Atualiza automaticamente o status_geral com base nas etapas concluídas.
        
        Fluxo COLETA: Portaria -> CheckList -> Onda -> Armazém (Entrada/Saída) -> Documentos
        Fluxo ENTREGA: Portaria -> Armazém (Entrada/Saída) -> Documentos (Pula CheckList e Onda)
        """
        is_entrega = (self.tipo == 'entrega')
        
        # 1. Processo Concluído (Comum a ambos)
        # Se documentos liberados, acabou
        if self.documentos_liberacao:
             # Para ter chegado aqui, deve ter passado na SAÍDA do armazém
            if self.armazem_saida:
                novo_status = 'processo_concluido'
            else:
                # Caso inconsistente, mas mantém lógica anterior
                novo_status = 'processo_concluido'
                
        # 2. Pendente Documentos (Comum a ambos - já SAIU do armazém)
        elif self.armazem_saida and not self.documentos_liberacao:
            novo_status = 'pendente_liberacao_documentos'

        # 3. Em Operação no Armazém (Já entrou mas não saiu)
        elif self.armazem_chegada and not self.armazem_saida:
            novo_status = 'em_operacao_armazem'

        # 4. Lógica específica por tipo antes do Armazém
        elif is_entrega:
            # Fluxo ENTREGA: Portaria -> OD (Onda) -> Armazém
            
            # Se já passou na portaria e a OD/Onda foi liberada
            if self.portaria_liberacao and self.onda_liberacao:
                novo_status = 'confirmacao_armazem'
            # Se passou na portaria mas a OD está pendente
            elif self.portaria_liberacao:
                novo_status = 'pendente_liberacao_onda'
            else:
                novo_status = 'aguardando_chegada'
                
        else:
            # Fluxo COLETA (Padrão): Portaria -> CheckList -> Onda -> Armazém
            
            # Armazém confirmado mas onda não liberada (não deveria acontecer, mas mantém)
            if self.armazem_chegada and not self.onda_liberacao:
                novo_status = 'pendente_liberacao_onda'
                
            # CheckList feito E onda liberada E armazém NÃO confirmado → aguardando confirmação no armazém
            elif self.checklist_data and self.onda_liberacao and not self.armazem_chegada:
                novo_status = 'confirmacao_armazem'
                
            # CheckList feito mas onda não liberada → pendente liberação de onda
            elif self.checklist_data and not self.onda_liberacao:
                novo_status = 'pendente_liberacao_onda'
                
            # CheckList feito (status transitório)
            elif self.checklist_data:
                novo_status = 'pendente_liberacao_onda' # Assumindo que precisa de onda
                
            # Portaria liberada (próximo passo é checklist)
            elif self.portaria_liberacao:
                novo_status = 'em_checklist'
                
            # Ainda não passou pela portaria
            else:
                novo_status = 'aguardando_chegada'

        if self.status_geral != novo_status:
            self.status_geral = novo_status
            self.save(update_fields=['status_geral', 'atualizado_em'])

    # ==================== SAVE SOBRESCRITO PARA REGISTRAR CRIADOR ====================
    def save(self, *args, **kwargs):
        # Registra quem criou (só na criação)
        if not self.pk and not self.criado_por:
            # O usuário geralmente vem do request (será setado na view)
            pass  # será preenchido na view com request.user

        super().save(*args, **kwargs)


# ==================== GRUPOS DE USUÁRIOS ====================
class GrupoUsuario(models.Model):
    """
    Grupos de usuários para Rondonópolis
    Não altera a tabela UserProfile, apenas cria relacionamento ManyToMany
    """
    NOME_CHOICES = [
        ('portaria', 'Portaria'),
        ('checklist', 'CheckList'),
        ('armazem', 'Armazém'),
        ('administracao', 'Administração'),
        ('logistica', 'Logística'),
        ('liberacao_documentos', 'Documentos'),
        ('monitores', 'Monitores'),
    ]
    
    nome = models.CharField(max_length=20, choices=NOME_CHOICES, unique=True)
    descricao = models.CharField(max_length=200, blank=True)
    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='grupos_rondonopolis',
        blank=True
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.get_nome_display()
    
    class Meta:
        verbose_name = 'Grupo de Usuário'
        verbose_name_plural = 'Grupos de Usuários'
        ordering = ['nome']


class GrupoAba(models.Model):
    """
    Configuração de quais abas cada grupo pode ver
    """
    ABA_CHOICES = [
        ('portaria', 'Portaria'),
        ('checklist', 'CheckList'),
        ('armazem', 'Armazém'),
        ('onda', 'Liberação de Onda'),
        ('liberacao_documentos', 'Documentos'),
        ('agendamentos', 'Agendamentos'),
        ('processos', 'Processos'),
        ('dashboard', 'Dashboard'),
        ('painel', 'Painel'),
    ]
    
    grupo = models.ForeignKey(GrupoUsuario, on_delete=models.CASCADE, related_name='abas')
    aba = models.CharField(max_length=20, choices=ABA_CHOICES)
    ativa = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição no menu")
    
    class Meta:
        verbose_name = 'Aba do Grupo'
        verbose_name_plural = 'Abas dos Grupos'
        unique_together = ['grupo', 'aba']
        ordering = ['grupo', 'ordem', 'aba']
    
    def __str__(self):
        return f"{self.grupo.get_nome_display()} - {self.get_aba_display()}"


# ==================== CONFIGURAÇÃO DE NOTIFICAÇÕES ====================
class ConfiguracaoNotificacao(models.Model):
    """
    Configuração de notificações por usuário
    Administrador configura email e WhatsApp para cada usuário
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configuracao_notificacao',
        help_text="Usuário que receberá as notificações"
    )
    email_destinatario = models.EmailField(
        blank=True,
        null=True,
        help_text="Email para receber notificações"
    )
    whatsapp_destinatario = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Número WhatsApp (formato: 5511999999999) - configurado pelo administrador"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração de Notificação'
        verbose_name_plural = 'Configurações de Notificações'
        ordering = ['usuario__username']
    
    def __str__(self):
        if self.usuario:
            return f"Notificações - {self.usuario.get_full_name() or self.usuario.username}"
        return f"Notificações - {self.email_destinatario}"


class PreferenciaNotificacaoUsuario(models.Model):
    """
    Preferências de notificação do usuário
    O usuário pode ativar/desativar tipos de notificação, mas não pode alterar email/whatsapp
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencias_notificacao',
        help_text="Usuário que configura suas preferências"
    )
    receber_email = models.BooleanField(
        default=True,
        help_text="Receber notificações por email"
    )
    receber_whatsapp = models.BooleanField(
        default=True,
        help_text="Receber notificações por WhatsApp"
    )
    receber_navegador = models.BooleanField(
        default=True,
        help_text="Receber notificações do navegador"
    )
    push_subscription = models.TextField(
        blank=True,
        null=True,
        help_text="Subscription JSON para Web Push Notifications"
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Preferência de Notificação'
        verbose_name_plural = 'Preferências de Notificações'
    
    def __str__(self):
        return f"Preferências - {self.usuario.get_full_name() or self.usuario.username}"


class NotificacaoProcesso(models.Model):
    """
    Histórico de notificações enviadas para cada processo
    Armazena o email completo com todas as etapas
    """
    TIPO_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('navegador', 'Notificação Navegador'),
    ]
    
    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    destinatario = models.CharField(max_length=255, help_text="Email ou número WhatsApp")
    assunto = models.CharField(max_length=255, blank=True)
    mensagem = models.TextField(help_text="Conteúdo da notificação")
    enviado_com_sucesso = models.BooleanField(default=False)
    erro = models.TextField(blank=True, null=True)
    enviado_em = models.DateTimeField(auto_now_add=True)
    etapa_quando_enviado = models.CharField(max_length=30, help_text="Etapa do processo quando foi enviado")
    
    class Meta:
        verbose_name = 'Notificação de Processo'
        verbose_name_plural = 'Notificações de Processos'
        ordering = ['-enviado_em']
        indexes = [
            models.Index(fields=['agendamento', 'tipo']),
            models.Index(fields=['enviado_em']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.agendamento.ordem} - {self.enviado_em.strftime('%d/%m/%Y %H:%M')}"


class ControleAtualizacao(models.Model):
    """
    Modelo tecnico para controlar atualizacoes em tempo real (Long Polling Inteligente).
    Substitui o cache de memoria para garantir funcionamento no PythonAnywhere (multi-worker).
    """
    TELA_CHOICES = [
        ('portaria', 'Portaria'),
        ('checklist', 'CheckList'),
        ('onda', 'Liberacao de Onda'),
        ('armazem', 'Armazem'),
        ('armazem', 'Armazem'),
        ('liberacao-documentos', 'Documentos'),
        ('liberacao_documentos', 'Documentos (Legacy)'),
        ('agendamentos', 'Agendamentos (Lista)'),
        ('dashboard', 'Dashboard'),
        ('painel', 'Painel TV'),
    ]

    tela = models.CharField(max_length=50, choices=TELA_CHOICES, unique=True, db_index=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Controle de Atualizacao'
        verbose_name_plural = 'Controle de Atualizacoes'

    def __str__(self):
        return f"{self.tela} - {self.ultima_atualizacao}"