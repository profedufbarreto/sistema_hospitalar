from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import create_db_connection, setup_database 
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors 
from pymysql import IntegrityError 
from functools import wraps

# Função auxiliar para criar a conexão
def get_db_connection(cursor_factory=pymysql.cursors.DictCursor):
    return create_db_connection(cursor_factory)

# Decorator para exigir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash("Você precisa estar logado para acessar esta página.", 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'root'

# ==============================================================================
# 🔑 AUTENTICAÇÃO
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
        
        conn = get_db_connection()
        if conn is None:
            return render_template('login.html', erro='Erro de conexão com o banco de dados.')
            
        cursor = conn.cursor() 
        cursor.execute("SELECT * FROM Usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['senha'], senha):
            session['usuario'] = user['usuario']
            session['nivel'] = user['nivel_acesso']
            session['usuario_id'] = user['id'] 
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro='Usuário ou senha inválidos.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==============================================================================
# 📊 DASHBOARD (COM 5 GRÁFICOS)
# ==============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    current_year = datetime.now().year
    
    dados_dashboard = {
        'total_internados': 0,
        'altas_ultimos_7_dias': 0,
        'baixo_estoque': 0,
        'provas_vida_ultimas_24h': 0,
        'prioridade_data': {'labels': ['Verde', 'Amarelo', 'Vermelho'], 'data': [0, 0, 0]},
        'prioridade_tendencia': {'verde': [0]*12, 'amarelo': [0]*12, 'vermelho': [0]*12},
        'dias_data': {'labels': [], 'data': []},     
        'movimentacao_mensal': {'labels': ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], 'entradas': [0]*12, 'altas': [0]*12},
        'movimentacao_anual': {'labels': [], 'entradas': [], 'altas': []},
    }
    
    if conn:
        cursor = conn.cursor() 
        try:
            cursor.execute("SELECT COUNT(*) as total FROM Pacientes WHERE status = 'internado'")
            dados_dashboard['total_internados'] = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT prioridade_atencao, COUNT(*) as total FROM Pacientes WHERE status = 'internado' GROUP BY prioridade_atencao")
            for item in cursor.fetchall():
                p = (item['prioridade_atencao'] or 'verde').lower()
                if p == 'verde': dados_dashboard['prioridade_data']['data'][0] = item['total']
                elif p == 'amarelo': dados_dashboard['prioridade_data']['data'][1] = item['total']
                elif p == 'vermelho': dados_dashboard['prioridade_data']['data'][2] = item['total']

            cursor.execute(f"SELECT MONTH(data_entrada) as mes, COUNT(*) as c FROM Pacientes WHERE YEAR(data_entrada) = {current_year} GROUP BY mes")
            for r in cursor.fetchall(): dados_dashboard['movimentacao_mensal']['entradas'][r['mes']-1] = r['c']

        except Exception as e:
            print(f"Erro no dashboard: {e}")
        finally:
            conn.close()
            
    return render_template('dashboard.html', usuario=session['usuario'], nivel=session['nivel'], dados=dados_dashboard)

# ==============================================================================
# 📝 MÓDULO PRONTUÁRIO
# ==============================================================================

@app.route('/prontuario')
@login_required
def prontuario():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_medicamento FROM Estoque WHERE quantidade > 0 ORDER BY nome_medicamento")
    medicamentos = cursor.fetchall()
    conn.close()
    return render_template('prontuario_form.html', medicamentos=medicamentos)

