import streamlit as st
import pandas as pd
import sqlite3
import os
import bcrypt
import json
import io
from datetime import datetime, timedelta
from pathlib import Path

# ============== CONFIGURAÇÃO ==============
st.set_page_config(
    page_title="Mural de Avisos - 10ª GRE",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "database.db"

# ============== INICIALIZAÇÃO DO SESSION STATE ==============
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session_key' not in st.session_state:
    st.session_state.session_key = datetime.now().strftime("%Y%m%d%H%M%S")

# ============== FUNÇÕES DO BANCO DE DADOS ==============
def init_database(db_path):
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tabela de semanas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS semanas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_inicio DATE NOT NULL,
        data_fim DATE NOT NULL,
        numero_semana TEXT
    )
    """)
    
    # Migração: Garante que a coluna numero_semana existe
    cursor.execute("PRAGMA table_info(semanas)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'numero_semana' not in columns:
        if 'semana' in columns:
            cursor.execute("ALTER TABLE semanas RENAME COLUMN semana TO numero_semana")
        else:
            cursor.execute("ALTER TABLE semanas ADD COLUMN numero_semana TEXT")
    
    # Tabela de setores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS setores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        descricao TEXT
    )
    """)
    
    # Tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setor_id INTEGER,
        nome TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        ativo INTEGER DEFAULT 1
    )
    """)
    
    # Tabela de avisos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setor_id INTEGER NOT NULL,
        semana_id INTEGER,
        titulo TEXT NOT NULL,
        descricao TEXT NOT NULL,
        dia_da_semana TEXT NOT NULL,
        data_aviso DATE,
        horario TEXT,
        criado_por INTEGER
    )
    """)
    
    # Migração: Garante que a coluna semana_id existe em avisos
    cursor.execute("PRAGMA table_info(avisos)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'semana_id' not in columns:
        cursor.execute("ALTER TABLE avisos ADD COLUMN semana_id INTEGER")
        
    conn.commit()
    return conn

# Criar usuários e setores de exemplo
def setup_demo_data():
    """Cria setores e usuários de exemplo"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    
    # Setores
    setores = [
        (1, 'Gerente', 'Gerente Regional'),
        (2, 'NUDEA', 'Pedagógico'),
        (3, 'NUTCI', 'TI'),
        (4, 'NUDPE', 'Protagonismo'),
        (5, 'NUAFS', 'Financeiro'),
        (6, 'NUCOM', 'Comunicação'),
        (7, 'Emocional', 'Socio Emocional')
    ]
    
    for set_id, nome, desc in setores:
        cursor.execute("INSERT OR IGNORE INTO setores (id, nome, descricao) VALUES (?, ?, ?)",
                       (set_id, nome, desc))
    
    # Usuários
    usuarios = [
        (1, None, 'Administrador', 'admin', 'admin123', 'mural10gre@see.pb.gov.br', 1),
        (2, 1, 'João Alexandre', 'joao', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (3, 2, 'Davi', 'davi', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (4, 3, 'Leonardo', 'leonardo', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (5, 4, 'Juciely', 'juciely', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (6, 5, 'Victoria', 'victoria', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (7, 6, 'Paulino', 'paulino', 'teste123', 'mural10gre@see.pb.gov.br', 1),
        (8, 7, 'Emocional', 'emocional', 'teste123', 'mural10gre@see.pb.gov.br', 1),
    ]
    
    for u_id, setor_id, nome, username, password, email, ativo in usuarios:
        cursor.execute("""
        INSERT OR IGNORE INTO usuarios (id, setor_id, nome, username, email, password_hash, ativo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (u_id, setor_id, nome, username, email, 
              bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), ativo))
    
    conn.commit()
    conn.close()

# Criar dados de exemplo se não existir
if not any(row[0] for row in init_database(DB_PATH).execute("SELECT id FROM setores")):
    setup_demo_data()

