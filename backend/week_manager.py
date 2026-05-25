import sqlite3
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

DB_PATH = os.getenv("DB_PATH", "./database.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

class WeekManager:
    def __init__(self, conn):
        self.conn = conn
    
    def get_current_week_id(self):
        """Pega ID da semana atual"""
        cursor = self.conn.cursor()
        today = datetime.now()
        
        # Calcular semana atual (segunda-feira)
        week_start = today - timedelta(days=today.weekday())
        
        cursor.execute("""
        SELECT id FROM semanas 
        WHERE data_inicio >= ?
        ORDER BY id DESC LIMIT 1
        """, (week_start,))
        
        week = cursor.fetchone()
        return week[0] if week else self.create_new_week()
    
    def create_new_week(self):
        """Cria nova semana se não existir"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT MAX(id) FROM semanas")
        last_id = cursor.fetchone()[0]
        
        new_id = last_id + 1 if last_id else 1
        
        cursor.execute("""
        INSERT INTO semanas (id, data_inicio, data_fim) VALUES (?, ?, ?)
        """, (new_id, week_start, week_end))
        
        self.conn.commit()
        return new_id
    
    def get_week_dates(self, week_id):
        """Pega datas de início e fim da semana"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT data_inicio, data_fim FROM semanas WHERE id = ?
        """, (week_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_week_number(self, week_id):
        """Pega número da semana"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT semana FROM semanas WHERE id = ?", (week_id,))
        return cursor.fetchone()[0]
    
    def get_week_data(self, week_id):
        """Pega todos os avisos de uma semana"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
        SELECT a.*, s.nome as setor
        FROM avisos a
        JOIN setores s ON a.setor_id = s.id
        WHERE a.semana_id = ?
        ORDER BY a.dia_da_semana, a.horario
        """, (week_id,))
        
        return cursor.fetchall()
    
    def get_week_data_for_day(self, week_id, dia):
        """Pega avisos de um dia específico"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
        SELECT a.*, s.nome as setor
        FROM avisos a
        JOIN setores s ON a.setor_id = s.id
        WHERE a.semana_id = ? AND a.dia_da_semana = ?
        ORDER BY a.horario
        """, (week_id, dia))
        
        return cursor.fetchone()
    
    def add_aviso(self, titulo, descricao, setor_id, dia, horario=None):
        """Adiciona novo aviso"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
        INSERT INTO avisos (titulo, descricao, setor_id, dia_da_semana, horario)
        VALUES (?, ?, ?, ?, ?)
        """, (titulo, descricao, setor_id, dia, horario))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_sectors(self):
        """Pega todos os setores"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM setores")
        return cursor.fetchall()
    
    def get_all_days(self):
        """Pega dias da semana"""
        return ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    
    def set_week(self, week_id):
        """Define semana específica"""
        self.conn.execute("SELECT data_inicio FROM semanas WHERE id = ?", (week_id,))
        return True
