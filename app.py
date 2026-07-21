from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.pool
import logging
import os
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Chave secreta para gerenciar as sessões

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações do Banco de Dados (Supabase)
DB_CONFIG = {
    'host': 'aws-1-sa-east-1.pooler.supabase.com',
    'dbname': 'postgres',
    'user': 'postgres.zlxlrpejtgrqxmpixwdq',
    'password': 'Odisseia2001FIM',
    'port': 5432
}

# Inicialização do Pool de conexões
connection_pool = None
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 20, **DB_CONFIG)
    logging.info("Pool de conexões do banco de dados inicializado com sucesso.")
except Exception as e:
    logging.error(f"Erro ao inicializar o pool de conexões do banco de dados: {e}")


def get_conn():
    """Obtém uma conexão do pool."""
    if connection_pool:
        return connection_pool.getconn()
    raise Exception("O pool de conexões não está disponível")


def put_conn(conn):
    """Devolve uma conexão ao pool."""
    if conn:
        connection_pool.putconn(conn)


def check_user(username, password, empresa):
    """Verifica as credenciais do usuário na view do banco."""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT profissional_id, login, fantasia, cnpj, id_prestador
            FROM vw_usuarios
            WHERE login=%s AND senha=%s AND identificador=%s
        """, (username, password, empresa))
        result = cur.fetchone()
        cur.close()
        if result:
            return {
                'profissional_id': result[0],
                'login': result[1],
                'nome_fantasia': result[2],
                'cnpj': result[3],
                'id_prestador': result[4]
            }
        return None
    except Exception as e:
        logging.error(f"Erro ao acessar o banco em check_user: {e}")
        return None
    finally:
        put_conn(conn)


# ──────────────────────────── ROTAS DE AUTENTICAÇÃO ────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        empresa = request.form['empresa']
        username = request.form['username']
        password = request.form['password']

        user_info = check_user(username, password, empresa)

        if user_info:
            session['logged_in'] = True
            session['username'] = user_info['login']
            session['company'] = user_info['nome_fantasia']
            session['id_prestador'] = user_info['id_prestador']
            session['profissional_id'] = user_info['profissional_id']
            message = f"Bem-vindo, {user_info['login']} da {user_info['nome_fantasia']}!"
            logging.info(message)
            return redirect(url_for('dashboard'))
        else:
            error = 'Nome da empresa, usuário ou senha inválidos.'
            logging.warning(f"Tentativa de login falhou para Empresa: {empresa}, Usuário: {username}")

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('company', None)
    session.pop('id_prestador', None)
    logging.info("Usuário desconectado.")
    return redirect(url_for('login'))


# ──────────────────────────── DASHBOARD / MENU ────────────────────────────

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# ──────────────────────────── FATURAMENTO DO DIA ────────────────────────────

@app.route('/faturamento-dia')
def faturamento_dia():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    id_prestador = session.get('id_prestador')
    data_selecionada = request.args.get('data', date.today().isoformat())

    conn = None
    recebidos = []
    previstos = []

    try:
        conn = get_conn()
        cur = conn.cursor()

        # Busca atendimentos finalizados (recebido)
        cur.execute("""
            SELECT a.id, a.id_prestador, a.data, a.status,
                   f.nome_forma_pagamento, COALESCE(p.valor, 0) AS valor
            FROM agenda a
            INNER JOIN pagamentos p ON p.agenda_id = a.id
            INNER JOIN formas_pagamento f ON f.id = p.forma_pgto
            WHERE a.id_prestador = %s AND a.data = %s AND a.status = 'f'
            ORDER BY a.id
        """, (id_prestador, data_selecionada))

        for row in cur.fetchall():
            recebidos.append({
                'id': row[0],
                'forma_pagamento': row[4],
                'valor': float(row[5])
            })

        # Busca atendimentos agendados (previsto)
        cur.execute("""
            SELECT a.id, a.id_prestador, a.data, a.status,
                   f.nome_forma_pagamento, COALESCE(p.valor, 0) AS valor
            FROM agenda a
            INNER JOIN pagamentos p ON p.agenda_id = a.id
            INNER JOIN formas_pagamento f ON f.id = p.forma_pgto
            WHERE a.id_prestador = %s AND a.data = %s AND a.status = 'a'
            ORDER BY a.id
        """, (id_prestador, data_selecionada))

        for row in cur.fetchall():
            previstos.append({
                'id': row[0],
                'forma_pagamento': row[4],
                'valor': float(row[5])
            })

        cur.close()

    except Exception as e:
        logging.error(f"Erro ao buscar faturamento do dia: {e}")
    finally:
        put_conn(conn)

    total_recebido = sum(item['valor'] for item in recebidos)
    total_previsto = sum(item['valor'] for item in previstos)

    return render_template(
        'faturamento_dia.html',
        recebidos=recebidos,
        previstos=previstos,
        total_recebido=total_recebido,
        total_previsto=total_previsto,
        data_selecionada=data_selecionada
    )


# ──────────────────────────── FATURAMENTO DO MÊS ────────────────────────────

@app.route('/faturamento-mes')
def faturamento_mes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    id_prestador = session.get('id_prestador')
    
    hoje = date.today()
    mes_selecionado = request.args.get('mes', hoje.strftime('%Y-%m'))
    
    try:
        ano, mes = map(int, mes_selecionado.split('-'))
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)
    except ValueError:
        data_inicio = date(hoje.year, hoje.month, 1)
        if hoje.month == 12:
            data_fim = date(hoje.year + 1, 1, 1)
        else:
            data_fim = date(hoje.year, hoje.month + 1, 1)
        mes_selecionado = hoje.strftime('%Y-%m')

    conn = None
    faturamento = []

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT f.nome_forma_pagamento, SUM(COALESCE(p.valor, 0)) AS valor
            FROM agenda a
            INNER JOIN pagamentos p ON p.agenda_id = a.id
            INNER JOIN formas_pagamento f ON f.id = p.forma_pgto
            WHERE a.id_prestador = %s AND a.status = 'f'
              AND a.data >= %s AND a.data < %s
            GROUP BY f.nome_forma_pagamento
            ORDER BY valor DESC
        """, (id_prestador, data_inicio.isoformat(), data_fim.isoformat()))

        for row in cur.fetchall():
            faturamento.append({
                'forma_pagamento': row[0],
                'valor': float(row[1])
            })

        cur.close()

    except Exception as e:
        logging.error(f"Erro ao buscar faturamento do mês: {e}")
    finally:
        put_conn(conn)

    total_faturamento = sum(item['valor'] for item in faturamento)

    return render_template(
        'faturamento_mes.html',
        faturamento=faturamento,
        total_faturamento=total_faturamento,
        mes_selecionado=mes_selecionado
    )


