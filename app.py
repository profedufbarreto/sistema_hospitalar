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
        
        conn = get_db_connection()
        if conn is None:
            return render_template('login.html', erro='Erro de conexão com o banco de dados.')
            
        cursor = conn.cursor() 
        sql = "SELECT * FROM Usuarios WHERE usuario = %s"
        cursor.execute(sql, (usuario,))
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
# 📊 ROTA PRINCIPAL (DASHBOARD COM OS 5 GRÁFICOS)
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
        'movimentacao_mensal': {'labels': [], 'entradas': [], 'altas': []},
        'movimentacao_anual': {'labels': [], 'entradas': [], 'altas': []},
    }
    
    if conn:
        cursor = conn.cursor() 
        try:
            # 1. KPIs Iniciais
            cursor.execute("SELECT COUNT(*) as total FROM Pacientes WHERE status = 'internado'")
            dados_dashboard['total_internados'] = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM Pacientes WHERE status = 'alta' AND data_baixa >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
            dados_dashboard['altas_ultimos_7_dias'] = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM Estoque WHERE quantidade < 100") 
            dados_dashboard['baixo_estoque'] = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            dados_dashboard['provas_vida_ultimas_24h'] = cursor.fetchone()['total']
            
            # 2. Distribuição por Prioridade (Gráfico de Rosca)
            sql_prioridade = "SELECT prioridade_atencao, COUNT(*) as total FROM Pacientes WHERE status = 'internado' AND prioridade_atencao IS NOT NULL GROUP BY prioridade_atencao"
            cursor.execute(sql_prioridade)
            for item in cursor.fetchall():
                p = item['prioridade_atencao'].lower()
                if p == 'verde': dados_dashboard['prioridade_data']['data'][0] = item['total']
                elif p == 'amarelo': dados_dashboard['prioridade_data']['data'][1] = item['total']
                elif p == 'vermelho': dados_dashboard['prioridade_data']['data'][2] = item['total']
            
            # 3. Tendência de Prioridade (Gráfico de Linha Mensal)
            sql_tendencia = f"SELECT MONTH(data_entrada) AS mes, prioridade_atencao, COUNT(*) AS total FROM Pacientes WHERE YEAR(data_entrada) = {current_year} AND prioridade_atencao IS NOT NULL GROUP BY mes, prioridade_atencao"
            cursor.execute(sql_tendencia)
            for r in cursor.fetchall():
                m_idx = r['mes'] - 1
                pri = r['prioridade_atencao'].lower()
                if pri in dados_dashboard['prioridade_tendencia']:
                    dados_dashboard['prioridade_tendencia'][pri][m_idx] = r['total']
            
            # 4. Média de Dias por Profissional (Gráfico de Barras Horizontal)
            sql_dias = "SELECT nome_baixa, AVG(TIMESTAMPDIFF(DAY, data_entrada, data_baixa)) as media FROM Pacientes WHERE status = 'alta' AND nome_baixa IS NOT NULL GROUP BY nome_baixa ORDER BY media DESC LIMIT 5"
            cursor.execute(sql_dias)
            res_dias = cursor.fetchall()
            dados_dashboard['dias_data']['labels'] = [d['nome_baixa'] for d in res_dias]
            dados_dashboard['dias_data']['data'] = [round(float(d['media']), 1) for d in res_dias]
            
            # 5. Movimentação Mensal (Entradas vs Altas)
            nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            dados_dashboard['movimentacao_mensal']['labels'] = nomes_meses
            
            cursor.execute(f"SELECT MONTH(data_entrada) as mes, COUNT(*) as c FROM Pacientes WHERE YEAR(data_entrada) = {current_year} GROUP BY mes")
            ent_m = {r['mes']: r['c'] for r in cursor.fetchall()}
            cursor.execute(f"SELECT MONTH(data_baixa) as mes, COUNT(*) as c FROM Pacientes WHERE YEAR(data_baixa) = {current_year} AND status = 'alta' GROUP BY mes")
            alt_m = {r['mes']: r['c'] for r in cursor.fetchall()}
            
            dados_dashboard['movimentacao_mensal']['entradas'] = [ent_m.get(i, 0) for i in range(1, 13)]
            dados_dashboard['movimentacao_mensal']['altas'] = [alt_m.get(i, 0) for i in range(1, 13)]

            # 6. Movimentação Anual (Histórico)
            cursor.execute("SELECT YEAR(data_entrada) as ano, COUNT(*) as c FROM Pacientes GROUP BY ano ORDER BY ano ASC LIMIT 5")
            ent_a = {r['ano']: r['c'] for r in cursor.fetchall()}
            cursor.execute("SELECT YEAR(data_baixa) as ano, COUNT(*) as c FROM Pacientes WHERE status = 'alta' GROUP BY ano ORDER BY ano ASC LIMIT 5")
            alt_a = {r['ano']: r['c'] for r in cursor.fetchall()}
            
            anos = sorted(list(set(list(ent_a.keys()) + list(alt_a.keys()))))
            dados_dashboard['movimentacao_anual']['labels'] = [str(a) for a in anos]
            dados_dashboard['movimentacao_anual']['entradas'] = [ent_a.get(a, 0) for a in anos]
            dados_dashboard['movimentacao_anual']['altas'] = [alt_a.get(a, 0) for a in anos]

        except Exception as e:
            conn.rollback()
            print(f"Erro no dashboard: {e}")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('dashboard.html', usuario=session['usuario'], nivel=session['nivel'], dados=dados_dashboard)

