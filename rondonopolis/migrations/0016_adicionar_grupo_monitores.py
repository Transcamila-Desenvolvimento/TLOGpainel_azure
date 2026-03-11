# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rondonopolis', '0015_adicionar_liberacao_documentos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grupousuario',
            name='nome',
            field=models.CharField(choices=[('portaria', 'Portaria'), ('checklist', 'CheckList'), ('armazem', 'Armazém'), ('administracao', 'Administração'), ('logistica', 'Logística'), ('liberacao_documentos', 'Documentos'), ('monitores', 'Monitores')], max_length=20, unique=True),
        ),
    ]




