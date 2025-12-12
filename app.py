from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
# Importa a função setup_database para inicialização
from database import create_db_connection, setup_database 
from datetime import datetime
# Importa funções de segurança do próprio Flask (Werkzeug)
from werkzeug.security import generate_password_hash, check_password_hash
# Importa o módulo de cursores para usar DictCursor
import pymysql.cursors 
from pymysql import IntegrityError # Importa para tratar erro de usuário duplicado

# Função auxiliar para criar a conexão, usando DictCursor por padrão para facilitar
def get_db_connection(cursor_factory=pymysql.cursors.DictCursor):
    return create_db_connection(cursor_factory)

# Decorator para exigir login
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash("Você precisa estar logado para acessar esta página.", 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
# Chave secreta é OBRIGATÓRIA para usar sessões
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
    session.pop('usuario', None)
    session.pop('nivel', None)
    return redirect(url_for('login'))

# ==============================================================================
# 📊 ROTA PRINCIPAL (DASHBOARD) - AGORA COM GRÁFICOS DE PRIORIDADE
# ==============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    current_year = datetime.now().year
    
    # ESTRUTURA ATUALIZADA DO DICIONÁRIO DE DADOS
    dados_dashboard = {
        'total_internados': 0,
        'altas_ultimos_7_dias': 0,
        'baixo_estoque': 0,
        'provas_vida_ultimas_24h': 0,
        
        # NOVOS DADOS BASEADOS EM PRIORIDADE DE ATENÇÃO
        'prioridade_data': {'labels': ['Verde', 'Amarelo', 'Vermelho'], 'data': [0, 0, 0]},
        'prioridade_tendencia': [], # Dados brutos da tendência mensal
        
        'dias_data': {'labels': [], 'data': []},     
        'movimentacao_mensal': {'labels': [], 'entradas': [], 'altas': []},
        'movimentacao_anual': {'labels': [], 'entradas': [], 'altas': []},
    }
    
    if conn:
        cursor = conn.cursor() 
        
        try:
            # 1. KPIs
            cursor.execute("SELECT COUNT(*) FROM Pacientes WHERE status = 'internado'")
            dados_dashboard['total_internados'] = list(cursor.fetchone().values())[0] 
            
            cursor.execute("SELECT COUNT(*) FROM Pacientes WHERE status = 'alta' AND data_baixa >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
            dados_dashboard['altas_ultimos_7_dias'] = list(cursor.fetchone().values())[0]
            
            cursor.execute("SELECT COUNT(*) FROM Estoque WHERE quantidade < 100") 
            dados_dashboard['baixo_estoque'] = list(cursor.fetchone().values())[0]

            cursor.execute("SELECT COUNT(*) FROM ProvasDeVida WHERE data_hora >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            dados_dashboard['provas_vida_ultimas_24h'] = list(cursor.fetchone().values())[0]
            
            # 2. NOVO GRÁFICO 1: DISTRIBUIÇÃO ATUAL POR PRIORIDADE (Rosca)
            sql_prioridade = """
            SELECT 
                prioridade_atencao, 
                COUNT(*) as total 
            FROM Pacientes 
            WHERE status = 'internado' AND prioridade_atencao IS NOT NULL
            GROUP BY prioridade_atencao 
            """
            cursor.execute(sql_prioridade)
            # Normaliza as chaves para minúsculo para garantir a correspondência
            prioridades = {item['prioridade_atencao'].lower(): item['total'] for item in cursor.fetchall()}
            
            # Preenche o dicionário com os valores (usando 'verde', 'amarelo', 'vermelho' como chaves)
            dados_dashboard['prioridade_data']['data'][0] = prioridades.get('verde', 0)
            dados_dashboard['prioridade_data']['data'][1] = prioridades.get('amarelo', 0)
            dados_dashboard['prioridade_data']['data'][2] = prioridades.get('vermelho', 0)
            
            
            # 3. NOVO GRÁFICO 2: TENDÊNCIA MENSAL POR PRIORIDADE (Linha)
            sql_tendencia_prioridade = f"""
            SELECT
                MONTH(data_entrada) AS mes,
                prioridade_atencao,
                COUNT(*) AS total
            FROM Pacientes
            WHERE YEAR(data_entrada) = {current_year}
                AND prioridade_atencao IS NOT NULL
            GROUP BY mes, prioridade_atencao
            ORDER BY mes ASC
            """
            cursor.execute(sql_tendencia_prioridade)
            dados_dashboard['prioridade_tendencia'] = cursor.fetchall()
            
            
            # 4. DADOS PARA GRÁFICO DE DIAS MÉDIOS DE INTERNAÇÃO (Barras)
            sql_dias = """
            SELECT 
                nome_baixa,
                AVG(TIMESTAMPDIFF(DAY, data_entrada, data_baixa)) as media_dias 
            FROM Pacientes 
            WHERE status = 'alta' AND nome_baixa IS NOT NULL
            GROUP BY nome_baixa 
            HAVING media_dias IS NOT NULL
            ORDER BY media_dias DESC 
            LIMIT 5
            """
            cursor.execute(sql_dias)
            dias_medios = cursor.fetchall()
            
            dados_dashboard['dias_data']['labels'] = [d['nome_baixa'] for d in dias_medios]
            dados_dashboard['dias_data']['data'] = [round(float(d['media_dias']), 1) for d in dias_medios]
            
            # 5. MOVIMENTAÇÃO MENSAL (Mantido)
            sql_entradas_mensal = f"""
            SELECT MONTH(data_entrada) as mes, COUNT(*) as entradas
            FROM Pacientes
            WHERE YEAR(data_entrada) = {current_year}
            GROUP BY mes
            """
            cursor.execute(sql_entradas_mensal)
            entradas_mensal = {item['mes']: item['entradas'] for item in cursor.fetchall()}

            sql_altas_mensal = f"""
            SELECT MONTH(data_baixa) as mes, COUNT(*) as altas
            FROM Pacientes
            WHERE YEAR(data_baixa) = {current_year} AND status = 'alta'
            GROUP BY mes
            """
            cursor.execute(sql_altas_mensal)
            altas_mensal = {item['mes']: item['altas'] for item in cursor.fetchall()}

            nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            
            for mes_num in range(1, 13):
                dados_dashboard['movimentacao_mensal']['labels'].append(nomes_meses[mes_num - 1])
                dados_dashboard['movimentacao_mensal']['entradas'].append(entradas_mensal.get(mes_num, 0))
                dados_dashboard['movimentacao_mensal']['altas'].append(altas_mensal.get(mes_num, 0))


            # 6. MOVIMENTAÇÃO ANUAL (Mantido)
            sql_movimentacao_anual = f"""
            SELECT 
                YEAR(data_entrada) as ano, 
                SUM(CASE WHEN data_entrada IS NOT NULL THEN 1 ELSE 0 END) as entradas,
                SUM(CASE WHEN data_baixa IS NOT NULL THEN 1 ELSE 0 END) as altas
            FROM Pacientes
            WHERE YEAR(data_entrada) >= {current_year - 4} OR YEAR(data_baixa) >= {current_year - 4}
            GROUP BY ano
            ORDER BY ano ASC
            """
            cursor.execute(sql_movimentacao_anual)
            mov_anual = cursor.fetchall()

            dados_anual = {item['ano']: {'entradas': item['entradas'], 'altas': item['altas']} for item in mov_anual}
            
            for ano in range(current_year - 4, current_year + 1):
                if ano in dados_anual:
                    dados_dashboard['movimentacao_anual']['labels'].append(str(ano))
                    dados_dashboard['movimentacao_anual']['entradas'].append(dados_anual[ano]['entradas'])
                    dados_dashboard['movimentacao_anual']['altas'].append(dados_anual[ano]['altas'])
                else:
                    dados_dashboard['movimentacao_anual']['labels'].append(str(ano))
                    dados_dashboard['movimentacao_anual']['entradas'].append(0)
                    dados_dashboard['movimentacao_anual']['altas'].append(0)

            
        except Exception as e:
            conn.rollback()
            print(f"Erro CRÍTICO ao buscar dados do dashboard: {e}")
            # Resetamos todos os dados para evitar quebras
            dados_dashboard['prioridade_data'] = {'labels': ['Verde', 'Amarelo', 'Vermelho'], 'data': [0, 0, 0]}
            dados_dashboard['dias_data'] = {'labels': [], 'data': []}
            dados_dashboard['movimentacao_mensal'] = {'labels': [], 'entradas': [], 'altas': []}
            dados_dashboard['movimentacao_anual'] = {'labels': [], 'entradas': [], 'altas': []}
            dados_dashboard['prioridade_tendencia'] = []
        finally:
            if conn:
                cursor.close()
                conn.close()
            
    return render_template(
        'dashboard.html', 
        usuario=session['usuario'], 
        nivel=session['nivel'], 
        dados=dados_dashboard,
        mensagem=request.args.get('mensagem')
    )

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
        
    return render_template(
        'prontuario_form.html', 
        usuario=session['usuario'],
        medicamentos=medicamentos
    )

@app.route('/prontuario/salvar', methods=['POST'])
@login_required
def salvar_prontuario():
    dados = request.form
    usuario_internacao = session.get('usuario') 
    
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None:
        return "Erro de conexão com o banco de dados.", 500
        
    cursor = conn.cursor()

    try:
        # **ATUALIZADO:** Incluindo cid_10, observacoes_entrada e prioridade_atencao
        sql_paciente = """
        INSERT INTO Pacientes (nome, data_nascimento, cep, endereco, bairro, data_entrada, procedimento, 
                               status, usuario_internacao, cid_10, observacoes_entrada, prioridade_atencao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'internado', %s, %s, %s, %s)
        """
        try:
            data_nascimento_mysql = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        except ValueError:
            data_nascimento_mysql = None 

        data_entrada_mysql = dados['hora_entrada'].replace('T', ' ')
        
        # Novos dados
        cid_10_val = dados.get('cid_10', '').strip()
        observacoes_val = dados.get('observacoes_entrada', '').strip()
        prioridade_val = dados.get('prioridade_atencao', 'verde').lower() # Novo campo (garante minúsculo)
        
        cursor.execute(sql_paciente, (
            dados['nome_paciente'], 
            data_nascimento_mysql, 
            dados['cep'], 
            f"{dados['endereco']}, {dados['numero']}",
            dados['bairro'], 
            data_entrada_mysql,
            dados['procedimento'],
            usuario_internacao,
            cid_10_val,
            observacoes_val,
            prioridade_val 
        ))
        
        paciente_id = cursor.lastrowid

        # ... (restante da lógica de medicamento - Mantido)
        medicamento = dados.get('medicamento_entrada')
        medicamento_nome = None
        
        if medicamento and medicamento != 'outro':
            medicamento_nome = medicamento
        elif medicamento == 'outro' and dados.get('outro_medicamento_nome'):
            medicamento_nome = dados['outro_medicamento_nome']
            cursor.execute("INSERT IGNORE INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, 0, 'UN', NOW())", (medicamento_nome,))


        if medicamento_nome:
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
# 👥 MÓDULO PACIENTES (LISTA DE INTERNADOS)
# ==============================================================================

@app.route('/pacientes')
@login_required
def pacientes():
    conn = get_db_connection()
    pacientes_internados = []
    if conn:
        try:
            # Seleciona também a prioridade para exibição/triagem
            sql = "SELECT id, nome, data_nascimento, data_entrada, prioridade_atencao FROM Pacientes WHERE status = 'internado' ORDER BY nome"
            cursor = conn.cursor()
            cursor.execute(sql)
            pacientes_internados = cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(f"Erro ao buscar pacientes: {e}")
        finally:
            conn.close()
            
    return render_template('pacientes.html', pacientes=pacientes_internados)

# ------------------------------------------------------------------------------
# 📑 ROTA DE DETALHES UNIFICADA (DETALHES_PRONTUARIO) - RENOMEADA E PADRONIZADA
# ------------------------------------------------------------------------------

@app.route('/paciente/detalhes/<int:paciente_id>')
@login_required
def detalhes_prontuario(paciente_id):
    conn = get_db_connection()
    paciente = None
    provas_vida = []
    medicamentos_admin = []
    
    if conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM Pacientes WHERE id = %s", (paciente_id,))
            paciente = cursor.fetchone()
            
            cursor.execute("SELECT * FROM ProvasDeVida WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
            provas_vida = cursor.fetchall()
            
            cursor.execute("SELECT * FROM AdministracaoMedicamentos WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
            medicamentos_admin = cursor.fetchall()
        
        except Exception as e:
            print(f"Erro ao buscar detalhes do paciente: {e}")
        finally:
            cursor.close()
            conn.close()
            
    if not paciente:
        flash("Paciente não encontrado.", 'danger')
        return redirect(url_for('pacientes'))
        
    return render_template(
        'detalhes_prontuario.html', 
        paciente=paciente, 
        provas_vida=provas_vida, 
        medicamentos_admin=medicamentos_admin
    )

# ==============================================================================
# ❤️ MÓDULO PROVA DE VIDA
# ==============================================================================

@app.route('/prova_vida/<int:paciente_id>', methods=('GET', 'POST'))
@login_required
def prova_vida(paciente_id):
    conn = get_db_connection()
    paciente = None
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM Pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        cursor.close()
        conn.close()
        
    if not paciente:
        flash(f"Paciente com ID {paciente_id} não encontrado.", 'danger')
        return redirect(url_for('pacientes'))

    if request.method == 'GET':
        agora = datetime.now().strftime('%Y-%m-%dT%H:%M')
        
        return render_template(
            'prova_vida_form.html', 
            paciente=paciente,
            agora=agora,
            usuario_logado=session['usuario']
        )
    
    elif request.method == 'POST':
        dados = request.form
        quem_efetuou_val = session.get('usuario', 'Desconhecido') 
        
        conn = get_db_connection(pymysql.cursors.Cursor) 
        if conn is None:
            return "Erro de conexão com o banco de dados.", 500
            
        cursor = conn.cursor()
        
        try:
            sql = """
            INSERT INTO ProvasDeVida 
            (paciente_id, data_hora, pressao_arterial, glicose, saturacao, batimentos_cardiacos, quem_efetuou, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            data_pv = dados['data_pv']
            hora_pv = dados['hora_pv']
            data_hora_mysql = f"{data_pv} {hora_pv}:00"
            
            glicose_val = dados['glicose'] if dados['glicose'] else None
            saturacao_val = dados['saturacao'] if dados['saturacao'] else None
            batimentos_val = dados['batimentos_cardiacos'] if dados['batimentos_cardiacos'] else None
            
            cursor.execute(sql, (
                paciente_id,
                data_hora_mysql,
                dados['pressao_arterial'], 
                glicose_val, 
                saturacao_val,
                batimentos_val,
                quem_efetuou_val,
                dados['observacoes']
            ))
            
            conn.commit()
            flash('Prova de vida registrada com sucesso!', 'success')
            return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
            
        except Exception as e:
            conn.rollback()
            print(f"Erro ao salvar Prova de Vida: {e}")
            flash(f"Erro interno ao salvar os dados: {e}", 'danger')
            return redirect(url_for('prova_vida', paciente_id=paciente_id))
        finally:
            cursor.close()
            conn.close()

@app.route('/prova_vida')
@login_required
def prova_vida_antiga():
    flash("Selecione um paciente internado para registrar a Prova de Vida.", 'info')
    return redirect(url_for('pacientes'))


# ==============================================================================
# 🛒 MÓDULO ESTOQUE
# ==============================================================================

@app.route('/estoque')
@login_required
def estoque():
    if session['nivel'] not in ['admin', 'tecnico']:
        flash("Acesso Negado: Permissão restrita a Admin e Técnico.", 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    itens_estoque = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Estoque ORDER BY nome_medicamento")
        itens_estoque = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('estoque.html', itens=itens_estoque, nivel=session['nivel'])

@app.route('/estoque/salvar', methods=['POST'])
@login_required
def salvar_estoque():
    if session.get('nivel') not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403

    dados = request.form
    nome = dados['nome'].strip()
    
    try:
        quantidade = int(dados['quantidade'])
    except ValueError:
        flash("Quantidade deve ser um número inteiro válido.", 'danger')
        return redirect(url_for('estoque'))
        
    unidade = dados['unidade']
    
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()
    
    try:
        sql_update = "UPDATE Estoque SET quantidade = quantidade + %s, unidade = %s, data_ultima_entrada = NOW() WHERE nome_medicamento = %s"
        cursor.execute(sql_update, (quantidade, unidade, nome))
        
        if cursor.rowcount == 0:
            sql_insert = "INSERT INTO Estoque (nome_medicamento, quantidade, unidade, data_ultima_entrada) VALUES (%s, %s, %s, NOW())"
            cursor.execute(sql_insert, (nome, quantidade, unidade))
            
        conn.commit()
        flash("Estoque atualizado com sucesso.", 'success')
        return redirect(url_for('estoque'))
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar estoque: {e}")
        flash(f"Erro: {e}", 'danger')
        return redirect(url_for('estoque'))
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# ➗ MÓDULO CONVERSOR
# ==============================================================================

@app.route('/conversor')
@login_required
def conversor():
    return render_template('conversor.html')


# ==============================================================================
# 🗄️ MÓDULO ARQUIVO (ALTAS)
# ==============================================================================

@app.route('/paciente/alta_form/<int:paciente_id>')
@login_required
def alta_form(paciente_id):
    if session.get('nivel') not in ['admin', 'tecnico']:
        flash("Acesso Negado: Apenas Admin/Técnicos podem dar alta.", 'danger')
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nome, data_entrada, status FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    cursor.close()
    conn.close()

    if not paciente or paciente['status'] != 'internado':
        flash("Paciente não encontrado ou já recebeu alta.", 'danger')
        return redirect(url_for('pacientes'))

    agora = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    return render_template(
        'alta_form.html',
        paciente=paciente,
        agora=agora,
        usuario_logado=session['usuario']
    )
    
@app.route('/arquivo')
@login_required
def arquivo():
    conn = get_db_connection()
    pacientes_altas = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, data_entrada, data_baixa, nome_baixa, procedimento, prioridade_atencao FROM Pacientes WHERE status = 'alta' ORDER BY data_baixa DESC")
        pacientes_altas = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('arquivo.html', pacientes=pacientes_altas, mensagem=request.args.get('mensagem'))
    
@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
@login_required
def dar_alta(paciente_id):
    if session.get('nivel') not in ['admin', 'tecnico']:
        flash("Acesso Negado: Permissão restrita a Admin e Técnico.", 'danger')
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
    
    dados = request.form
    data_hora_alta = dados['data_hora_alta']
    
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()
    
    try:
        data_baixa_mysql = f"{data_hora_alta.replace('T', ' ')}:00"

        usuario_baixa = session.get('usuario', 'N/A')
        
        sql = "UPDATE Pacientes SET status = 'alta', data_baixa = %s, nome_baixa = %s WHERE id = %s AND status = 'internado'"
        cursor.execute(sql, (data_baixa_mysql, usuario_baixa, paciente_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            flash(f'Alta registrada por {usuario_baixa} em {data_baixa_mysql}!', 'success')
            return redirect(url_for('arquivo'))
        else:
            flash("Erro: Paciente não encontrado ou já tinha alta.", 'danger')
            return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id))
            
    except Exception as e:
        conn.rollback()
        print(f"Erro ao registrar alta: {e}")
        flash(f"Erro interno: {e}", 'danger')
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id))
    finally:
        cursor.close()
        conn.close()


# ==============================================================================
# 👥 MÓDULO GERENCIAMENTO DE USUÁRIOS (CORRIGIDO)
# ==============================================================================

@app.route('/usuarios')
@login_required
def gerenciar_usuarios():
    if session['nivel'] not in ['admin', 'tecnico']:
        flash("Acesso Negado: Permissão restrita a Administradores e Técnicos.", 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    usuarios = []
    if conn:
        cursor = conn.cursor()
        
        try:
            sql_base = "SELECT id, nome_completo, usuario, data_nascimento, nivel_acesso, nacionalidade FROM Usuarios"
            
            if session['nivel'] == 'tecnico':
                sql = f"{sql_base} WHERE nivel_acesso = 'enfermeiro' ORDER BY usuario"
            else:
                sql = f"{sql_base} ORDER BY nivel_acesso DESC, usuario"
                
            cursor.execute(sql)
            usuarios = cursor.fetchall()
            
        except Exception as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
            cursor.close()
            conn.close()
            
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
@login_required
def adicionar_usuario():
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403

    dados = request.form
    
    nome_completo = dados['nome_completo'].strip()
    data_nascimento_form = dados['data_nascimento']
    nacionalidade = dados['nacionalidade'].strip()
    
    novo_usuario = dados['usuario'].strip()
    nova_senha = dados['nova_senha']
    nivel_novo = dados['nivel_acesso']

    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()

    if session['nivel'] == 'tecnico' and nivel_novo != 'enfermeiro':
        flash("Acesso Negado: Técnicos só podem adicionar Enfermeiros.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))
    
    if session['nivel'] == 'admin' and nivel_novo == 'tecnico':
        cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE nivel_acesso = 'tecnico'")
        num_tecnicos = cursor.fetchone()[0]
        if num_tecnicos >= 5:
            flash("Limite máximo de 5 Técnicos atingido. Ação não permitida.", 'danger')
            conn.close()
            return redirect(url_for('gerenciar_usuarios'))

    try:
        data_nascimento_mysql = datetime.strptime(data_nascimento_form, '%Y-%m-%d').date()
    except ValueError:
        flash("Erro: Data de nascimento inválida.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))
        
    try:
        hashed_password = generate_password_hash(nova_senha) 
        
        sql = """
        INSERT INTO Usuarios (nome_completo, usuario, senha, data_nascimento, nivel_acesso, nacionalidade) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            nome_completo,
            novo_usuario,
            hashed_password,
            data_nascimento_mysql,
            nivel_novo,
            nacionalidade
        ))
        conn.commit()
        flash(f"Usuário {novo_usuario} adicionado com sucesso!", 'success')
        return redirect(url_for('gerenciar_usuarios'))
        
    except IntegrityError:
        conn.rollback()
        flash("Erro: O nome de usuário já existe.", 'danger')
        return redirect(url_for('gerenciar_usuarios'))
    except Exception as e:
        conn.rollback()
        print(f"Erro ao adicionar usuário: {e}")
        flash(f"Erro: Não foi possível adicionar o usuário. {e}", 'danger')
        return redirect(url_for('gerenciar_usuarios'))
    finally:
        cursor.close()
        conn.close()
        
@app.route('/usuarios/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    if session['nivel'] not in ['admin', 'tecnico']:
        flash("Acesso Negado.", 'danger')
        return redirect(url_for('gerenciar_usuarios'))
        
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT nivel_acesso FROM Usuarios WHERE id = %s", (user_id,))
    user_to_delete = cursor.fetchone()
    
    if not user_to_delete:
        cursor.close()
        conn.close()
        flash("Usuário não encontrado.", 'warning')
        return redirect(url_for('gerenciar_usuarios'))

    nivel_deletado = user_to_delete['nivel_acesso']
    cursor.close()
    cursor = conn.cursor() 

    if session['nivel'] == 'tecnico' and nivel_deletado != 'enfermeiro':
        flash("Acesso Negado: Técnicos só podem excluir usuários de nível Enfermeiro.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))
    
    if nivel_deletado == 'admin':
        flash("Acesso Negado: Não é permitido excluir o Administrador por esta via.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))

    try:
        sql = "DELETE FROM Usuarios WHERE id = %s"
        cursor.execute(sql, (user_id,))
        conn.commit()
        flash("Usuário excluído com sucesso.", 'success')
        return redirect(url_for('gerenciar_usuarios'))
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir usuário: {e}")
        flash(f"Erro ao excluir usuário: {e}", 'danger')
        return redirect(url_for('gerenciar_usuarios'))
    finally:
        cursor.close()
        conn.close()


# ==============================================================================
# 🚀 INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    setup_database() 
    app.run(debug=True)