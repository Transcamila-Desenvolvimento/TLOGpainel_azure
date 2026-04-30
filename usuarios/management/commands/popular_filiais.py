# usuarios/management/commands/popular_filiais.py
from django.core.management.base import BaseCommand
from usuarios.models import Filial

class Command(BaseCommand):
    help = 'Popula as filiais iniciais do sistema'

    def handle(self, *args, **options):
        filiais_data = [
            {
                'nome': 'Ibiporã',
                'codigo': 'ibipora',
                'app_django': 'core',
                'url_inicial': '/',
                'ativa': True
            },
            {
                'nome': 'Paranaguá', 
                'codigo': 'paranagua',
                'app_django': 'paranagua',
                'url_inicial': '/paranagua/',
                'ativa': True
            },
            {
                'nome': 'Rondonópolis',
                'codigo': 'rondonopolis', 
                'app_django': 'rondonopolis',
                'url_inicial': '/rondonopolis/',
                'ativa': True
            }
        ]
        
        for data in filiais_data:
            filial, created = Filial.objects.get_or_create(
                codigo=data['codigo'],
                defaults=data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Filial {filial.nome} criada com sucesso!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Filial {filial.nome} já existe')
                )