@app.route('/prontuario/salvar', methods=['POST'])
@login_required
def salvar_prontuario():
    dados = request.form
    conn = get_db_connection(pymysql.cursors.Cursor)
    cursor = conn.cursor()
    try:
        sql = """INSERT INTO Pacientes (nome, data_nascimento, cpf, cep, endereco, bairro, data_entrada, 
                 procedimento, status, usuario_internacao, cid_10, prioridade_atencao) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'internado', %s, %s, %s)"""
        cursor.execute(sql, (dados['nome_paciente'], dados['data_nascimento'], dados['cpf'], dados['cep'], 
                            dados['endereco'], dados['bairro'], dados['hora_entrada'].replace('T', ' '), 
                            dados['procedimento'], session['usuario'], dados.get('cid_10'), dados.get('prioridade_atencao', 'verde')))
        conn.commit()
        flash("Paciente internado com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erro: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('pacientes'))

# ==============================================================================
# 👥 GESTÃO DE USUÁRIOS (ADMIN E TÉCNICO COM EDIÇÃO E HIERARQUIA)
# ==============================================================================

@app.route('/usuarios')
@login_required
def gerenciar_usuarios():
    if session['nivel'] not in ['admin', 'tecnico']:
        flash("Acesso Negado: Apenas Administradores e Técnicos podem gerenciar usuários.", 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome_completo, usuario, nivel_acesso, nacionalidade, data_nascimento FROM Usuarios ORDER BY nivel_acesso")
    usuarios = cursor.fetchall()
    conn.close()

    if session['nivel'] == 'admin':
        niveis_permitidos = ['admin', 'tecnico', 'enfermeiro', 'estagiario']
    else: # técnico
        niveis_permitidos = ['tecnico', 'enfermeiro', 'estagiario']
    
    return render_template('gerenciar_usuarios.html', 
                           usuarios=usuarios, 
                           nivel_logado=session['nivel'], 
                           niveis_permitidos=niveis_permitidos)

@app.route('/usuarios/adicionar', methods=['POST'])
@login_required
def adicionar_usuario():
    nivel_logado = session.get('nivel')
    nivel_destino = request.form.get('nivel_acesso')

    if nivel_logado == 'tecnico' and nivel_destino == 'admin':
        flash("Erro: Técnicos não podem criar usuários Administradores.", "danger")
        return redirect(url_for('gerenciar_usuarios'))
    
    if nivel_logado not in ['admin', 'tecnico']:
        return "Acesso Negado", 403

    dados = request.form
    hashed = generate_password_hash(dados['nova_senha'])
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Usuarios (nome_completo, usuario, senha, data_nascimento, nivel_acesso, nacionalidade) VALUES (%s, %s, %s, %s, %s, %s)",
                       (dados['nome_completo'], dados['usuario'], hashed, dados['data_nascimento'], nivel_destino, dados['nacionalidade']))
        conn.commit()
        flash("Usuário cadastrado com sucesso!", "success")
    except IntegrityError:
        flash("Erro: Usuário já existe.", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/editar/<int:user_id>', methods=['POST'])
@login_required
def editar_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado", 403
    
    dados = request.form
    novo_nivel = dados.get('nivel_acesso')
    novo_login = dados.get('usuario') # Pegando o novo login

    # ... (manter as travas de hierarquia de nível aqui)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if dados.get('nova_senha'):
            hashed = generate_password_hash(dados['nova_senha'])
            # Adicionado 'usuario=%s'
            sql = """UPDATE Usuarios SET nome_completo=%s, usuario=%s, nivel_acesso=%s, nacionalidade=%s, senha=%s 
                     WHERE id=%s"""
            cursor.execute(sql, (dados['nome_completo'], novo_login, novo_nivel, dados['nacionalidade'], hashed, user_id))
        else:
            # Adicionado 'usuario=%s'
            sql = """UPDATE Usuarios SET nome_completo=%s, usuario=%s, nivel_acesso=%s, nacionalidade=%s 
                     WHERE id=%s"""
            cursor.execute(sql, (dados['nome_completo'], novo_login, novo_nivel, dados['nacionalidade'], user_id))
        
        conn.commit()
        flash("Usuário e login atualizados com sucesso!", "success")
    except IntegrityError:
        flash("Erro: Esse login já está em uso por outro usuário.", "danger")
    except Exception as e:
        flash(f"Erro ao atualizar: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado", 403
    if user_id == session['usuario_id']:
        flash("Você não pode excluir sua própria conta.", "warning")
        return redirect(url_for('gerenciar_usuarios'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Usuarios WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('gerenciar_usuarios'))

# ==============================================================================
# 🩺 OPERAÇÕES HOSPITALARES
# ==============================================================================

@app.route('/pacientes')
@login_required
def pacientes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pacientes WHERE status = 'internado' ORDER BY nome")
    pacientes_internados = cursor.fetchall()
    conn.close()
    return render_template('pacientes.html', pacientes=pacientes_internados)

@app.route('/prova_vida/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
def prova_vida(paciente_id):
    if request.method == 'POST':
        dados = request.form
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO ProvasDeVida (paciente_id, data_hora, pressao_arterial, glicose, saturacao, batimentos_cardiacos, quem_efetuou) 
                          VALUES (%s, NOW(), %s, %s, %s, %s, %s)""", 
                       (paciente_id, dados['pa'], dados['glicose'], dados['sat'], dados['bpm'], session['usuario']))
        conn.commit()
        conn.close()
        flash("Sinais vitais registrados.", "success")
        return redirect(url_for('pacientes'))
    return render_template('prova_vida_form.html', paciente_id=paciente_id)

@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
@login_required
def dar_alta(paciente_id):
    if session['nivel'] not in ['admin', 'tecnico']:
        flash("Acesso Negado.", "danger")
        return redirect(url_for('pacientes'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Pacientes SET status = 'alta', data_baixa = NOW(), nome_baixa = %s WHERE id = %s", (session['usuario'], paciente_id))
    conn.commit()
    conn.close()
    flash("Alta registrada!", "success")
    return redirect(url_for('arquivo'))

@app.route('/arquivo')
@login_required
def arquivo():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pacientes WHERE status = 'alta' ORDER BY data_baixa DESC")
    pacientes_alta = cursor.fetchall()
    conn.close()
    return render_template('arquivo.html', pacientes=pacientes_alta)

# ==============================================================================
# 📦 OUTROS MÓDULOS
# ==============================================================================

@app.route('/estoque')
@login_required
def estoque():
    if session['nivel'] not in ['admin', 'tecnico', 'enfermeiro']:
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Estoque ORDER BY nome_medicamento")
    itens = cursor.fetchall()
    conn.close()
    return render_template('estoque.html', itens=itens)

@app.route('/conversor')
@login_required
def conversor():
    return render_template('conversor.html')

# ==============================================================================
# 🚀 INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    setup_database() 
    app.run(debug=True)