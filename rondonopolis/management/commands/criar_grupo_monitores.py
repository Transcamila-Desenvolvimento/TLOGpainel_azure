from django.core.management.base import BaseCommand
from rondonopolis.models import GrupoUsuario


class Command(BaseCommand):
    help = 'Cria o grupo Monitores se não existir'

    def handle(self, *args, **options):
        grupo, created = GrupoUsuario.objects.get_or_create(
            nome='monitores',
            defaults={
                'descricao': 'Grupo de monitores com acesso ao painel de movimentações',
                'ativo': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Grupo "Monitores" criado com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Grupo "Monitores" já existe.')
            )
            
            # Ativar o grupo se estiver inativo
            if not grupo.ativo:
                grupo.ativo = True
                grupo.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Grupo "Monitores" foi ativado.')
                )