# ──────────────────────────── COMISSÃO ────────────────────────────

@app.route('/comissao', methods=['GET'])
def comissao():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    profissional_id = session.get('profissional_id')
    id_prestador = session.get('id_prestador')
    
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()

    conn = None
    comissao_dia = 0
    comissao_mes = 0
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Comissão do dia selecionado
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_agenda_produtos
            WHERE profissional_id = %s AND data = %s AND id_prestador = %s
        """, (profissional_id, data_selecionada, id_prestador))
        row = cur.fetchone()
        comissao_dia = row[0] if row else 0
        
        # Comissão do mês da data selecionada
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_agenda_produtos
            WHERE profissional_id = %s AND date_trunc('month', data) = date_trunc('month', %s) AND id_prestador = %s
        """, (profissional_id, data_selecionada, id_prestador))
        row = cur.fetchone()
        comissao_mes = row[0] if row else 0
        
        cur.close()
    except Exception as e:
        logging.error(f"Erro ao buscar comissão: {e}")
    finally:
        put_conn(conn)

    return render_template('comissao.html', comissao_dia=comissao_dia, comissao_mes=comissao_mes, data_selecionada=data_selecionada)


# ──────────────────────────── INICIALIZADOR PRODUCTION ────────────────────────────

if __name__ == "__main__":
    # Define a porta usando as configurações do Render ou usa a 5000 localmente
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