# ============== AUTENTICAÇÃO ==============
def authenticate(username, password):
    """Autentica usuário e retorna usuário se válido"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, setor_id, nome, username, email, password_hash, ativo
    FROM usuarios WHERE username = ? AND ativo = 1
    """, (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        password_bytes = password.encode('utf-8')
        password_hash = user[5]
        
        try:
            password_hash_bytes = bytes.fromhex(password_hash)
            if bcrypt.checkpw(password_bytes, password_hash_bytes):
                return {
                    'id': user[0],
                    'setor_id': user[1],
                    'nome': user[2],
                    'username': user[3],
                    'email': user[4],
                    'ativo': user[6]
                }
        except:
            if bcrypt.checkpw(password_bytes, user[5].encode('utf-8')):
                return {
                    'id': user[0],
                    'setor_id': user[1],
                    'nome': user[2],
                    'username': user[3],
                    'email': user[4],
                    'ativo': user[6]
                }
    return None

def change_own_password(usuario_id, senha_atual, nova_senha):
    """Troca a senha do próprio usuário após verificar a senha atual"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM usuarios WHERE id = ?", (usuario_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False, "Usuário não encontrado."
    try:
        stored = row[0]
        try:
            match = bcrypt.checkpw(senha_atual.encode('utf-8'), bytes.fromhex(stored))
        except Exception:
            match = bcrypt.checkpw(senha_atual.encode('utf-8'), stored.encode('utf-8'))
        if not match:
            return False, "Senha atual incorreta."
    except Exception:
        return False, "Erro ao verificar senha."
    nova_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (nova_hash, usuario_id))
    conn.commit()
    conn.close()
    return True, "Senha alterada com sucesso!"

# ============== FUNÇÕES DE SEMANA ==============
def get_current_week_id():
    """Obtém o ID da semana atual (ou cria se não existir)"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    cursor.execute("SELECT id FROM semanas WHERE data_inicio = ?", (week_start,))
    week = cursor.fetchone()
    
    if week:
        conn.close()
        return week[0]
    
    # Se não existe, vamos criar
    numero_semana = f"Semana {week_start.strftime('%d/%m')}"
    cursor.execute("INSERT INTO semanas (data_inicio, data_fim, numero_semana) VALUES (?, ?, ?)",
                   (week_start, week_end, numero_semana))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_week_info(week_id):
    """Retorna informações da semana"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT data_inicio, data_fim, numero_semana FROM semanas WHERE id = ?", (week_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_all_weeks():
    """Retorna todas as semanas cadastradas"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_inicio, data_fim, numero_semana FROM semanas ORDER BY data_inicio DESC")
    weeks = cursor.fetchall()
    conn.close()
    return weeks

def add_semana(data_inicio, data_fim, numero_semana):
    """Adiciona nova semana"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO semanas (data_inicio, data_fim, numero_semana) VALUES (?, ?, ?)",
                   (data_inicio, data_fim, numero_semana))
    conn.commit()
    conn.close()

def edit_semana(semana_id, data_inicio, data_fim, numero_semana):
    """Edita semana existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE semanas SET data_inicio = ?, data_fim = ?, numero_semana = ? WHERE id = ?",
                   (data_inicio, data_fim, numero_semana, semana_id))
    conn.commit()
    conn.close()

def delete_semana(semana_id):
    """Apaga semana existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semanas WHERE id = ?", (semana_id,))
    cursor.execute("DELETE FROM avisos WHERE semana_id = ?", (semana_id,))
    conn.commit()
    conn.close()

# ============== FUNÇÕES DE SETORES ==============
def get_all_setores():
    """Retorna todos os setores cadastrados"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, descricao FROM setores ORDER BY nome")
    sectors = cursor.fetchall()
    conn.close()
    return sectors

