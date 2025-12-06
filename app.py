from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# CORREÇÃO 1: Importa a função setup_database para inicialização
from database import create_db_connection, setup_database 
from datetime import datetime
# Importa funções de segurança do próprio Flask (Werkzeug)
from werkzeug.security import generate_password_hash, check_password_hash
# CORREÇÃO 2: Importa o módulo de cursores para usar DictCursor
import pymysql.cursors 

app = Flask(__name__)
# Chave secreta é OBRIGATÓRIA para usar sessões
app.secret_key = 'sua_chave_secreta_super_segura_42'

# ==============================================================================
# 🔑 ROTAS DE AUTENTICAÇÃO E NAVEGAÇÃO BÁSICA
# ==============================================================================

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        
        conn = create_db_connection()
        if conn is None:
            return render_template('login.html', erro='Erro de conexão com o banco de dados.')
            
        # CORREÇÃO 3: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        
        # 1. BUSCA O USUÁRIO PELO NOME
        sql = "SELECT * FROM Usuarios WHERE usuario = %s"
        cursor.execute(sql, (usuario,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['senha'], senha):
            # 2. SE O USUÁRIO EXISTE, CHECA O HASH DA SENHA (CORREÇÃO DE SEGURANÇA)
            session['usuario'] = user['usuario']
            session['nivel'] = user['nivel_acesso']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro='Usuário ou senha inválidos.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('nivel', None)
    return redirect(url_for('login'))

# ==============================================================================
# 📊 ROTA PRINCIPAL (DASHBOARD)
# ==============================================================================

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = create_db_connection()
    dados_dashboard = {
        'total_internados': 0,
        'altas_ultimos_7_dias': 0,
        'baixo_estoque': 0,
        'provas_vida_ultimas_24h': 0
    }
    
    if conn:
        # Cursor padrão é suficiente, pois está usando fetchone()[0]
        cursor = conn.cursor() 
        
        try:
            # 1. TOTAL DE PACIENTES INTERNADOS
            cursor.execute("SELECT COUNT(*) FROM Pacientes WHERE status = 'internado'")
            count_internados = cursor.fetchone()[0]
            dados_dashboard['total_internados'] = count_internados
            
            # *** LINHAS DE DEBUG REMOVIDAS ***
            
            # 2. ALTAS NOS ÚLTIMOS 7 DIAS
            cursor.execute("SELECT COUNT(*) FROM Pacientes WHERE status = 'alta' AND data_baixa >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
            count_altas = cursor.fetchone()[0]
            dados_dashboard['altas_ultimos_7_dias'] = count_altas
            
            # *** LINHAS DE DEBUG REMOVIDAS ***
            
            # 3. ITENS COM BAIXO ESTOQUE (Exemplo: quantidade < 10)
            cursor.execute("SELECT COUNT(*) FROM Estoque WHERE quantidade < 10")
            count_estoque = cursor.fetchone()[0]
            dados_dashboard['baixo_estoque'] = count_estoque
            
            # *** LINHAS DE DEBUG REMOVIDAS ***

            # 4. PROVAS DE VIDA REGISTRADAS NAS ÚLTIMAS 24H
            cursor.execute("SELECT COUNT(*) FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            dados_dashboard['provas_vida_ultimas_24h'] = cursor.fetchone()[0]
            
        except Exception as e:
            # Se a conexão falhar, o erro será impresso.
            print(f"Erro CRÍTICO ao buscar dados do dashboard: {e}")
        finally:
            cursor.close()
            conn.close()
            
    # O template 'dashboard.html' deve usar a variável 'dados' para exibir os resultados.
    return render_template(
        'dashboard.html', 
        usuario=session['usuario'], 
        nivel=session['nivel'], 
        dados=dados_dashboard,
        mensagem=request.args.get('mensagem')
    )

# ==============================================================================
# 📝 MÓDULO PRONTUÁRIO
# ==============================================================================

@app.route('/prontuario')
def prontuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = create_db_connection()
    medicamentos = []
    if conn:
        # CORREÇÃO 4: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        cursor.execute("SELECT nome_medicamento FROM Estoque WHERE quantidade > 0 ORDER BY nome_medicamento")
        medicamentos = cursor.fetchall()
        cursor.close()
        conn.close()
        
    # Passa a lista de medicamentos para o formulário
    return render_template(
        'prontuario_form.html', 
        usuario=session['usuario'],
        medicamentos=medicamentos
    )

@app.route('/prontuario/salvar', methods=['POST'])
def salvar_prontuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    dados = request.form
    conn = create_db_connection()
    if conn is None:
        return "Erro de conexão com o banco de dados.", 500
        
    cursor = conn.cursor()

    try:
        # 1. SALVAR DADOS DO PACIENTE
        sql_paciente = """
        INSERT INTO Pacientes (nome, data_nascimento, cep, endereco, bairro, data_entrada, procedimento, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'internado')
        """
        # Trata a conversão de data
        try:
            data_nascimento_mysql = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        except ValueError:
            data_nascimento_mysql = None 

        data_entrada_mysql = dados['hora_entrada'].replace('T', ' ')
        
        cursor.execute(sql_paciente, (
            dados['nome_paciente'], 
            data_nascimento_mysql, 
            dados['cep'], 
            f"{dados['endereco']}, {dados['numero']}",
            dados['bairro'], 
            data_entrada_mysql,
            dados['procedimento']
        ))
        
        paciente_id = cursor.lastrowid

        # 2. SALVAR ADMINISTRAÇÃO DE MEDICAMENTO INICIAL E BAIXA DE ESTOQUE
        medicamento = dados.get('medicamento_entrada')
        medicamento_nome = None
        
        if medicamento and medicamento != 'outro':
            medicamento_nome = medicamento
        elif medicamento == 'outro' and dados.get('outro_medicamento_nome'):
            medicamento_nome = dados['outro_medicamento_nome']
            # Adiciona o novo medicamento ao estoque com quantidade inicial zero, se não existir
            cursor.execute("INSERT IGNORE INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, 0, 'UN', NOW())", (medicamento_nome,))


        if medicamento_nome:
            # CORREÇÃO: Tenta converter a dose para float, evitando ValueError se o campo estiver vazio ou for inválido
            try:
                dose = float(dados.get('dose') or 0.0) 
            except ValueError:
                conn.close()
                return "Erro: Dose de medicamento inválida. Use apenas números.", 400
            
            sql_med = """
            INSERT INTO AdministracaoMedicamentos (paciente_id, medicamento_nome, quantidade_administrada, se_necessario, data_hora)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_med, (
                paciente_id,
                medicamento_nome,
                dose,
                1 if 'se_necessario' in dados else 0,
                data_entrada_mysql
            ))
            
            # Baixa de Estoque
            if dose > 0:
                sql_baixa = "UPDATE Estoque SET quantidade = GREATEST(quantidade - %s, 0) WHERE nome_medicamento = %s"
                cursor.execute(sql_baixa, (dose, medicamento_nome))
                
                if cursor.rowcount == 0:
                    print(f"ATENÇÃO: Medicamento '{medicamento_nome}' não encontrado. Baixa não efetuada.")


        conn.commit()
        return redirect(url_for('dashboard', mensagem='Prontuário salvo com sucesso!'))
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar prontuário: {e}")
        return f"Erro interno ao salvar os dados: {e}", 500
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# 🛒 MÓDULO ESTOQUE
# ==============================================================================

@app.route('/estoque')
def estoque():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado: Permissão restrita a Admin e Técnico.", 403

    conn = create_db_connection()
    itens_estoque = []
    if conn:
        # CORREÇÃO 5: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        cursor.execute("SELECT * FROM Estoque ORDER BY nome_medicamento")
        itens_estoque = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('estoque.html', itens=itens_estoque, nivel=session['nivel'])

@app.route('/estoque/salvar', methods=['POST'])
def salvar_estoque():
    if session.get('nivel') not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403

    dados = request.form
    nome = dados['nome'].strip()
    
    # Tratamento de erro para garantir que a quantidade seja um número válido
    try:
        quantidade = int(dados['quantidade'])
    except ValueError:
        return "Quantidade deve ser um número inteiro válido.", 400
        
    unidade = dados['unidade']
    
    conn = create_db_connection()
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()
    
    try:
        # Verifica se existe, se existir, atualiza (adiciona), se não, insere
        sql_update = "UPDATE Estoque SET quantidade = quantidade + %s, unidade = %s, data_ultima_entrada = NOW() WHERE nome_medicamento = %s"
        cursor.execute(sql_update, (quantidade, unidade, nome))
        
        if cursor.rowcount == 0:
            # Não existe, então insere um novo
            sql_insert = "INSERT INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, %s, %s, NOW())"
            cursor.execute(sql_insert, (nome, quantidade, unidade))
            
        conn.commit()
        return redirect(url_for('estoque'))
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar estoque: {e}")
        return f"Erro: {e}", 500
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# ➗ MÓDULO CONVERSOR
# ==============================================================================

@app.route('/conversor')
def conversor():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    return render_template('conversor.html')

# ==============================================================================
# ❤️ MÓDULO PROVA DE VIDA
# ==============================================================================

@app.route('/prova_vida')
def prova_vida():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = create_db_connection()
    pacientes_internados = []
    if conn:
        # CORREÇÃO 6: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        cursor.execute("SELECT id, nome FROM Pacientes WHERE status = 'internado' ORDER BY nome")
        pacientes_internados = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template(
        'prova_vida_form.html', 
        pacientes=pacientes_internados,
        usuario_logado=session['usuario']
    )

@app.route('/prova_vida/salvar', methods=['POST'])
def salvar_prova_vida():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    dados = request.form
    conn = create_db_connection()
    if conn is None:
        return "Erro de conexão com o banco de dados.", 500
        
    cursor = conn.cursor()
    
    try:
        sql = """
        INSERT INTO ProvasDeVida 
        (paciente_id, data_hora, pressao_arterial, glicose, saturacao, batimentos_cardiacos, quem_efetuou, observacoes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        data_hora_mysql = dados['data_hora'].replace('T', ' ')
        
        # Garante que os campos numéricos vazios sejam None (para o MySQL)
        glicose_val = dados['glicose'] if dados['glicose'] else None
        saturacao_val = dados['saturacao'] if dados['saturacao'] else None
        batimentos_val = dados['batimentos_cardiacos'] if dados['batimentos_cardiacos'] else None
        
        cursor.execute(sql, (
            dados['paciente_id'], 
            data_hora_mysql,
            dados['pressao_arterial'], 
            glicose_val, 
            saturacao_val,
            batimentos_val,
            dados['quem_efetuou'],
            dados['observacoes']
        ))
        
        conn.commit()
        return redirect(url_for('dashboard', mensagem='Prova de vida registrada com sucesso!'))
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar Prova de Vida: {e}")
        return f"Erro interno ao salvar os dados: {e}", 500
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# 🗄️ MÓDULO ARQUIVO (ALTAS)
# ==============================================================================

@app.route('/arquivo')
def arquivo():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = create_db_connection()
    pacientes_altas = []
    if conn:
        # CORREÇÃO 7: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        cursor.execute("SELECT id, nome, data_entrada, data_baixa, procedimento FROM Pacientes WHERE status = 'alta' ORDER BY data_baixa DESC")
        pacientes_altas = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('arquivo.html', pacientes=pacientes_altas, mensagem=request.args.get('mensagem'))
    
@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
def dar_alta(paciente_id):
    if session.get('nivel') not in ['admin', 'tecnico']:
        return "Acesso Negado: Permissão restrita a Admin e Técnico.", 403
    
    conn = create_db_connection()
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()
    
    try:
        # ATUALIZA NOME_BAIXA E DATA_BAIXA
        usuario_baixa = session.get('usuario', 'N/A')
        sql = "UPDATE Pacientes SET status = 'alta', data_baixa = CURDATE(), nome_baixa = %s WHERE id = %s AND status = 'internado'"
        cursor.execute(sql, (usuario_baixa, paciente_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            return redirect(url_for('arquivo', mensagem='Alta registrada e paciente arquivado com sucesso!'))
        else:
            return "Erro: Paciente não encontrado ou já tinha alta.", 404
            
    except Exception as e:
        conn.rollback()
        print(f"Erro ao registrar alta: {e}")
        return f"Erro interno: {e}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/arquivo/detalhes/<int:paciente_id>')
def detalhes_prontuario(paciente_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = create_db_connection()
    paciente = None
    provas_vida = []
    medicamentos_admin = []
    
    if conn:
        # CORREÇÃO 8: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        
        # 1. Buscar Dados Detalhados do Paciente (Prontuário)
        cursor.execute("SELECT * FROM Pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        
        # 2. Buscar todas as Provas de Vida
        cursor.execute("SELECT * FROM ProvasDeVida WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
        provas_vida = cursor.fetchall()
        
        # 3. Buscar Histórico de Medicamentos
        cursor.execute("SELECT * FROM AdministracaoMedicamentos WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
        medicamentos_admin = cursor.fetchall()

        cursor.close()
        conn.close()
        
    if not paciente:
        return "Paciente não encontrado.", 404
        
    return render_template('detalhes_prontuario.html', paciente=paciente, provas_vida=provas_vida, medicamentos_admin=medicamentos_admin)
    
# ==============================================================================
# 👥 MÓDULO GERENCIAMENTO DE USUÁRIOS
# ==============================================================================

@app.route('/usuarios')
def gerenciar_usuarios():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado: Permissão restrita a Administradores e Técnicos.", 403

    conn = create_db_connection()
    usuarios = []
    if conn:
        # CORREÇÃO 9: Usando DictCursor do PyMySQL
        cursor = conn.cursor(pymysql.cursors.DictCursor) 
        # Filtra a visualização para Técnicos (não podem ver outros Admins/Técnicos)
        if session['nivel'] == 'tecnico':
            # Técnico vê somente Enfermeiros
            sql = "SELECT id, usuario, nivel_acesso FROM Usuarios WHERE nivel_acesso = 'enfermeiro' ORDER BY usuario"
        else: # Admin vê todos
            sql = "SELECT id, usuario, nivel_acesso FROM Usuarios ORDER BY nivel_acesso DESC, usuario"
            
        cursor.execute(sql)
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        
    # Define os níveis que o usuário logado pode criar
    niveis_permitidos = []
    if session['nivel'] == 'admin':
        niveis_permitidos = ['tecnico', 'enfermeiro']
    elif session['nivel'] == 'tecnico':
        niveis_permitidos = ['enfermeiro']
        
    return render_template(
        'gerenciar_usuarios.html', 
        usuarios=usuarios, 
        nivel_logado=session['nivel'],
        niveis_permitidos=niveis_permitidos
    )

@app.route('/usuarios/adicionar', methods=['POST'])
def adicionar_usuario():
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403

    dados = request.form
    novo_usuario = dados['novo_usuario'].strip()
    nova_senha = dados['nova_senha']
    nivel_novo = dados['nivel_acesso']

    conn = create_db_connection()
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()

    # 1. VERIFICAÇÃO DE HIERARQUIA E LIMITES
    if session['nivel'] == 'tecnico' and nivel_novo != 'enfermeiro':
        return "Acesso Negado: Técnicos só podem adicionar Enfermeiros.", 403
    
    if session['nivel'] == 'admin' and nivel_novo == 'tecnico':
        cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE nivel_acesso = 'tecnico'")
        num_tecnicos = cursor.fetchone()[0]
        if num_tecnicos >= 5:
            return "Limite máximo de 5 Técnicos atingido. Ação não permitida.", 403

    # 2. INSERÇÃO DO NOVO USUÁRIO
    try:
        # CORREÇÃO DE SEGURANÇA: HASH DA SENHA ANTES DE INSERIR
        hashed_password = generate_password_hash(nova_senha) 
        sql = "INSERT INTO Usuarios (usuario, senha, nivel_acesso) VALUES (%s, %s, %s)"
        cursor.execute(sql, (novo_usuario, hashed_password, nivel_novo))
        conn.commit()
        return redirect(url_for('gerenciar_usuarios'))
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao adicionar usuário: {e}")
        # Erro de integridade (usuário já existe)
        if 'Duplicate entry' in str(e):
             return "Erro: O nome de usuário já existe.", 500
        return f"Erro: Não foi possível adicionar o usuário. {e}", 500
    finally:
        cursor.close()
        conn.close()
        
@app.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
def excluir_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403
        
    conn = create_db_connection()
    if conn is None: return "Erro de conexão.", 500
    # CORREÇÃO 10: Usando DictCursor do PyMySQL
    cursor = conn.cursor(pymysql.cursors.DictCursor) 
    
    # 1. Busca o nível do usuário a ser excluído para verificação
    cursor.execute("SELECT nivel_acesso FROM Usuarios WHERE id = %s", (user_id,))
    user_to_delete = cursor.fetchone()
    
    if not user_to_delete:
        cursor.close()
        conn.close()
        return "Usuário não encontrado.", 404

    nivel_deletado = user_to_delete['nivel_acesso']

    # 2. VERIFICAÇÃO DE HIERARQUIA
    if session['nivel'] == 'tecnico' and nivel_deletado != 'enfermeiro':
        return "Acesso Negado: Técnicos só podem excluir usuários de nível Enfermeiro.", 403
    
    if nivel_deletado == 'admin':
        return "Acesso Negado: Não é permitido excluir o Administrador por esta via.", 403

    # 3. EXCLUSÃO
    try:
        sql = "DELETE FROM Usuarios WHERE id = %s"
        cursor.execute(sql, (user_id,))
        conn.commit()
        return redirect(url_for('gerenciar_usuarios'))
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir usuário: {e}")
        return f"Erro ao excluir usuário: {e}", 500
    finally:
        cursor.close()
        conn.close()


# ==============================================================================
# 🚀 INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    # CORREÇÃO 11: Chama a função de setup do banco de dados ANTES de iniciar o servidor
    setup_database() 
    
    # CORREÇÃO 12: Inicia o servidor Flask
    app.run(debug=True)