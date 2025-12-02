# database.py

import mysql.connector

# --- CONFIGURAÇÕES DE CONEXÃO ---
# Mude estas variáveis para as suas credenciais do MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "prontuario_hospitalar"
}

def create_db_connection():
    """Tenta estabelecer a conexão com o banco de dados."""
    try:
        # Tenta conectar usando as configurações completas
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        print("Verifique se o MySQL Server está rodando e se as credenciais (host, user, password) estão corretas.")
        return None

def setup_database():
    """Cria o banco de dados (se não existir) e todas as tabelas iniciais."""
    
    # 1. Conecta-se sem especificar o DB para garantir que ele exista
    temp_config = DB_CONFIG.copy()
    db_name = temp_config.pop("database")
    
    try:
        conn = mysql.connector.connect(**temp_config)
        cursor = conn.cursor()
        
        # Cria o banco de dados
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.close()
        conn.close()
        print(f"✅ Banco de dados '{db_name}' verificado/criado.")
    except mysql.connector.Error as err:
        print(f"❌ Erro na criação do DB: {err}")
        return

    # 2. Conecta-se ao DB criado para criar as tabelas
    conn = create_db_connection()
    if conn is None:
        print("❌ Não foi possível continuar a criação das tabelas.")
        return

    cursor = conn.cursor()
    
    print("\nIniciando criação das tabelas...")
    
    # --- CRIAÇÃO DE TABELAS ---

    # Tabela de Usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(50) NOT NULL UNIQUE,
        senha VARCHAR(255) NOT NULL, -- Armazenar a senha como hash é crucial!
        nivel_acesso ENUM('admin', 'tecnico', 'enfermeiro') NOT NULL
    )
    """)
    print("  - Tabela 'Usuarios' criada/verificada.")
    
    # Tabela de Pacientes/Prontuário
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Pacientes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        data_nascimento DATE,
        cep VARCHAR(10),
        endereco VARCHAR(255),
        bairro VARCHAR(100),
        data_entrada DATETIME NOT NULL,
        nome_baixa VARCHAR(100),
        data_baixa DATE,
        procedimento TEXT,
        status ENUM('internado', 'alta') DEFAULT 'internado'
    )
    """)
    print("  - Tabela 'Pacientes' criada/verificada.")

    # Tabela de Provas de Vida (Dados Vitais)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProvasDeVida (
        id INT AUTO_INCREMENT PRIMARY KEY,
        paciente_id INT NOT NULL,
        data_hora DATETIME NOT NULL,
        pressao_arterial VARCHAR(20),
        glicose DECIMAL(6, 2),
        saturacao DECIMAL(4, 2),
        batimentos_cardiacos INT,
        quem_efetuou VARCHAR(100),
        observacoes TEXT,
        FOREIGN KEY (paciente_id) REFERENCES Pacientes(id)
    )
    """)
    print("  - Tabela 'ProvasDeVida' criada/verificada.")

    # Tabela de Estoque
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Estoque (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome_medicamento VARCHAR(100) NOT NULL UNIQUE,
        quantidade INT NOT NULL,
        unidade VARCHAR(10),
        data_ultima_entrada DATETIME
    )
    """)
    print("  - Tabela 'Estoque' criada/verificada.")
    
    # Tabela de Registro de Administração de Medicamentos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AdministracaoMedicamentos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        paciente_id INT NOT NULL,
        medicamento_nome VARCHAR(100) NOT NULL,
        quantidade_administrada DECIMAL(6, 2) NOT NULL,
        se_necessario BOOLEAN,
        data_hora DATETIME NOT NULL,
        FOREIGN KEY (paciente_id) REFERENCES Pacientes(id)
    )
    """)
    print("  - Tabela 'AdministracaoMedicamentos' criada/verificada.")
    
    # 3. Insere o Administrador Inicial
    ADMIN_USER = 'admin'
    ADMIN_PASS_PLAINTEXT = '123456789'
    
    # Verifica se o administrador já existe
    cursor.execute("SELECT id FROM Usuarios WHERE usuario = %s", (ADMIN_USER,))
    if not cursor.fetchone():
        # AQUI VOCÊ DEVERIA USAR hash(ADMIN_PASS_PLAINTEXT)
        sql = "INSERT INTO Usuarios (usuario, senha, nivel_acesso) VALUES (%s, %s, %s)"
        cursor.execute(sql, (ADMIN_USER, ADMIN_PASS_PLAINTEXT, 'admin'))
        conn.commit()
        print(f"\n✅ Usuário administrador '{ADMIN_USER}' criado com sucesso (Senha: {ADMIN_PASS_PLAINTEXT}).")
    else:
        print(f"\nℹ️ Usuário administrador '{ADMIN_USER}' já existe.")
        
    cursor.close()
    conn.close()
    
if __name__ == '__main__':
    setup_database()