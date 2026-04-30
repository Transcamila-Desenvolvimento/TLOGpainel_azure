#!/bin/bash

echo "--------------------------------------------------------"
echo "Iniciando processo de build do Django na Azure..."
echo "--------------------------------------------------------"

# Entrar no diretório do projeto (onde o script está localizado)
cd "$(dirname "$0")" || { echo "Não localizou o diretório do script. Abortando."; exit 1; }

# --- GARANTIR PYTHON 3.12 ---
# Se a pasta antenv já existe, vamos verificar se é a versão correta.
# Se não for 3.12, deletamos para criar do zero.
if [ -d "antenv" ]; then
    VENV_VERSION=$(./antenv/bin/python --version 2>&1)
    if [[ $VENV_VERSION != *"3.12"* ]]; then
        echo "Versão antiga detectada ($VENV_VERSION). Limpando antenv..."
        rm -rf antenv
    fi
fi

if [ ! -d "antenv" ]; then
    echo "Criando ambiente virtual com Python 3.12..."
    python3.12 -m venv antenv
fi

echo "Ativando ambiente virtual..."
source antenv/bin/activate

# Verificar versão para o log da Azure
python --version
# ----------------------------

export USE_MYSQL=${USE_MYSQL:-True}
export DEBUG=${DEBUG:-False}

echo "Atualizando pip..."
python -m pip install --upgrade pip

# NOTA DE OTIMIZAÇÃO PARA AZURE:
# Idealmente, a instalação de pacotes e o collectstatic devem ser feitos durante o Deploy (GitHub Actions ou ZipDeploy via Oryx),
# pois fazer isso no startup.sh a cada vez que o container reinicia pode causar Timeouts (Erro 502) por demorar mais de 230 segundos.
# Se você tiver lentidão no boot da aplicação, mude o processo de deploy e remova as próximas duas linhas:
echo "Instalando dependências..."
python -m pip install -r requirements.txt

echo "Coletando staticfiles..."
python manage.py collectstatic --noinput

echo "Rodando migrações..."
python manage.py migrate --noinput

export PORT=${PORT:-8000}

echo "Iniciando Daphne na porta $PORT..."
# O comando daphne agora será chamado a partir do venv ativo
daphne -b 0.0.0.0 -p $PORT painel.asgi:application
