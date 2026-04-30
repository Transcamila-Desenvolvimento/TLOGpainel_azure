# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rondonopolis', '0012_adicionar_push_subscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamento',
            name='coluna_ad',
            field=models.TextField(blank=True, null=True, verbose_name='Coluna AD'),
        ),
    ]