def add_setor(nome, descricao):
    """Adiciona novo setor"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO setores (nome, descricao) VALUES (?, ?)", (nome, descricao))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def edit_setor(setor_id, nome, descricao):
    """Edita setor existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE setores SET nome = ?, descricao = ? WHERE id = ?", (nome, descricao, setor_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_setor(setor_id):
    """Apaga setor existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM setores WHERE id = ?", (setor_id,))
    cursor.execute("UPDATE usuarios SET setor_id = NULL WHERE setor_id = ?", (setor_id,))
    cursor.execute("DELETE FROM avisos WHERE setor_id = ?", (setor_id,))
    conn.commit()
    conn.close()

# ============== FUNÇÕES DE USUÁRIOS ==============
def get_all_usuarios():
    """Retorna todos os usuários cadastrados"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.setor_id, u.nome, u.username, u.email, u.ativo, s.nome as setor_nome 
        FROM usuarios u
        LEFT JOIN setores s ON u.setor_id = s.id
        ORDER BY u.nome
    """)
    users = cursor.fetchall()
    conn.close()
    return users

def add_usuario(setor_id, nome, username, password, email, ativo=1):
    """Adiciona novo usuário"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        cursor.execute("""
            INSERT INTO usuarios (setor_id, nome, username, password_hash, email, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (setor_id, nome, username, password_hash, email, ativo))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def edit_usuario(usuario_id, setor_id, nome, username, email, ativo, password=None):
    """Edita usuário existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    try:
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                UPDATE usuarios 
                SET setor_id = ?, nome = ?, username = ?, email = ?, ativo = ?, password_hash = ?
                WHERE id = ?
            """, (setor_id, nome, username, email, ativo, password_hash, usuario_id))
        else:
            cursor.execute("""
                UPDATE usuarios 
                SET setor_id = ?, nome = ?, username = ?, email = ?, ativo = ?
                WHERE id = ?
            """, (setor_id, nome, username, email, ativo, usuario_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_usuario(usuario_id):
    """Apaga usuário existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()

# ============== FUNÇÕES DE AVISOS ==============
def get_aviso_data_for_sector(week_id, sector_id, dia):
    """Retorna avisos para um setor, semana e dia específicos, incluindo data"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.titulo, a.descricao, a.horario, a.data_aviso, a.criado_por, u.username
        FROM avisos a
        LEFT JOIN usuarios u ON a.criado_por = u.id
        WHERE a.semana_id = ? AND a.setor_id = ? AND a.dia_da_semana = ?
        ORDER BY a.horario
    """, (week_id, sector_id, dia))
    results = cursor.fetchall()
    conn.close()
    return results

def add_aviso(titulo, descricao, setor_id, semana_id, dia, horario, criado_por=None):
    """Adiciona novo aviso"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO avisos (setor_id, semana_id, titulo, descricao, dia_da_semana, data_aviso, horario, criado_por)
    VALUES (?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)
    """, (setor_id, semana_id, titulo, descricao, dia, horario, criado_por))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def edit_aviso(aviso_id, titulo, descricao, horario=None):
    """Edita aviso existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE avisos SET titulo = ?, descricao = ?, horario = ? WHERE id = ?",
                   (titulo, descricao, horario, aviso_id))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count > 0

def delete_aviso(aviso_id):
    """Apaga aviso existente"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM avisos WHERE id = ?", (aviso_id,))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count > 0

# ============== INTERFACE ==============
def load_css():
    """Carrega o CSS customizado se existir"""
    css_path = Path("frontend/style.css")
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_login_sidebar():
    with st.sidebar:
        st.header("🔐 Autenticação")
        
        user = st.session_state.user
        
        if user:
            st.success(f"👤 {user['nome']}")

            with st.expander("🔑 Trocar Senha", expanded=False):
                senha_atual = st.text_input("Senha atual:", type="password", key="change_pass_atual")
                nova_senha = st.text_input("Nova senha:", type="password", key="change_pass_nova")
                confirmar_senha = st.text_input("Confirmar nova senha:", type="password", key="change_pass_confirm")
                if st.button("Salvar nova senha", key="change_pass_btn", use_container_width=True):
                    if not senha_atual or not nova_senha or not confirmar_senha:
                        st.error("Preencha todos os campos.")
                    elif nova_senha != confirmar_senha:
                        st.error("As senhas novas não coincidem.")
                    elif len(nova_senha) < 4:
                        st.error("A nova senha deve ter pelo menos 4 caracteres.")
                    else:
                        ok, msg = change_own_password(user['id'], senha_atual, nova_senha)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

            if st.button("🚪 Sair", use_container_width=True):
                st.session_state.user = None
                st.rerun()
        else:
            username_input = st.text_input("Usuário:", key="login_user")
            password_input = st.text_input("Senha:", type="password", key="login_pass")
            
            if st.button("Entrar", key="login_btn", use_container_width=True):
                user_data = authenticate(username_input, password_input)
                if user_data:
                    st.session_state.user = user_data
                    st.success(f"Login realizado! 👋")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos")
    
    st.divider()

def render_mural_grid(week_id):
    """Renderiza a grade/planilha de avisos com setores nas linhas e dias nas colunas"""
    # Fetch sectors and order them as defined in mudar.txt
    sectors = get_all_setores()
    user = st.session_state.user
    day_names = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    # Desired display order (case-sensitive matching names in DB)
    desired_order = ["Gerente", "NUDEA", "Emocional", "NUTCI", "NUDPE", "NUAFS", "NUCOM"]
    # Create ordered list preserving tuples (id, nome, desc)
    ordered_sectors = []
    for name in desired_order:
        for sec in sectors:
            if sec[1] == name:
                ordered_sectors.append(sec)
    # Fallback to any sectors not in the desired order
    remaining = [sec for sec in sectors if sec not in ordered_sectors]
    sectors = ordered_sectors + remaining
    
    if not sectors:
        st.info("ℹ️ Nenhum setor cadastrado ainda.")
        return

    # Injeta estilos customizados para visualização compacta na grade
    st.markdown(
        """
        <style>
        .grid-header {
            font-weight: bold;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 8px;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sector-cell {
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 6px;
            border: 1px solid #dee2e6;
            margin-bottom: 8px;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .sector-title {
            font-weight: bold;
            color: #764ba2;
            font-size: 15px;
            margin: 0;
        }
        .sector-desc {
            font-size: 11px;
            color: #6c757d;
            margin: 2px 0 0 0;
            line-height: 1.2;
        }
        .notice-card-small {
            background-color: white;
            border-left: 3px solid #764ba2;
            padding: 8px;
            border-radius: 4px;
            margin-top: 6px;
            margin-bottom: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .notice-title-small {
            font-size: 13px;
            font-weight: bold;
            color: #333;
            margin: 0 0 4px 0;
        }
        .notice-desc-small {
            font-size: 12px;
            color: #495057;
            margin: 0 0 4px 0;
            white-space: pre-wrap;
            line-height: 1.3;
        }
        .notice-meta-small {
            font-size: 10px;
            color: #868e96;
            line-height: 1.2;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Grade de colunas: Setor (1.2), Segunda (2), Terça (2), Quarta (2), Quinta (2), Sexta (2)
    col_widths = [1.2, 2, 2, 2, 2, 2]
    
    # 1. Linha do Cabeçalho
    header_cols = st.columns(col_widths)
    with header_cols[0]:
        st.markdown('<div class="grid-header">🏢 Setor</div>', unsafe_allow_html=True)
    for idx, day in enumerate(day_names):
        with header_cols[idx + 1]:
            st.markdown(f'<div class="grid-header">📅 {day}</div>', unsafe_allow_html=True)
            
    # 2. Linhas de dados (Setores)
    for sector_id, sector_nome, sector_desc in sectors:
        row_cols = st.columns(col_widths)
        
        # Coluna do Setor (Identificação)
        with row_cols[0]:
            st.markdown(
                f"""
                <div class="sector-cell">
                    <div class="sector-title">{sector_nome}</div>
                    <div class="sector-desc">{sector_desc or 'Sem descrição'}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # Colunas dos dias da semana
        for idx, day_name in enumerate(day_names):
            with row_cols[idx + 1]:
                with st.container(border=True):
                    # Verificar permissão para adicionar aviso neste setor
                    can_add = user and (user['username'] == 'admin' or user['setor_id'] == sector_id)
                    
                    # Botão compactado para adicionar
                    if can_add:
                        # Coloca o popover de cadastro no topo do container da célula
                        with st.popover("➕ Novo", use_container_width=True):
                            st.markdown(f"**Novo aviso: {sector_nome} ({day_name})**")
                            add_titulo = st.text_input("Título:", key=f"add_title_{day_name}_{sector_id}")
                            add_desc = st.text_area("Descrição:", key=f"add_desc_{day_name}_{sector_id}")
                            add_horario = st.text_input("Horário (opcional):", placeholder="Ex: 14:00", key=f"add_time_{day_name}_{sector_id}")
                            
                            if st.button("Salvar", key=f"save_btn_{day_name}_{sector_id}", use_container_width=True):
                                if add_titulo and add_desc:
                                    add_aviso(add_titulo, add_desc, sector_id, week_id, day_name, add_horario, criado_por=user['id'])
                                    st.success("Adicionado!")
                                    st.rerun()
                                else:
                                    st.error("Campos obrigatórios!")
                                    
                    # Buscar e listar avisos
                    avisos = get_aviso_data_for_sector(week_id, sector_id, day_name)
                    
                    if not avisos:
                        st.caption("📭 Sem avisos")
                    else:
                        for av_id, av_titulo, av_desc, av_horario, av_data, av_criado_por, av_username in avisos:
                            # Formatar data no formato DD/MM/AAAA
                            if av_data:
                                try:
                                    av_data_fmt = datetime.strptime(av_data, '%Y-%m-%d').strftime('%d/%m/%Y')
                                except Exception:
                                    av_data_fmt = av_data
                            else:
                                av_data_fmt = None

                            st.markdown(
                                f"""
                                <div class="notice-card-small">
                                    <div class="notice-title-small">📌 {av_titulo}</div>
                                    <div class="notice-desc-small">{av_desc}</div>
                                    <div class="notice-meta-small">
                                        {f'📅 {av_data_fmt}<br/>' if av_data_fmt else ''}{f'⏰ {av_horario}<br/>' if av_horario else ''}👤 {av_username or 'Sistema'}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            # Opções de editar/deletar (admin ou dono do setor)
                            can_edit_delete = user and (user['username'] == 'admin' or user['setor_id'] == sector_id)
                            if can_edit_delete:
                                col_edit, col_del = st.columns(2)
                                with col_edit:
                                    with st.popover("📝", help="Editar Aviso", use_container_width=True):
                                        st.write("**Editar Aviso**")
                                        new_titulo = st.text_input("Título:", value=av_titulo, key=f"edit_title_{av_id}")
                                        new_desc = st.text_area("Descrição:", value=av_desc, key=f"edit_desc_{av_id}")
                                        new_horario = st.text_input("Horário:", value=av_horario or "", key=f"edit_time_{av_id}")
                                        if st.button("Salvar", key=f"save_edit_{av_id}", use_container_width=True):
                                            if new_titulo and new_desc:
                                                edit_aviso(av_id, new_titulo, new_desc, new_horario)
                                                st.success("Atualizado!")
                                                st.rerun()
                                            else:
                                                st.error("Campos vazios!")
                                with col_del:
                                    with st.popover("🗑️", help="Excluir Aviso", use_container_width=True):
                                        st.write("Excluir aviso permanentemente?")
                                        if st.button("Confirmar", key=f"del_btn_{av_id}", type="primary", use_container_width=True):
                                            delete_aviso(av_id)
                                            st.success("Excluído!")
                                            st.rerun()
        st.divider()


# render_week_navigation removida: o sistema sempre exibe a semana vigente automaticamente.

# ============== PAINEL ADMINISTRATIVO ==============
def render_admin_setores():
    st.header("🏢 Gerenciar Setores")
    
    # 1. Formulário para adicionar setor
    with st.expander("➕ Adicionar Novo Setor", expanded=False):
        new_nome = st.text_input("Nome do Setor:")
        new_desc = st.text_input("Descrição/Função:")
        if st.button("Cadastrar Setor", type="primary"):
            if new_nome:
                if add_setor(new_nome, new_desc):
                    st.success(f"Setor '{new_nome}' cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Nome de setor já existe!")
            else:
                st.error("O nome é obrigatório!")

    # 2. Listagem de setores com edição/exclusão
    sectors = get_all_setores()
    if not sectors:
        st.info("Nenhum setor cadastrado.")
        return
        
    st.write("### Setores Cadastrados")
    for sec_id, nome, desc in sectors:
        with st.container(border=True):
            col_info, col_edit, col_del = st.columns([4, 1, 1])
            with col_info:
                st.markdown(f"**{nome}**")
                st.caption(desc or "Sem descrição")
            
            with col_edit:
                with st.popover("📝 Editar", use_container_width=True):
                    edit_nome = st.text_input("Nome:", value=nome, key=f"edit_sec_name_{sec_id}")
                    edit_desc = st.text_input("Descrição:", value=desc or "", key=f"edit_sec_desc_{sec_id}")
                    if st.button("Salvar Alterações", key=f"save_sec_btn_{sec_id}", use_container_width=True):
                        if edit_nome:
                            if edit_setor(sec_id, edit_nome, edit_desc):
                                st.success("Atualizado!")
                                st.rerun()
                            else:
                                st.error("Erro ou nome já existente!")
                        else:
                            st.error("Nome obrigatório!")
            
            with col_del:
                with st.popover("🗑️ Excluir", use_container_width=True):
                    st.warning("A exclusão removerá todos os avisos deste setor!")
                    if st.button("Confirmar Exclusão", key=f"del_sec_btn_{sec_id}", type="primary", use_container_width=True):
                        delete_setor(sec_id)
                        st.success("Setor excluído!")
                        st.rerun()

def render_admin_usuarios():
    st.header("👤 Gerenciar Usuários")
    
    sectors = get_all_setores()
    sector_options = {nome: sec_id for sec_id, nome, _ in sectors}
    sector_names = ["(Nenhum/Admin)"] + list(sector_options.keys())
    
    # 1. Formulário para adicionar usuário
    with st.expander("➕ Adicionar Novo Usuário", expanded=False):
        new_nome = st.text_input("Nome Completo:")
        new_username = st.text_input("Nome de Usuário (username):")
        new_password = st.text_input("Senha inicial:", type="password")
        new_email = st.text_input("E-mail:")
        new_sector_name = st.selectbox("Setor associado:", sector_names, key="add_user_sec")
        new_ativo = st.toggle("Usuário ativo", value=True)
        
        selected_sector_id = sector_options[new_sector_name] if new_sector_name != "(Nenhum/Admin)" else None
        
        if st.button("Cadastrar Usuário", type="primary"):
            if new_nome and new_username and new_password:
                if add_usuario(selected_sector_id, new_nome, new_username, new_password, new_email, 1 if new_ativo else 0):
                    st.success(f"Usuário '{new_username}' cadastrado!")
                    st.rerun()
                else:
                    st.error("Username já existe!")
            else:
                st.error("Nome, username e senha são obrigatórios!")

    # 2. Listagem de usuários
    users = get_all_usuarios()
    if not users:
        st.info("Nenhum usuário cadastrado.")
        return
        
    st.write("### Usuários Cadastrados")
    for u_id, setor_id, nome, username, email, ativo, setor_nome in users:
        with st.container(border=True):
            col_info, col_edit, col_del = st.columns([4, 1, 1])
            with col_info:
                sec_badge = f"🏢 Setor: **{setor_nome}**" if setor_nome else "⚙️ **Administrador / Sem Setor**"
                status_badge = "🟢 Ativo" if ativo else "🔴 Inativo"
                st.markdown(f"**{nome}** ({username}) — {status_badge}")
                st.caption(f"{sec_badge} | ✉️ {email or 'Sem email'}")
            
            with col_edit:
                with st.popover("📝 Editar", use_container_width=True):
                    edit_nome = st.text_input("Nome Completo:", value=nome, key=f"edit_u_nome_{u_id}")
                    edit_username = st.text_input("Username:", value=username, key=f"edit_u_username_{u_id}")
                    edit_email = st.text_input("Email:", value=email or "", key=f"edit_u_email_{u_id}")
                    
                    # Encontrar índice do setor atual
                    current_sector_index = 0
                    if setor_nome and setor_nome in sector_options:
                        current_sector_index = sector_names.index(setor_nome)
                        
                    edit_sector_name = st.selectbox("Setor:", sector_names, index=current_sector_index, key=f"edit_u_sec_{u_id}")
                    edit_ativo = st.toggle("Usuário ativo", value=bool(ativo), key=f"edit_u_ativo_{u_id}")
                    
                    st.markdown("---")
                    st.write("🔑 **Alterar Senha** (deixe em branco para manter)")
                    edit_password = st.text_input("Nova Senha:", type="password", key=f"edit_u_pass_{u_id}")
                    
                    edit_selected_sector_id = sector_options[edit_sector_name] if edit_sector_name != "(Nenhum/Admin)" else None
                    
                    if st.button("Salvar Alterações", key=f"save_u_btn_{u_id}", use_container_width=True):
                        if edit_nome and edit_username:
                            if edit_usuario(u_id, edit_selected_sector_id, edit_nome, edit_username, edit_email, 1 if edit_ativo else 0, edit_password if edit_password else None):
                                st.success("Atualizado!")
                                st.rerun()
                            else:
                                st.error("Erro ou username duplicado!")
                        else:
                            st.error("Nome e username são obrigatórios!")
            
            with col_del:
                if username == 'admin':
                    st.button("🗑️", disabled=True, help="Não é possível excluir o administrador.")
                else:
                    with st.popover("🗑️ Excluir", use_container_width=True):
                        st.warning(f"Excluir '{username}' permanentemente?")
                        if st.button("Confirmar", key=f"del_u_btn_{u_id}", type="primary", use_container_width=True):
                            delete_usuario(u_id)
                            st.success("Usuário excluído!")
                            st.rerun()

def export_avisos_semana(week_id):
    """Exporta todos os avisos da semana como JSON para backup"""
    conn = init_database(DB_PATH)
    cursor = conn.cursor()
    # Info da semana
    cursor.execute("SELECT data_inicio, data_fim, numero_semana FROM semanas WHERE id = ?", (week_id,))
    week_row = cursor.fetchone()
    # Avisos
    cursor.execute("""
        SELECT a.titulo, a.descricao, a.dia_da_semana, a.horario, s.nome as setor_nome
        FROM avisos a
        LEFT JOIN setores s ON a.setor_id = s.id
        WHERE a.semana_id = ?
        ORDER BY s.nome, a.dia_da_semana, a.horario
    """, (week_id,))
    avisos = cursor.fetchall()
    conn.close()

    data = {
        "semana": {
            "data_inicio": week_row[0] if week_row else None,
            "data_fim": week_row[1] if week_row else None,
            "rotulo": week_row[2] if week_row else None,
        },
        "avisos": [
            {
                "titulo": av[0],
                "descricao": av[1],
                "dia_da_semana": av[2],
                "horario": av[3],
                "setor_nome": av[4],
            }
            for av in avisos
        ]
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_avisos_semana(json_str, week_id):
    """Importa avisos de um JSON de backup para a semana vigente"""
    try:
        data = json.loads(json_str)
    except Exception as e:
        return False, f"Arquivo inválido: {e}"

    avisos = data.get("avisos", [])
    if not avisos:
        return False, "Nenhum aviso encontrado no arquivo."

    conn = init_database(DB_PATH)
    cursor = conn.cursor()

    # Mapear nome de setor -> id
    cursor.execute("SELECT id, nome FROM setores")
    setor_map = {nome: sid for sid, nome in cursor.fetchall()}

    imported = 0
    errors = []
    for av in avisos:
        setor_nome = av.get("setor_nome")
        setor_id = setor_map.get(setor_nome)
        if not setor_id:
            errors.append(f"Setor '{setor_nome}' não encontrado, aviso ignorado.")
            continue
        try:
            cursor.execute("""
                INSERT INTO avisos (setor_id, semana_id, titulo, descricao, dia_da_semana, data_aviso, horario, criado_por)
                VALUES (?, ?, ?, ?, ?, CURRENT_DATE, ?, NULL)
            """, (setor_id, week_id, av.get("titulo", ""), av.get("descricao", ""),
                  av.get("dia_da_semana", ""), av.get("horario", "")))
            imported += 1
        except Exception as e:
            errors.append(str(e))

    conn.commit()
    conn.close()

    msg = f"{imported} aviso(s) importado(s) com sucesso."
    if errors:
        msg += " Avisos ignorados: " + "; ".join(errors)
    return True, msg


def render_admin_backup():
    """Painel de backup e importação de avisos da semana vigente"""
    st.header("💾 Backup e Importação de Avisos")

    week_id = get_current_week_id()
    week_info = get_week_info(week_id)
    if week_info:
        try:
            start_fmt = datetime.strptime(week_info[0], "%Y-%m-%d").strftime("%d/%m/%Y")
            end_fmt = datetime.strptime(week_info[1], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            start_fmt, end_fmt = week_info[0], week_info[1]
        st.info(f"📅 Semana vigente: **{week_info[2]}** ({start_fmt} – {end_fmt})")

    st.subheader("📤 Exportar (Backup)")
    st.write("Baixe um arquivo JSON com todos os avisos da semana atual.")
    if st.button("Gerar Backup da Semana Vigente", type="primary"):
        json_data = export_avisos_semana(week_id)
        filename = f"backup_avisos_{datetime.now().strftime('%Y%m%d')}.json"
        st.download_button(
            label="⬇️ Baixar Backup JSON",
            data=json_data.encode("utf-8"),
            file_name=filename,
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    st.subheader("📥 Importar Avisos")
    st.write("Carregue um arquivo JSON de backup para importar os avisos para a semana vigente.")
    st.warning("⚠️ Os avisos importados serão **adicionados** aos existentes. Avisos duplicados não serão verificados automaticamente.")

    uploaded_file = st.file_uploader("Selecione o arquivo de backup (.json):", type=["json"], key="backup_upload")
    if uploaded_file is not None:
        if st.button("Importar Avisos para Semana Vigente", type="primary", key="import_btn"):
            json_str = uploaded_file.read().decode("utf-8")
            ok, msg = import_avisos_semana(json_str, week_id)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ============== INTERFACE PRINCIPAL ==============
def main():
    st.title("🏛️ Mural de Avisos - 10ª GRE")
    
    # Carregar estilos css
    load_css()
    
    # Sempre usa a semana vigente
    current_week_id = get_current_week_id()
    
    # Renderizar login
    render_login_sidebar()
    
    user = st.session_state.user
    
    # Definir menu para administrador ou usuário comum
    if user and user['username'] == 'admin':
        st.sidebar.divider()
        st.sidebar.subheader("⚙️ Administração")
        menu = st.sidebar.radio(
            "Navegar para:",
            ["📋 Mural de Avisos", "🏢 Gerenciar Setores", "👤 Gerenciar Usuários", "💾 Backup e Importação"]
        )
    else:
        menu = "📋 Mural de Avisos"
        
    # Renderizar conteúdo selecionado
    if menu == "📋 Mural de Avisos":
        # Exibe a semana vigente
        week_info = get_week_info(current_week_id)
        if week_info:
            try:
                start_fmt = datetime.strptime(week_info[0], "%Y-%m-%d").strftime("%d/%m/%Y")
                end_fmt = datetime.strptime(week_info[1], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                start_fmt, end_fmt = week_info[0], week_info[1]
            st.caption(f"📅 Semana vigente: **{week_info[2]}** — {start_fmt} a {end_fmt}")

        # Mural principal em formato de planilha/grade
        st.write("")
        render_mural_grid(current_week_id)
                
    elif menu == "🏢 Gerenciar Setores":
        render_admin_setores()
    elif menu == "👤 Gerenciar Usuários":
        render_admin_usuarios()
    elif menu == "💾 Backup e Importação":
        render_admin_backup()

if __name__ == "__main__":
    main()
