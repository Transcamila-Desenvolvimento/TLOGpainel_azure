from django.core.management.base import BaseCommand
from rondonopolis.models import Motorista, Transportadora


class Command(BaseCommand):
    help = 'Atualiza todos os nomes de motoristas e transportadoras para maiúsculas'

    def handle(self, *args, **options):
        # Atualizar motoristas
        motoristas_atualizados = 0
        for motorista in Motorista.objects.all():
            nome_antigo = motorista.nome
            motorista.nome = motorista.nome.strip().upper()
            if nome_antigo != motorista.nome:
                motorista.save()
                motoristas_atualizados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Motorista atualizado: {nome_antigo} -> {motorista.nome}')
                )
        
        # Atualizar transportadoras
        transportadoras_atualizadas = 0
        for transportadora in Transportadora.objects.all():
            nome_antigo = transportadora.nome
            transportadora.nome = transportadora.nome.strip().upper()
            if nome_antigo != transportadora.nome:
                transportadora.save()
                transportadoras_atualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Transportadora atualizada: {nome_antigo} -> {transportadora.nome}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Concluído! {motoristas_atualizados} motorista(s) e {transportadoras_atualizadas} transportadora(s) atualizado(s).'
            )
        )