# --- ROTAS DE API PARA FILTROS DINÂMICOS (KPIs) ---

@app.route('/api/kpi/altas/<string:periodo>')
@login_required
def api_kpi_altas(periodo):
    intervalos = {'7d': 7, '15d': 15, '1m': 30, '3m': 90, '6m': 180, '1y': 365}
    dias = intervalos.get(periodo, 7)
    conn = get_db_connection()
    cursor = conn.cursor()
    # SQL Corrigido: CURDATE() garante que busque a partir de hoje retroativamente
    sql = "SELECT COUNT(*) as total FROM Pacientes WHERE status = 'alta' AND data_baixa >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
    cursor.execute(sql, (dias,))
    total = cursor.fetchone()['total']
    conn.close()
    return jsonify({'valor': total if total else 0})

@app.route('/api/kpi/pv/<string:periodo>')
@login_required
def api_kpi_pv(periodo):
    intervalos = {'24h': 24, '48h': 48, '96h': 96, '7d': 168}
    horas = intervalos.get(periodo, 24)
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "SELECT COUNT(*) as total FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL %s HOUR)"
    cursor.execute(sql, (horas,))
    total = cursor.fetchone()['total']
    conn.close()
    return jsonify({'valor': total if total else 0})

# ==============================================================================
# 📝 MÓDULO PRONTUÁRIO (NOVA INTERNAÇÃO)
# ==============================================================================

@app.route('/prontuario')
@login_required
def prontuario():
    conn = get_db_connection()
    medicamentos = []
    if conn:
        cursor = conn.cursor() 
        cursor.execute("SELECT nome_medicamento FROM Estoque WHERE quantidade > 0 ORDER BY nome_medicamento")
        medicamentos = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('prontuario_form.html', usuario=session['usuario'], medicamentos=medicamentos)

@app.route('/prontuario/salvar', methods=['POST'])
@login_required
def salvar_prontuario():
    dados = request.form
    usuario_internacao = session.get('usuario') 
    conn = get_db_connection(pymysql.cursors.Cursor) 
    cursor = conn.cursor()

    try:
        sql_paciente = """
        INSERT INTO Pacientes (nome, data_nascimento, cpf, cep, endereco, bairro, data_entrada, procedimento, 
                               status, usuario_internacao, cid_10, observacoes_entrada, prioridade_atencao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'internado', %s, %s, %s, %s)
        """
        data_nascimento_mysql = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date() if dados['data_nascimento'] else None
        data_entrada_mysql = dados['hora_entrada'].replace('T', ' ')
        
        cursor.execute(sql_paciente, (
            dados['nome_paciente'], data_nascimento_mysql, dados.get('cpf', '').replace('.', '').replace('-', '').strip(),
            dados['cep'], f"{dados['endereco']}, {dados['numero']}", dados['bairro'], data_entrada_mysql,
            dados['procedimento'], usuario_internacao, dados.get('cid_10', '').strip(), 
            dados.get('observacoes_entrada', '').strip(), dados.get('prioridade_atencao', 'verde').lower()
        ))
        
        paciente_id = cursor.lastrowid
        medicamento_nomes = request.form.getlist('medicamento_entrada[]')
        doses = request.form.getlist('dose[]')
        nomes_outros = request.form.getlist('outro_medicamento_nome[]')
        outro_index = 0
        
        for i in range(len(medicamento_nomes)):
            med_selecionado = medicamento_nomes[i]
            if not med_selecionado: continue
            
            medicamento_nome = med_selecionado
            if med_selecionado == 'outro':
                medicamento_nome = nomes_outros[outro_index].strip()
                outro_index += 1
                cursor.execute("INSERT IGNORE INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, 0, 'UN', NOW())", (medicamento_nome,))
            
            dose = float(doses[i]) if doses[i] else 0.0
            se_necessario_val = dados.get(f'se_necessario_{i}', '0')
            
            cursor.execute("INSERT INTO AdministracaoMedicamentos (paciente_id, medicamento_nome, quantidade_administrada, se_necessario, data_hora) VALUES (%s, %s, %s, %s, %s)",
                           (paciente_id, medicamento_nome, dose, se_necessario_val, data_entrada_mysql))
            
            if dose > 0:
                cursor.execute("UPDATE Estoque SET quantidade = GREATEST(quantidade - %s, 0) WHERE nome_medicamento = %s", (dose, medicamento_nome))

        conn.commit()
        return redirect(url_for('dashboard', mensagem='Prontuário salvo com sucesso!'))
    except Exception as e:
        conn.rollback()
        return f"Erro: {e}", 500
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# 👥 MÓDULO PACIENTES E DETALHES
# ==============================================================================

