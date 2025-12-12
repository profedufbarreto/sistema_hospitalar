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
# Assumimos que create_db_connection (em database.py) aceita o argumento cursor_factory
def get_db_connection(cursor_factory=pymysql.cursors.DictCursor):
    # 'create_db_connection' deve ser implementada para aceitar o cursor_factory
    # Aqui, garantimos que DictCursor é o padrão, a menos que seja sobrescrito.
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
        
        # CORRIGIDO: Usando get_db_connection() para garantir DictCursor
        conn = get_db_connection()
        if conn is None:
            return render_template('login.html', erro='Erro de conexão com o banco de dados.')
            
        cursor = conn.cursor() 
        
        # 1. BUSCA O USUÁRIO PELO NOME
        sql = "SELECT * FROM Usuarios WHERE usuario = %s"
        cursor.execute(sql, (usuario,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['senha'], senha):
            # 2. CHECA O HASH DA SENHA E DEFINE A SESSÃO
            session['usuario'] = user['usuario']
            session['nivel'] = user['nivel_acesso']
            # Armazena o ID do usuário na sessão para referência futura, se necessário
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
# 📊 ROTA PRINCIPAL (DASHBOARD) - AGORA COM DADOS PARA GRÁFICOS
# ==============================================================================

@app.route('/dashboard')
@login_required # Garante que só usuários logados acessem
def dashboard():
    conn = get_db_connection()
    current_year = datetime.now().year # Obtém o ano atual
    
    dados_dashboard = {
        'total_internados': 0,
        'altas_ultimos_7_dias': 0,
        'baixo_estoque': 0,
        'provas_vida_ultimas_24h': 0,
        'motivos_data': {'labels': [], 'data': []}, 
        'dias_data': {'labels': [], 'data': []},     
        # NOVOS DADOS TEMPORAIS:
        'movimentacao_mensal': {'labels': [], 'entradas': [], 'altas': []},
        'movimentacao_anual': {'labels': [], 'entradas': [], 'altas': []}
    }
    
    if conn:
        # Usa o cursor padrão (DictCursor) da get_db_connection
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
            
            # 2. DADOS PARA GRÁFICO DE MOTIVOS (Rosca)
            sql_motivos = """
            SELECT 
                procedimento, 
                COUNT(*) as total 
            FROM Pacientes 
            GROUP BY procedimento 
            ORDER BY total DESC 
            LIMIT 5
            """
            cursor.execute(sql_motivos)
            motivos = cursor.fetchall()
            
            # Prepara os dados para o JS: Trunca labels longas
            dados_dashboard['motivos_data']['labels'] = [m['procedimento'][:20] + '...' if len(m['procedimento']) > 20 else m['procedimento'] for m in motivos]
            dados_dashboard['motivos_data']['data'] = [m['total'] for m in motivos]
            
            # 3. DADOS PARA GRÁFICO DE DIAS MÉDIOS DE INTERNAÇÃO (Barras)
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
            
            # Prepara os dados para o JS: Arredonda os dias médios
            dados_dashboard['dias_data']['labels'] = [d['nome_baixa'] for d in dias_medios]
            dados_dashboard['dias_data']['data'] = [round(float(d['media_dias']), 1) for d in dias_medios]
            
            # 4. NOVO: MOVIMENTAÇÃO MENSAL (Entradas e Saídas no ANO ATUAL)
            # Entrada por Mês
            sql_entradas_mensal = f"""
            SELECT MONTH(data_entrada) as mes, COUNT(*) as entradas
            FROM Pacientes
            WHERE YEAR(data_entrada) = {current_year}
            GROUP BY mes
            """
            cursor.execute(sql_entradas_mensal)
            entradas_mensal = {item['mes']: item['entradas'] for item in cursor.fetchall()}

            # Alta por Mês
            sql_altas_mensal = f"""
            SELECT MONTH(data_baixa) as mes, COUNT(*) as altas
            FROM Pacientes
            WHERE YEAR(data_baixa) = {current_year} AND status = 'alta'
            GROUP BY mes
            """
            cursor.execute(sql_altas_mensal)
            altas_mensal = {item['mes']: item['altas'] for item in cursor.fetchall()}

            # Cria listas ordenadas de 1 a 12 para o JS
            nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            
            for mes_num in range(1, 13):
                dados_dashboard['movimentacao_mensal']['labels'].append(nomes_meses[mes_num - 1])
                dados_dashboard['movimentacao_mensal']['entradas'].append(entradas_mensal.get(mes_num, 0))
                dados_dashboard['movimentacao_mensal']['altas'].append(altas_mensal.get(mes_num, 0))


            # 5. NOVO: MOVIMENTAÇÃO ANUAL (Últimos 5 Anos)
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
            # Em caso de erro, garante que os dados do gráfico estejam vazios para evitar quebrar o JS
            dados_dashboard['motivos_data'] = {'labels': [], 'data': []}
            dados_dashboard['dias_data'] = {'labels': [], 'data': []}
            dados_dashboard['movimentacao_mensal'] = {'labels': [], 'entradas': [], 'altas': []}
            dados_dashboard['movimentacao_anual'] = {'labels': [], 'entradas': [], 'altas': []}
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
        # get_db_connection já retorna DictCursor
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
    # NOVO: Captura o usuário logado para registrar a internação
    usuario_internacao = session.get('usuario') 
    
    # CORRIGIDO: Usando get_db_connection() para inserção (cursor padrão)
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None:
        return "Erro de conexão com o banco de dados.", 500
        
    cursor = conn.cursor()

    try:
        # 1. SALVAR DADOS DO PACIENTE
        # ATUALIZADO: Adicionada a coluna 'usuario_internacao'
        sql_paciente = """
        INSERT INTO Pacientes (nome, data_nascimento, cep, endereco, bairro, data_entrada, procedimento, status, usuario_internacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'internado', %s)
        """
        # Trata a conversão de data
        try:
            data_nascimento_mysql = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        except ValueError:
            data_nascimento_mysql = None 

        data_entrada_mysql = dados['hora_entrada'].replace('T', ' ')
        
        # CORREÇÃO: O nome do paciente no formulário (dados['nome_paciente']) é salvo na coluna 'nome' da tabela Pacientes.
        cursor.execute(sql_paciente, (
            dados['nome_paciente'], # Corrigido: Usando a chave do formulário para o nome
            data_nascimento_mysql, 
            dados['cep'], 
            f"{dados['endereco']}, {dados['numero']}",
            dados['bairro'], 
            data_entrada_mysql,
            dados['procedimento'],
            usuario_internacao # NOVO CAMPO
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
            # Tenta converter a dose para float, evitando ValueError se o campo estiver vazio ou for inválido
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
# 👥 MÓDULO PACIENTES (LISTA DE INTERNADOS)
# ==============================================================================

@app.route('/pacientes')
@login_required
def pacientes():
    conn = get_db_connection() # Usando get_db_connection
    pacientes_internados = []
    if conn:
        try:
            # Consulta pacientes internados
            # A consulta usa a coluna 'nome'
            sql = "SELECT id, nome, data_nascimento, data_entrada FROM Pacientes WHERE status = 'internado' ORDER BY nome"
            # get_db_connection já retorna DictCursor, as chaves serão 'id', 'nome', 'data_nascimento', 'data_entrada'
            cursor = conn.cursor()
            cursor.execute(sql)
            pacientes_internados = cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(f"Erro ao buscar pacientes: {e}")
        finally:
            conn.close()
            
    # Renderiza a nova página, o template deve usar paciente.nome e paciente.data_entrada
    return render_template('pacientes.html', pacientes=pacientes_internados)

# ------------------------------------------------------------------------------
# 📑 ROTA DE DETALHES UNIFICADA (DETALHES_PRONTUARIO) - RENOMEADA E PADRONIZADA
# ------------------------------------------------------------------------------

@app.route('/paciente/detalhes/<int:paciente_id>')
@login_required
def detalhes_prontuario(paciente_id): # <-- ESTE É O NOME DO ENDPOINT CORRETO
    conn = get_db_connection() # Usando get_db_connection (DictCursor)
    paciente = None
    provas_vida = []
    medicamentos_admin = []
    
    if conn:
        cursor = conn.cursor() # DictCursor
        
        try:
            # 1. Buscar Dados Detalhados do Paciente (Prontuário)
            # ATUALIZADO: Garante que o campo 'usuario_internacao' é buscado
            cursor.execute("SELECT * FROM Pacientes WHERE id = %s", (paciente_id,))
            paciente = cursor.fetchone()
            
            # 2. Buscar todas as Provas de Vida
            cursor.execute("SELECT * FROM ProvasDeVida WHERE paciente_id = %s ORDER BY data_hora DESC", (paciente_id,))
            provas_vida = cursor.fetchall()
            
            # 3. Buscar Histórico de Medicamentos
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

# Rota de Prova de Vida com parâmetro paciente_id
@app.route('/prova_vida/<int:paciente_id>', methods=('GET', 'POST'))
@login_required
def prova_vida(paciente_id):
    conn = get_db_connection() # Usando get_db_connection (DictCursor)
    paciente = None
    
    if conn:
        # 1. Busca o paciente pelo ID
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM Pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        cursor.close()
        conn.close()
        
    if not paciente:
        flash(f"Paciente com ID {paciente_id} não encontrado.", 'danger')
        return redirect(url_for('pacientes')) # Redireciona para a lista se o ID for inválido

    # Caso GET: Exibe o formulário
    if request.method == 'GET':
        # Passa a data/hora atual como padrão para os campos (YYYY-MM-DDTHH:MM)
        agora = datetime.now().strftime('%Y-%m-%dT%H:%M')
        
        return render_template(
            'prova_vida_form.html', 
            paciente=paciente,
            agora=agora,
            usuario_logado=session['usuario']
        )
    
    # Caso POST: Salva a nova prova de vida
    elif request.method == 'POST':
        dados = request.form
        # NOVO: Captura o usuário logado para registrar a prova de vida
        quem_efetuou_val = session.get('usuario', 'Desconhecido') 
        
        # CORRIGIDO: Usando get_db_connection com cursor padrão para inserção
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
            
            # Combina Data e Hora do formulário (que agora virão separadamente)
            data_pv = dados['data_pv'] # YYYY-MM-DD
            hora_pv = dados['hora_pv'] # HH:MM
            data_hora_mysql = f"{data_pv} {hora_pv}:00" # Formato MySQL: YYYY-MM-DD HH:MM:SS
            
            # Garante que os campos numéricos vazios sejam None (para o MySQL)
            glicose_val = dados['glicose'] if dados['glicose'] else None
            saturacao_val = dados['saturacao'] if dados['saturacao'] else None
            batimentos_val = dados['batimentos_cardiacos'] if dados['batimentos_cardiacos'] else None
            
            cursor.execute(sql, (
                paciente_id, # Usando o ID da URL
                data_hora_mysql,
                dados['pressao_arterial'], 
                glicose_val, 
                saturacao_val,
                batimentos_val,
                quem_efetuou_val, # USANDO USUÁRIO DA SESSÃO
                dados['observacoes']
            ))
            
            conn.commit()
            flash('Prova de vida registrada com sucesso!', 'success')
            # CORRIGIDO: Redireciona para o endpoint RENOMEADO
            return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
            
        except Exception as e:
            conn.rollback()
            print(f"Erro ao salvar Prova de Vida: {e}")
            flash(f"Erro interno ao salvar os dados: {e}", 'danger')
            return redirect(url_for('prova_vida', paciente_id=paciente_id))
        finally:
            cursor.close()
            conn.close()

# Rota para o módulo de Prova de Vida genérico (MANTIDO, mas deve ser removido ou alterado no futuro)
@app.route('/prova_vida')
@login_required
def prova_vida_antiga():
    # Esta rota agora redireciona para a nova lista, incentivando o uso do link via Pacientes
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

    conn = get_db_connection() # CORRIGIDO: Usando get_db_connection()
    itens_estoque = []
    if conn:
        cursor = conn.cursor() # DictCursor
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
    
    # Tratamento de erro para garantir que a quantidade seja um número válido
    try:
        quantidade = int(dados['quantidade'])
    except ValueError:
        flash("Quantidade deve ser um número inteiro válido.", 'danger')
        return redirect(url_for('estoque'))
        
    unidade = dados['unidade']
    
    # CORRIGIDO: Usando get_db_connection com cursor padrão para inserção
    conn = get_db_connection(pymysql.cursors.Cursor) 
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

# NOVO: Rota para exibir o formulário de alta
@app.route('/paciente/alta_form/<int:paciente_id>')
@login_required
def alta_form(paciente_id):
    if session.get('nivel') not in ['admin', 'tecnico']:
        flash("Acesso Negado: Apenas Admin/Técnicos podem dar alta.", 'danger')
        # CORRIGIDO: Redireciona para o endpoint RENOMEADO
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Busca os dados essenciais do paciente
    cursor.execute("SELECT id, nome, data_entrada, status FROM Pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    cursor.close()
    conn.close()

    if not paciente or paciente['status'] != 'internado':
        flash("Paciente não encontrado ou já recebeu alta.", 'danger')
        return redirect(url_for('pacientes'))

    # Passa a data/hora atual como padrão para o campo datetime-local (YYYY-MM-DDTHH:MM)
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
    conn = get_db_connection() # CORRIGIDO: Usando get_db_connection()
    pacientes_altas = []
    if conn:
        cursor = conn.cursor() # DictCursor
        # ATUALIZADO: Inclui nome_baixa para exibição no arquivo
        cursor.execute("SELECT id, nome, data_entrada, data_baixa, nome_baixa, procedimento FROM Pacientes WHERE status = 'alta' ORDER BY data_baixa DESC")
        pacientes_altas = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('arquivo.html', pacientes=pacientes_altas, mensagem=request.args.get('mensagem'))
    
# ATUALIZADO: Rota para processar a alta (agora recebe data/hora do formulário)
@app.route('/paciente/alta/<int:paciente_id>', methods=['POST'])
@login_required
def dar_alta(paciente_id):
    if session.get('nivel') not in ['admin', 'tecnico']:
        flash("Acesso Negado: Permissão restrita a Admin e Técnico.", 'danger')
        # CORRIGIDO: Redireciona para o endpoint RENOMEADO
        return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id)) 
    
    dados = request.form
    data_hora_alta = dados['data_hora_alta'] # Formato esperado: YYYY-MM-DDTHH:MM
    
    # CORRIGIDO: Usando get_db_connection com cursor padrão para atualização
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()
    
    try:
        # 1. Trata a data/hora para o formato MySQL DATETIME
        data_baixa_mysql = f"{data_hora_alta.replace('T', ' ')}:00"

        # ATUALIZA NOME_BAIXA E DATA_BAIXA (agora com hora)
        usuario_baixa = session.get('usuario', 'N/A')
        
        sql = "UPDATE Pacientes SET status = 'alta', data_baixa = %s, nome_baixa = %s WHERE id = %s AND status = 'internado'"
        cursor.execute(sql, (data_baixa_mysql, usuario_baixa, paciente_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            flash(f'Alta registrada por {usuario_baixa} em {data_baixa_mysql}!', 'success')
            return redirect(url_for('arquivo'))
        else:
            flash("Erro: Paciente não encontrado ou já tinha alta.", 'danger')
            # CORRIGIDO: Redireciona para o endpoint RENOMEADO
            return redirect(url_for('detalhes_prontuario', paciente_id=paciente_id))
            
    except Exception as e:
        conn.rollback()
        print(f"Erro ao registrar alta: {e}")
        flash(f"Erro interno: {e}", 'danger')
        # CORRIGIDO: Redireciona para o endpoint RENOMEADO
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

    conn = get_db_connection() # Usando get_db_connection (DictCursor)
    usuarios = []
    if conn:
        cursor = conn.cursor() # DictCursor
        
        try:
            # 🚀 CORRIGIDO: Inclui nome_completo, data_nascimento e nacionalidade
            sql_base = "SELECT id, nome_completo, usuario, data_nascimento, nivel_acesso, nacionalidade FROM Usuarios"
            
            # Filtra a visualização para Técnicos (não podem ver outros Admins/Técnicos)
            if session['nivel'] == 'tecnico':
                # Técnico vê somente Enfermeiros
                sql = f"{sql_base} WHERE nivel_acesso = 'enfermeiro' ORDER BY usuario"
            else: # Admin vê todos
                sql = f"{sql_base} ORDER BY nivel_acesso DESC, usuario"
                
            cursor.execute(sql)
            usuarios = cursor.fetchall()
            
        except Exception as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
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
@login_required
def adicionar_usuario():
    if session['nivel'] not in ['admin', 'tecnico']:
        return "Acesso Negado.", 403

    dados = request.form
    
    # 🚨 NOVOS CAMPOS CAPTURADOS: nome_completo, data_nascimento e nacionalidade
    nome_completo = dados['nome_completo'].strip()
    data_nascimento_form = dados['data_nascimento'] # YYYY-MM-DD
    nacionalidade = dados['nacionalidade'].strip()
    # ----------------------------------
    
    novo_usuario = dados['usuario'].strip()
    nova_senha = dados['nova_senha']
    nivel_novo = dados['nivel_acesso']

    # CORRIGIDO: Usando get_db_connection com cursor padrão para inserção
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor()

    # 1. VERIFICAÇÃO DE HIERARQUIA E LIMITES
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

    # 2. TRATAMENTO DA DATA DE NASCIMENTO (Convertendo 'AAAA-MM-DD' para o formato MySQL DATE)
    try:
        data_nascimento_mysql = datetime.strptime(data_nascimento_form, '%Y-%m-%d').date()
    except ValueError:
        flash("Erro: Data de nascimento inválida.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))
        
    # 3. INSERÇÃO DO NOVO USUÁRIO
    try:
        hashed_password = generate_password_hash(nova_senha) 
        
        # 🚀 CORRIGIDO: Adicionada nacionalidade e nome_completo ao comando SQL
        sql = """
        INSERT INTO Usuarios (nome_completo, usuario, senha, data_nascimento, nivel_acesso, nacionalidade) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            nome_completo,
            novo_usuario,
            hashed_password,
            data_nascimento_mysql, # Já formatada como objeto date
            nivel_novo,
            nacionalidade # NOVO CAMPO INSERIDO
        ))
        conn.commit()
        flash(f"Usuário {novo_usuario} adicionado com sucesso!", 'success')
        return redirect(url_for('gerenciar_usuarios'))
        
    except IntegrityError:
        conn.rollback()
        # Erro de integridade (usuário já existe)
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
        
    # CORRIGIDO: Usando get_db_connection com cursor padrão para exclusão
    conn = get_db_connection(pymysql.cursors.Cursor) 
    if conn is None: return "Erro de conexão.", 500
    cursor = conn.cursor(pymysql.cursors.DictCursor) # Usa DictCursor para buscar
    
    # 1. Busca o nível do usuário a ser excluído para verificação
    cursor.execute("SELECT nivel_acesso FROM Usuarios WHERE id = %s", (user_id,))
    user_to_delete = cursor.fetchone()
    
    if not user_to_delete:
        cursor.close()
        conn.close()
        flash("Usuário não encontrado.", 'warning')
        return redirect(url_for('gerenciar_usuarios'))

    nivel_deletado = user_to_delete['nivel_acesso']
    # Fecha o cursor DictCursor e abre o padrão para DELETE
    cursor.close()
    cursor = conn.cursor() 

    # 2. VERIFICAÇÃO DE HIERARQUIA
    if session['nivel'] == 'tecnico' and nivel_deletado != 'enfermeiro':
        flash("Acesso Negado: Técnicos só podem excluir usuários de nível Enfermeiro.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))
    
    if nivel_deletado == 'admin':
        flash("Acesso Negado: Não é permitido excluir o Administrador por esta via.", 'danger')
        conn.close()
        return redirect(url_for('gerenciar_usuarios'))

    # 3. EXCLUSÃO
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
    # Chama a função de setup do banco de dados ANTES de iniciar o servidor
    setup_database() 
    
    # Inicia o servidor Flask
    app.run(debug=True)