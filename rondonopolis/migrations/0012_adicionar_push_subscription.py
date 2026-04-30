# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rondonopolis', '0011_tornar_email_opcional'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferencianotificacaousuario',
            name='push_subscription',
            field=models.TextField(blank=True, help_text='Subscription JSON para Web Push Notifications', null=True),
        ),
    ]







