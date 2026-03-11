"""
Script para migrar dados do SQLite para MySQL
Execute este script APENAS UMA VEZ após configurar o MySQL

USO:
1. Configure o MySQL no settings.py
2. Execute: python migrar_sqlite_para_mysql.py
"""

import os
import sys
import django
from pathlib import Path

# Configurar o Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'painel.settings')
django.setup()

from django.db import connections
from django.core.management import call_command
import sqlite3

def migrar_dados():
    """
    Migra dados do SQLite para MySQL
    """
    print("=" * 60)
    print("MIGRAÇÃO DE SQLITE PARA MYSQL")
    print("=" * 60)
    
    # Caminho do banco SQLite
    sqlite_db = BASE_DIR / 'db.sqlite3'
    
    if not sqlite_db.exists():
        print(f"ERRO: Arquivo {sqlite_db} não encontrado!")
        return False
    
    print(f"\n1. Conectando ao SQLite: {sqlite_db}")
    sqlite_conn = sqlite3.connect(str(sqlite_db))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Conectar ao MySQL
    print("2. Conectando ao MySQL...")
    mysql_conn = connections['default']
    
    try:
        # Verificar se o MySQL está configurado
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("   ✓ Conexão com MySQL estabelecida")
    except Exception as e:
        print(f"   ✗ ERRO ao conectar ao MySQL: {e}")
        print("\n   Verifique as configurações no settings.py e arquivo .env")
        return False
    
    # Obter lista de tabelas do SQLite
    print("\n3. Obtendo lista de tabelas do SQLite...")
    sqlite_cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tabelas = [row[0] for row in sqlite_cursor.fetchall()]
    print(f"   Encontradas {len(tabelas)} tabelas: {', '.join(tabelas)}")
    
    # Verificar se o MySQL já tem dados
    print("\n4. Verificando se o MySQL já contém dados...")
    with mysql_conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        mysql_tables = [row[0] for row in cursor.fetchall()]
        
        if mysql_tables:
            resposta = input(f"   ⚠️  O MySQL já contém {len(mysql_tables)} tabelas. Continuar? (s/N): ")
            if resposta.lower() != 's':
                print("   Migração cancelada pelo usuário.")
                return False
    
    print("\n5. Criando estrutura do banco no MySQL...")
    print("   Executando migrations...")
    try:
        call_command('migrate', verbosity=0)
        print("   ✓ Estrutura criada com sucesso")
    except Exception as e:
        print(f"   ✗ ERRO ao criar estrutura: {e}")
        return False
    
    # Migrar dados de cada tabela
    print("\n6. Migrando dados...")
    total_registros = 0
    
    for tabela in tabelas:
        try:
            # Obter dados do SQLite
            sqlite_cursor.execute(f"SELECT * FROM {tabela}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"   - {tabela}: 0 registros (pulando)")
                continue
            
            # Obter nomes das colunas
            colunas = [description[0] for description in sqlite_cursor.description]
            
            # Preparar query de inserção
            placeholders = ', '.join(['%s'] * len(colunas))
            colunas_str = ', '.join([f"`{col}`" for col in colunas])
            insert_query = f"INSERT INTO `{tabela}` ({colunas_str}) VALUES ({placeholders})"
            
            # Inserir dados no MySQL
            with mysql_conn.cursor() as cursor:
                # Desabilitar foreign key checks temporariamente
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                
                # Limpar tabela antes de inserir (opcional, mas recomendado)
                cursor.execute(f"TRUNCATE TABLE `{tabela}`")
                
                # Inserir registros
                valores = []
                for row in rows:
                    valores.append(tuple(row))
                
                cursor.executemany(insert_query, valores)
                mysql_conn.commit()
                
                # Reabilitar foreign key checks
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            print(f"   ✓ {tabela}: {len(rows)} registros migrados")
            total_registros += len(rows)
            
        except Exception as e:
            print(f"   ✗ ERRO ao migrar {tabela}: {e}")
            # Continuar com outras tabelas
            continue
    
    sqlite_conn.close()
    
    print("\n" + "=" * 60)
    print(f"MIGRAÇÃO CONCLUÍDA!")
    print(f"Total de registros migrados: {total_registros}")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        migrar_dados()
    except KeyboardInterrupt:
        print("\n\nMigração cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\nERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()