@app.route('/pacientes')
@login_required
def pacientes():
    conn = get_db_connection()
    pacientes_internados = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, data_nascimento, data_entrada, prioridade_atencao FROM Pacientes WHERE status = 'internado' ORDER BY nome")
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
    cursor.execute("SELECT * FROM AdministracaoMedicamentos WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
    medicamentos_admin = cursor.fetchall()
    conn.close()
    return render_template('detalhes_prontuario.html', paciente=paciente, provas_vida=provas_vida, medicamentos_admin=medicamentos_admin)

# ==============================================================================
# ❤️ MÓDULO PROVA DE VIDA
# ==============================================================================

@app.route('/prova_vida/<int:paciente_id>', methods=('GET', 'POST'))
@login_required
def prova_vida(paciente_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    conn.close()
    
    if request.method == 'POST':
        dados = request.form
        conn = get_db_connection(pymysql.cursors.Cursor) 
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO ProvasDeVida (paciente_id, data_hora, pressao_arterial, glicose, saturacao, batimentos_cardiacos, quem_efetuou, observacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (paciente_id, f"{dados['data_pv']} {dados['hora_pv']}:00", dados['pressao_arterial'], dados['glicose'] or None, dados['saturacao'] or None, dados['batimentos_cardiacos'] or None, session['usuario'], dados['observacoes']))
            conn.commit()
            flash('Prova de vida registrada!', 'success')
            return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id))
        except Exception as e:
            conn.rollback()
            flash(f"Erro: {e}", 'danger')
        finally:
            conn.close()
    
    return render_template('prova_vida_form.html', paciente=paciente, agora=datetime.now().strftime('%Y-%m-%dT%H:%M'), usuario_logado=session['usuario'])

# ==============================================================================
# 🛒 MÓDULO ESTOQUE E CONVERSOR
# ==============================================================================

