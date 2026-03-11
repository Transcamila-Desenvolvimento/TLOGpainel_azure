#!/bin/bash
# startup.sh - Azure App Service Startup Script para rodar Daphne (ASGI) suportando Channels

echo "--------------------------------------------------------"
echo "Iniciando processo de build do Django na Azure..."
echo "--------------------------------------------------------"

# Entrar no diretório do projeto
cd /home/site/wwwroot || { echo "Não localizou wwwroot. Abortando."; exit 1; }

# Garantir que as variáveis do sistema estão ativadas (o App Service carrega isso)
export USE_MYSQL=${USE_MYSQL:-True}
export DEBUG=${DEBUG:-False}

# 1. Instalar pacotes ausentes, se necessário (isso é usual no Oryx se algo faltar, 
# mas em teoria já vai instalar via requirements.txt, deixamos como backup útil)
echo "Instalando daphne, gunicorn, whitenoise se faltarem..."
pip install -r requirements.txt || echo "Falhou em instalar requirements, continuando..."

# 2. Coletar arquivos estáticos
echo "Coletando staticfiles..."
python manage.py collectstatic --noinput

# 3. Rodar migrações do banco de dados MySQL
echo "Rodando migrações..."
python manage.py migrate --noinput

# 4. Iniciar o servidor com Daphne (porta dinamicamente por WEBSITES_PORT, que no linux App Service é PORT, por padrão $PORT ou 8000)
# Vamos exportar PORT caso não exista
export PORT=${PORT:-8000}

echo "Iniciando Daphne na porta $PORT..."
daphne -b 0.0.0.0 -p $PORT painel.asgi:application
