import sqlite3
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./database.db")

def get_connection(db_path):
    """Retorna conexão com o banco de dados"""
    conn = sqlite3.connect(db_path)
    return conn

def create_database(db_path):
    """Cria tabela de setores"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Criar tabela de setores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS setores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        responsavel TEXT,
        email TEXT
    )
    """)
    
    # Criar tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setor_id INTEGER,
        nome TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        FOREIGN KEY (setor_id) REFERENCES setores(id)
    )
    """)
    
    # Criar tabela de avisos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setor_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT NOT NULL,
        dia_da_semana TEXT NOT NULL,
        data_criacao TEXT NOT NULL,
        horario TEXT,
        FOREIGN KEY (setor_id) REFERENCES setores(id)
    )
    """)
    
    # Criar tabela de permissões de edição
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aviso_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        permissao_editar INTEGER DEFAULT 0,
        FOREIGN KEY (aviso_id) REFERENCES avisos(id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    """)
    
    conn.commit()
    conn.close()
    
    # Inserção de setores de exemplo
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Setores exemplo
    setores = [
        ('Humanos', 'RH', 'rh@institucional.edu.br'),
        ('Financeiro', 'Contabilidade', 'financeiro@institucional.edu.br'),
        ('Secretaria', 'Administração', 'admin@institucional.edu.br'),
        ('Tecnologia', 'TI', 'ti@institucional.edu.br'),
        ('Serviços', 'Logística', 'servicos@institucional.edu.br')
    ]
    
    cursor.executemany("""
    INSERT OR IGNORE INTO setores (nome, responsavel, email) VALUES (?, ?, ?)
    """, setores)
    
    # Usuários de exemplo
    usuarios = [
        (1, 'Admin', 'admin', 'admin123', 'admin@institucional.edu.br'),
        (1, 'Maria', 'maria_rh', 'maria123', 'maria@institucional.edu.br'),
        (2, 'João', 'joao_fin', 'joao456', 'joao@institucional.edu.br'),
        (3, 'Ana', 'ana_sec', 'ana789', 'ana@institucional.edu.br'),
        (4, 'Carlos', 'carlos_ti', 'carlos123', 'carlos@institucional.edu.br'),
        (5, 'Lucia', 'lucia_serv', 'lucia456', 'lucia@institucional.edu.br')
    ]
    
    import bcrypt
    for sector_id, nome, username, password, email in usuarios:
        hash_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("""
        INSERT OR IGNORE INTO usuarios (setor_id, nome, username, password_hash, email) 
        VALUES (?, ?, ?, ?, ?)
        """, (sector_id, nome, username, hash_password.decode('utf-8'), email))
    
    conn.commit()
    conn.close()

# Função de hash de senha
def hash_password(password):
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