@app.route('/estoque')
@login_required
def estoque():
    if session['nivel'] not in ['admin', 'enfermeiro']:
        flash("Acesso Negado: Estagiários não gerenciam estoque.", 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Estoque ORDER BY nome_medicamento")
    itens = cursor.fetchall()
    conn.close()
    return render_template('estoque.html', itens=itens, nivel=session['nivel'])

@app.route('/estoque/salvar', methods=['POST'])
@login_required
def salvar_estoque():
    if session.get('nivel') not in ['admin', 'enfermeiro']:
        return "Acesso Negado.", 403
    
    dados = request.form
    conn = get_db_connection(pymysql.cursors.Cursor) 
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE quantidade = quantidade + VALUES(quantidade), data_ultima_entrada = NOW()"
        cursor.execute(sql, (dados['nome'].strip(), int(dados['quantidade']), dados['unidade']))
        conn.commit()
        flash("Estoque atualizado.", 'success')
    finally:
        conn.close()
    return redirect(url_for('estoque'))

@app.route('/conversor')
@login_required
def conversor():
    return render_template('conversor.html')

# ==============================================================================
# 🗄️ MÓDULO ALTA E ARQUIVO
# ==============================================================================

@app.route('/paciente/alta_form/<int:paciente_id>')
@login_required
def alta_form(paciente_id):
    if session.get('nivel') not in ['admin', 'enfermeiro']:
        flash("Acesso Negado: Estagiários não podem dar alta.", 'danger')
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, data_entrada, status FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    conn.close()
    return render_template('alta_form.html', paciente=paciente, agora=datetime.now().strftime('%Y-%m-%dT%H:%M'), usuario_logado=session['usuario'])

@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
@login_required
def dar_alta(paciente_id):
    if session.get('nivel') not in ['admin', 'enfermeiro']:
        flash("Acesso Negado: Apenas Enfermeiros e Admins podem realizar esta ação.", 'danger')
        return redirect(url_for('dashboard'))
    
    data_baixa = f"{request.form['data_hora_alta'].replace('T', ' ')}:00"
    conn = get_db_connection(pymysql.cursors.Cursor) 
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Pacientes SET status = 'alta', data_baixa = %s, nome_baixa = %s WHERE id = %s", (data_baixa, session['usuario'], paciente_id))
        conn.commit()
        flash('Alta registrada!', 'success')
    finally:
        conn.close()
    return redirect(url_for('arquivo'))

@app.route('/arquivo')
@login_required
def arquivo():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, data_entrada, data_baixa, nome_baixa, procedimento, prioridade_atencao FROM Pacientes WHERE status = 'alta' ORDER BY data_baixa DESC")
    pacientes = cursor.fetchall()
    conn.close()
    return render_template('arquivo.html', pacientes=pacientes)

# ==============================================================================
# 👥 MÓDULO GERENCIAMENTO DE USUÁRIOS
# ==============================================================================

@app.route('/usuarios')
@login_required
def gerenciar_usuarios():
    if session['nivel'] not in ['admin', 'enfermeiro']:
        flash("Acesso Negado.", 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    if session['nivel'] == 'enfermeiro':
        cursor.execute("SELECT * FROM Usuarios WHERE nivel_acesso = 'estagiario'")
    else:
        cursor.execute("SELECT * FROM Usuarios ORDER BY nivel_acesso")
    usuarios = cursor.fetchall()
    conn.close()
    niveis_permitidos = ['enfermeiro', 'estagiario'] if session['nivel'] == 'admin' else ['estagiario']
    return render_template('gerenciar_usuarios.html', usuarios=usuarios, nivel_logado=session['nivel'], niveis_permitidos=niveis_permitidos)

@app.route('/usuarios/adicionar', methods=['POST'])
@login_required
def adicionar_usuario():
    if session['nivel'] not in ['admin', 'enfermeiro']: return "Acesso Negado.", 403
    dados = request.form
    hashed_password = generate_password_hash(dados['nova_senha'])
    conn = get_db_connection(pymysql.cursors.Cursor) 
    cursor = conn.cursor()
    if session['nivel'] == 'admin' and dados['nivel_acesso'] == 'enfermeiro':
        cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE nivel_acesso = 'enfermeiro'")
        if cursor.fetchone()[0] >= 5:
            flash("Limite de 5 Enfermeiros atingido.", 'danger')
            return redirect(url_for('gerenciar_usuarios'))
    try:
        sql = "INSERT INTO Usuarios (nome_completo, usuario, senha, data_nascimento, nivel_acesso, nacionalidade) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (dados['nome_completo'], dados['usuario'], hashed_password, dados['data_nascimento'], dados['nivel_acesso'], dados['nacionalidade']))
        conn.commit()
        flash("Usuário adicionado!", 'success')
    except IntegrityError:
        flash("Usuário já existe.", 'danger')
    finally:
        conn.close()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    if session['nivel'] not in ['admin', 'enfermeiro']: return "Acesso Negado.", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nivel_acesso FROM Usuarios WHERE id = %s", (user_id,))
    alvo = cursor.fetchone()
    permitido = False
    if session['nivel'] == 'admin' and alvo['nivel_acesso'] != 'admin': permitido = True
    elif session['nivel'] == 'enfermeiro' and alvo['nivel_acesso'] == 'estagiario': permitido = True
    if permitido:
        cursor.execute("DELETE FROM Usuarios WHERE id = %s", (user_id,))
        conn.commit()
        flash("Usuário removido.", 'success')
    else:
        flash("Sem permissão para excluir este nível.", 'danger')
    conn.close()
    return redirect(url_for('gerenciar_usuarios'))

# ==============================================================================
# 🚀 INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    setup_database() 
    app.run(debug=True)