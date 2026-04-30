"""
Comando Django para testar a configuração da API do WhatsApp
Uso: python manage.py test_whatsapp_api
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
from dotenv import load_dotenv

class Command(BaseCommand):
    help = 'Testa a configuração da API do WhatsApp'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Teste de Configuração WhatsApp API ===\n'))
        
        # Verificar se o arquivo .env existe
        env_path = os.path.join(settings.BASE_DIR, '.env')
        if os.path.exists(env_path):
            self.stdout.write(self.style.SUCCESS(f'✓ Arquivo .env encontrado: {env_path}'))
            load_dotenv(env_path)
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Arquivo .env NÃO encontrado em: {env_path}'))
            self.stdout.write(self.style.WARNING('  Tentando carregar variáveis do sistema...'))
            load_dotenv()
        
        # Verificar variáveis
        api_url = os.getenv('WHATSAPP_API_URL', '')
        api_key = os.getenv('WHATSAPP_API_KEY', '')
        api_instance = os.getenv('WHATSAPP_API_INSTANCE', 'default')
        
        self.stdout.write('\n--- Variáveis de Ambiente ---')
        self.stdout.write(f'WHATSAPP_API_URL: {api_url if api_url else self.style.ERROR("NÃO DEFINIDA")}')
        self.stdout.write(f'WHATSAPP_API_KEY: {"***" + api_key[-4:] if api_key else self.style.ERROR("NÃO DEFINIDA")}')
        self.stdout.write(f'WHATSAPP_API_INSTANCE: {api_instance}')
        
        # Verificar settings
        self.stdout.write('\n--- Configurações no Django Settings ---')
        settings_url = getattr(settings, 'WHATSAPP_API_URL', None)
        settings_key = getattr(settings, 'WHATSAPP_API_KEY', None)
        settings_instance = getattr(settings, 'WHATSAPP_API_INSTANCE', 'default')
        
        self.stdout.write(f'WHATSAPP_API_URL: {settings_url if settings_url else self.style.ERROR("NÃO DEFINIDA")}')
        self.stdout.write(f'WHATSAPP_API_KEY: {"***" + settings_key[-4:] if settings_key else self.style.ERROR("NÃO DEFINIDA")}')
        self.stdout.write(f'WHATSAPP_API_INSTANCE: {settings_instance}')
        
        # Diagnóstico
        self.stdout.write('\n--- Diagnóstico ---')
        if not api_url:
            self.stdout.write(self.style.ERROR('✗ WHATSAPP_API_URL não está definida'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ WHATSAPP_API_URL: {api_url}'))
        
        if not api_key:
            self.stdout.write(self.style.ERROR('✗ WHATSAPP_API_KEY não está definida'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ WHATSAPP_API_KEY: Definida ({len(api_key)} caracteres)'))
        
        if api_url and api_key:
            self.stdout.write(self.style.SUCCESS('\n✓ Configuração básica OK!'))
            self.stdout.write('\nPróximos passos:')
            self.stdout.write('1. Verifique se a URL da API está correta')
            self.stdout.write('2. Verifique se o token/chave está correto')
            self.stdout.write('3. Teste enviando uma mensagem pelo sistema')
        else:
            self.stdout.write(self.style.ERROR('\n✗ Configuração incompleta!'))
            self.stdout.write('\nPara corrigir:')
            self.stdout.write('1. Crie um arquivo .env na raiz do projeto')
            self.stdout.write('2. Adicione as variáveis:')
            self.stdout.write('   WHATSAPP_API_URL=sua_url_aqui')
            self.stdout.write('   WHATSAPP_API_KEY=seu_token_aqui')
            self.stdout.write('   WHATSAPP_API_INSTANCE=default')
            self.stdout.write('3. Reinicie o servidor Django')
        
        self.stdout.write('\n')



