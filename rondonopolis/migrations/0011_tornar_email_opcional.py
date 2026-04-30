# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rondonopolis', '0010_alterar_configuracao_notificacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracaonotificacao',
            name='email_destinatario',
            field=models.EmailField(blank=True, help_text='Email para receber notificações', max_length=254, null=True),
        ),
    ]







