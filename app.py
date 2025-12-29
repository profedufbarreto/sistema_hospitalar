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
            flash("Você precisa estar logado.", 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'root'

# ==============================================================================
# 🔑 AUTENTICAÇÃO E DASHBOARD
# ==============================================================================

@app.route('/')
def index():
    if 'usuario' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        conn = get_db_connection()
        if conn is None: return render_template('login.html', erro='Erro de conexão.')
        cursor = conn.cursor() 
        cursor.execute("SELECT * FROM Usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['senha'], senha):
            session['usuario'] = user['usuario']
            session['nivel'] = user['nivel_acesso']
            session['usuario_id'] = user['id'] 
            return redirect(url_for('dashboard'))
        return render_template('login.html', erro='Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    current_year = datetime.now().year
    
    dados_dashboard = {
        'total_internados': 0, 'altas_ultimos_7_dias': 0, 'baixo_estoque': 0, 'provas_vida_ultimas_24h': 0,
        'prioridade_data': {'labels': ['Verde', 'Amarelo', 'Vermelho'], 'data': [0, 0, 0]},
        'prioridade_tendencia': {'verde': [0]*12, 'amarelo': [0]*12, 'vermelho': [0]*12},
        'dias_data': {'labels': [], 'data': []},     
        'movimentacao_mensal': {'labels': ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], 'entradas': [0]*12, 'altas': [0]*12},
        # Agora as listas serão preenchidas
        'movimentacao_anual': {'labels': [], 'entradas': [], 'altas': []},
    }
    
    if conn:
        cursor = conn.cursor() 
        try:
            # (Mantendo suas consultas anteriores de internados, altas 7d, estoque e pv...)
            cursor.execute("SELECT COUNT(*) as total FROM Pacientes WHERE status = 'internado'")
            dados_dashboard['total_internados'] = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as total FROM Pacientes WHERE status = 'alta' AND data_baixa >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
            dados_dashboard['altas_ultimos_7_dias'] = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as total FROM Estoque WHERE quantidade < 100")
            dados_dashboard['baixo_estoque'] = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT COUNT(*) as total FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            dados_dashboard['provas_vida_ultimas_24h'] = cursor.fetchone()['total'] or 0

            # LÓGICA DO HISTÓRICO ANUAL (O QUE ESTAVA FALTANDO)
            # Busca os últimos 5 anos para comparar
            sql_anual = """
                SELECT YEAR(data_entrada) as ano, COUNT(*) as entradas,
                SUM(CASE WHEN status = 'alta' THEN 1 ELSE 0 END) as altas
                FROM Pacientes 
                GROUP BY ano ORDER BY ano ASC LIMIT 5
            """
            cursor.execute(sql_anual)
            resultados_anual = cursor.fetchall()
            
            for row in resultados_anual:
                if row['ano']:
                    dados_dashboard['movimentacao_anual']['labels'].append(str(row['ano']))
                    dados_dashboard['movimentacao_anual']['entradas'].append(row['entradas'])
                    dados_dashboard['movimentacao_anual']['altas'].append(int(row['altas']))

            # Prioridades e Mensal (Mantendo igual ao seu código)
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

@app.route('/api/kpi/<tipo>/<periodo>')
@login_required
def api_kpi(tipo, periodo):
    conn = get_db_connection()
    cursor = conn.cursor()
    valor = 0
    try:
        if tipo == 'altas':
            # Mapeamento estendido de períodos
            dias = 7
            if periodo == '15d': dias = 15
            elif periodo == '30d': dias = 30
            elif periodo == 'trimestre': dias = 90
            elif periodo == 'semestre': dias = 180
            elif periodo == 'ano': dias = 365
            
            cursor.execute("""
                SELECT COUNT(*) as total FROM Pacientes 
                WHERE status = 'alta' AND data_baixa >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (dias,))
            valor = cursor.fetchone()['total'] or 0
            
        elif tipo == 'pv':
            horas = 24
            if periodo == '48h': horas = 48
            elif periodo == '92h': horas = 92
            cursor.execute("SELECT COUNT(*) as total FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL %s HOUR)", (horas,))
            valor = cursor.fetchone()['total'] or 0
    finally:
        conn.close()
    return jsonify({'valor': valor})

# ==============================================================================
# 👥 GESTÃO DE USUÁRIOS
# ==============================================================================

@app.route('/usuarios')
@login_required
def gerenciar_usuarios():
    if session['nivel'] not in ['admin', 'tecnico']: return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome_completo, usuario, nivel_acesso, nacionalidade FROM Usuarios ORDER BY nivel_acesso")
    usuarios = cursor.fetchall()
    conn.close()
    niveis = ['admin', 'tecnico', 'enfermeiro', 'estagiario'] if session['nivel'] == 'admin' else ['tecnico', 'enfermeiro', 'estagiario']
    return render_template('gerenciar_usuarios.html', usuarios=usuarios, nivel_logado=session['nivel'], niveis_permitidos=niveis)

@app.route('/usuarios/adicionar', methods=['POST'])
@login_required
def adicionar_usuario():
    if session['nivel'] not in ['admin', 'tecnico']: return "Negado", 403
    dados = request.form
    hashed = generate_password_hash(dados['nova_senha'])
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Usuarios (nome_completo, usuario, senha, nivel_acesso, nacionalidade) VALUES (%s, %s, %s, %s, %s)",
                       (dados['nome_completo'], dados['usuario'], hashed, dados['nivel_acesso'], dados['nacionalidade']))
        conn.commit()
    except IntegrityError: flash("Login já existe!", "danger")
    finally: conn.close()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/editar/<int:user_id>', methods=['POST'])
@login_required
def editar_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico']: return "Negado", 403
    dados = request.form
    conn = get_db_connection()
    cursor = conn.cursor()
    if dados.get('nova_senha'):
        hashed = generate_password_hash(dados['nova_senha'])
        sql = "UPDATE Usuarios SET nome_completo=%s, usuario=%s, nivel_acesso=%s, nacionalidade=%s, senha=%s WHERE id=%s"
        cursor.execute(sql, (dados['nome_completo'], dados['usuario'], dados['nivel_acesso'], dados['nacionalidade'], hashed, user_id))
    else:
        sql = "UPDATE Usuarios SET nome_completo=%s, usuario=%s, nivel_acesso=%s, nacionalidade=%s WHERE id=%s"
        cursor.execute(sql, (dados['nome_completo'], dados['usuario'], dados['nivel_acesso'], dados['nacionalidade'], user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico'] or user_id == session['usuario_id']: return "Negado", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Usuarios WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('gerenciar_usuarios'))

# ==============================================================================
# 🩺 PACIENTES E PRONTUÁRIO
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

@app.route('/paciente/detalhes/<int:paciente_id>')
@login_required
def detalhes_prontuario(paciente_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    cursor.execute("SELECT * FROM ProvasDeVida WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
    provas_vida = cursor.fetchall()
    conn.close()
    return render_template('detalhes_prontuario.html', paciente=paciente, provas_vida=provas_vida)

@app.route('/prontuario')
@login_required
def prontuario():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_medicamento FROM Estoque WHERE quantidade > 0")
    medicamentos = cursor.fetchall()
    conn.close()
    return render_template('prontuario_form.html', medicamentos=medicamentos)

@app.route('/prontuario/salvar', methods=['POST'])
@login_required
def salvar_prontuario():
    dados = request.form
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO Pacientes (nome, data_nascimento, cpf, cep, endereco, bairro, data_entrada, 
             procedimento, status, usuario_internacao, prioridade_atencao) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'internado', %s, %s)"""
    cursor.execute(sql, (dados['nome_paciente'], dados['data_nascimento'], dados['cpf'], dados['cep'], 
                        dados['endereco'], dados['bairro'], dados['hora_entrada'].replace('T', ' '), 
                        dados['procedimento'], session['usuario'], dados.get('prioridade_atencao', 'verde')))
    conn.commit()
    conn.close()
    return redirect(url_for('pacientes'))

# ==============================================================================
# ❤️ PROVA DE VIDA, ALTA E ARQUIVO
# ==============================================================================

@app.route('/prova_vida/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
def prova_vida(paciente_id):
    if request.method == 'POST':
        dados = request.form
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ProvasDeVida (paciente_id, data_hora, pressao_arterial, glicose, saturacao, batimentos_cardiacos, quem_efetuou) VALUES (%s, NOW(), %s, %s, %s, %s, %s)", 
                       (paciente_id, dados['pa'], dados['glicose'], dados['sat'], dados['bpm'], session['usuario']))
        conn.commit()
        conn.close()
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id))
    return render_template('prova_vida_form.html', paciente_id=paciente_id)

@app.route('/paciente/alta_form/<int:paciente_id>')
@login_required
def alta_form(paciente_id):
    if session['nivel'] not in ['admin', 'tecnico']: return redirect(url_for('pacientes'))
    conn = get_db_connection()
    cursor = conn.cursor()
    # ADICIONADO: data_entrada para evitar o UndefinedError no Jinja2
    cursor.execute("SELECT id, nome, data_entrada FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    conn.close()
    return render_template('alta_form.html', 
                           paciente=paciente, 
                           agora=datetime.now().strftime('%Y-%m-%dT%H:%M'), 
                           usuario_logado=session['usuario'])

@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
@login_required
def dar_alta(paciente_id):
    if session['nivel'] not in ['admin', 'tecnico']: return "Negado", 403
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
# 📦 ESTOQUE
# ==============================================================================

@app.route('/estoque')
@login_required
def estoque():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Estoque ORDER BY nome_medicamento")
    itens = cursor.fetchall()
    conn.close()
    return render_template('estoque.html', itens=itens)

@app.route('/estoque/salvar', methods=['POST'])
@login_required
def salvar_estoque():
    if session['nivel'] not in ['admin', 'tecnico', 'enfermeiro']: return "Negado", 403
    dados = request.form
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """INSERT INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada, usuario_ultima_alteracao) 
                 VALUES (%s, %s, %s, NOW(), %s) ON DUPLICATE KEY UPDATE 
                 quantidade = quantidade + VALUES(quantidade), data_ultima_entrada = NOW(), 
                 usuario_ultima_alteracao = VALUES(usuario_ultima_alteracao)"""
        cursor.execute(sql, (dados['nome'].strip(), int(dados['quantidade']), dados['unidade'], session['usuario']))
        conn.commit()
    finally: conn.close()
    return redirect(url_for('estoque'))

@app.route('/estoque/editar/<int:item_id>', methods=['POST'])
@login_required
def editar_estoque(item_id):
    if session['nivel'] not in ['admin', 'tecnico']: return "Negado", 403
    dados = request.form
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """UPDATE Estoque SET nome_medicamento = %s, quantidade = %s, unidade = %s, 
                 data_ultima_entrada = NOW(), usuario_ultima_alteracao = %s WHERE id = %s"""
        cursor.execute(sql, (dados['nome_medicamento'], dados['quantidade'], dados['unidade'], session['usuario'], item_id))
        conn.commit()
    finally: conn.close()
    return redirect(url_for('estoque'))

@app.route('/conversor')
@login_required
def conversor(): return render_template('conversor.html')

@app.route('/provas_vida_geral')
@login_required
def provas_vida_geral():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Busca todas as provas de vida com o nome do paciente relacionado
    sql = """
        SELECT pv.*, p.nome as nome_paciente 
        FROM ProvasDeVida pv
        JOIN Pacientes p ON pv.paciente_id = p.id
        ORDER BY pv.data_hora DESC
    """
    cursor.execute(sql)
    historico = cursor.fetchall()
    conn.close()
    return render_template('provas_vida_geral.html', historico=historico)

if __name__ == '__main__':
    setup_database() 
    app.run(debug=True)