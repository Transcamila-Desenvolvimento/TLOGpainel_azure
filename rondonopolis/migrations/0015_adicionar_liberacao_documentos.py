# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('rondonopolis', '0014_adicionar_grupo_logistica'),
    ]

    operations = [
        # Adicionar campos de Liberação dos Documentos no Agendamento
        migrations.AddField(
            model_name='agendamento',
            name='documentos_liberacao',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Documentos - Data/Hora da Liberação'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='documentos_liberado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='liberacoes_documentos',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Adicionar novo status no STATUS_GERAL_CHOICES
        migrations.AlterField(
            model_name='agendamento',
            name='status_geral',
            field=models.CharField(
                choices=[
                    ('aguardando_chegada', 'Aguardando Chegada'),
                    ('em_checklist', 'Em CheckList'),
                    ('confirmacao_armazem', 'Confirmação Armazém'),
                    ('pendente_liberacao_onda', 'Pendente de Liberação Onda'),
                    ('pendente_liberacao_documentos', 'Pendente Liberação Documentos'),
                    ('processo_concluido', 'Processo Concluído'),
                ],
                db_index=True,
                default='aguardando_chegada',
                max_length=30,
                verbose_name='Status Geral'
            ),
        ),
        # Adicionar novo grupo de usuários
        migrations.AlterField(
            model_name='grupousuario',
            name='nome',
            field=models.CharField(
                choices=[
                    ('portaria', 'Portaria'),
                    ('checklist', 'CheckList'),
                    ('armazem', 'Armazém'),
                    ('administracao', 'Administração'),
                    ('logistica', 'Logística'),
                    ('liberacao_documentos', 'Liberação dos Documentos'),
                ],
                max_length=20,
                unique=True
            ),
        ),
        # Adicionar nova aba no GrupoAba
        migrations.AlterField(
            model_name='grupoaba',
            name='aba',
            field=models.CharField(
                choices=[
                    ('portaria', 'Portaria'),
                    ('checklist', 'CheckList'),
                    ('armazem', 'Armazém'),
                    ('onda', 'Liberação de Onda'),
                    ('liberacao_documentos', 'Liberação dos Documentos'),
                    ('agendamentos', 'Agendamentos'),
                    ('processos', 'Processos'),
                    ('dashboard', 'Dashboard'),
                    ('painel', 'Painel'),
                ],
                max_length=20
            ),
        ),
    ]

