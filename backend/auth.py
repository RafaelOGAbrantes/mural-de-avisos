import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./database.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_auth_data(conn):
    """Retorna objeto de autenticação"""
    return AuthManager(conn)

class AuthManager:
    def __init__(self, conn):
        self.conn = conn
    
    def login(self, username, password):
        """Realiza login do usuário"""
        cursor = self.conn.cursor()
        
        # Buscar usuário
        cursor.execute("""
        SELECT u.id, u.username, u.nome, s.nome as setor 
        FROM usuarios u
        JOIN setores s ON u.setor_id = s.id
        WHERE u.username = ?
        """, (username,))
        
        user = cursor.fetchone()
        
        if user:
            cursor.execute("SELECT id, nome, username FROM usuarios WHERE id = ?", (user[0],))
            user = cursor.fetchone()
            
            import bcrypt
            password_check = bcrypt.checkpw(
                password.encode('utf-8'),
                bytes.fromhex(user[3]) if isinstance(user[3], str) else user[3]
            )
            
            if password_check:
                return True
            else:
                return False
        else:
            return False
    
    def get_user(self, username):
        """Busca dados do usuário por username"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT id, nome, username, setor FROM usuarios WHERE username = ?
        """, (username,))
        return cursor.fetchone()
    
    def get_sector_users(self, setor_id):
        """Busca usuários de um setor específico"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT id, nome, username FROM usuarios WHERE setor_id = ?
        """, (setor_id,))
        return cursor.fetchall()
    
    def can_edit(self, username, aviso_id):
        """Verifica se usuário pode editar um aviso"""
        cursor = self.conn.cursor()
        
        # Usuário admin
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        admin_user = cursor.fetchone()
        
        if admin_user:
            return True
        
        # Usuário do mesmo setor
        cursor.execute("""
        SELECT id FROM avisos 
        WHERE id = ? AND setor_id IN (
            SELECT id FROM usuarios WHERE username = ?
        )
        """, (aviso_id, username))
        return cursor.fetchone() is not None
    
    def logout(self):
        """Realiza logout do usuário"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_id = None
