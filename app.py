import logging
from flask import Flask, render_template_string, request, redirect, url_for, session
import psycopg2
from psycopg2 import pool
from flask_ngrok import run_with_ngrok

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'


# Novo template de login com campo para nome da empresa (identificador)
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', Arial, sans-serif; background: #1565c0; margin: 0; min-height: 100vh; }
        .container { max-width: 400px; margin: 80px auto; background: #f4f8fb; padding: 36px 28px 28px 28px; border-radius: 16px; box-shadow: 0 4px 24px rgba(21,101,192,0.13); text-align: center; }
        .titulo { font-size: 2.1rem; font-weight: 700; color: #1565c0; margin-bottom: 18px; }
        .form-group { margin-bottom: 18px; text-align: left; }
        label { display: block; font-weight: 700; color: #1976d2; margin-bottom: 6px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #b0bec5; font-size: 1rem; }
        .btn { width: 100%; padding: 12px; background: #1976d2; color: #fff; border: none; border-radius: 6px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: background 0.2s; }
        .btn:hover { background: #0d47a1; }
        .error { color: #d32f2f; margin-bottom: 12px; font-weight: 700; }
    </style>
    <link rel="apple-touch-icon" sizes="192x192" href="{{ url_for('static', filename='calendario.png') }}">
    <link rel="icon" type="image/png" sizes="192x192" href="{{ url_for('static', filename='calendario.png') }}">
</head>
<body>
    <div class="container">
        <div class="titulo">Login</div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <div class="form-group">
                <label for="empresa">Nome da empresa</label>
                <input type="text" id="empresa" name="empresa" required placeholder="Nome da empresa">
            </div>
            <div class="form-group">
                <label for="username">Usuário</label>
                <input type="text" id="username" name="username" required placeholder="Login">
            </div>
            <div class="form-group">
                <label for="password">Senha</label>
                <input type="password" id="password" name="password" required placeholder="Senha">
            </div>
            <button type="submit" class="btn">Entrar</button>
        </form>
    </div>
</body>
</html>
'''

DB_CONFIG = {
    'host': 'aws-1-sa-east-1.pooler.supabase.com',
    'dbname': 'postgres',
    'user': 'postgres.zlxlrpejtgrqxmpixwdq',
    'password': 'Odisseia2001FIM',
    'port': 5432
}

# Initialize a connection pool
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 20, **DB_CONFIG)
except Exception as e:
    logging.error(f"Erro ao inicializar o pool de conexões do banco de dados: {e}")
    # Depending on the application, you might want to exit or handle this more gracefully

def get_prestador_info():
    conn = None
    try:
        conn = connection_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT fantasia, cnpj FROM prestador LIMIT 1")
        row = cur.fetchone()
        cur.close()
        if row:
            return {'nome_fantasia': row[0], 'cnpj': row[1]}
    except Exception as e:
        logging.error(f"Erro ao buscar informações do prestador: {e}")
    finally:
        if conn:
            connection_pool.putconn(conn)
    return {'nome_fantasia': '', 'cnpj': ''}


# Busca id_prestador pelo nome da empresa (identificador) e valida login
def check_user(username, password, empresa):
    conn = None
    try:
        conn = connection_pool.getconn()
        cur = conn.cursor()
        # Valida login, senha e identificador (nome da empresa) em uma única consulta
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
        return False
    finally:
        if conn:
            connection_pool.putconn(conn)

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        empresa = request.form['empresa']
        username = request.form['username']
        password = request.form['password']
        user = check_user(username, password, empresa)
        if user:
            session['user_id'] = user['profissional_id']
            session['username'] = user['login']
            session['nome_fantasia'] = user['nome_fantasia']
            session['cnpj'] = user['cnpj']
            session['id_prestador'] = user['id_prestador']
            return redirect(url_for('comissao'))
        else:
            error = 'Usuário, senha ou empresa inválidos.'
    return render_template_string(LOGIN_HTML, error=error)


# Nova rota para exibir comissão

from datetime import date, timedelta, datetime

@app.route('/comissao', methods=['GET'])
def comissao():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    id_prestador = session.get('id_prestador')
    # Data selecionada via query param, padrão: hoje
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()
    print(f"[DEBUG] user_id: {user_id}, data_selecionada: {data_selecionada}, id_prestador: {id_prestador}  ")

    # Consulta agenda do dia
    agenda = []
    conn_agenda = None
    try:
        conn_agenda = connection_pool.getconn()
        cur = conn_agenda.cursor()
        cur.execute("""
            SELECT profissional_id, data, hora, produto_descricao, valor_comissao
            FROM vw_agenda_dia
            WHERE profissional_id = %s AND data = %s AND id_prestador = %s
            ORDER BY hora
        """, (user_id, data_selecionada, id_prestador))
        print(f"[DEBUG] Agenda query executed for profissional_id={user_id}, data={data_selecionada}, id_prestador={id_prestador}")
        agenda = cur.fetchall()
        cur.close()
    except Exception as e:
        logging.error(f"Erro ao buscar agenda do dia para profissional_id={user_id}, data={data_selecionada}, id_prestador={id_prestador}: {e}")
        return f"<h2>Erro ao acessar o banco: {e}</h2>"
    finally:
        if conn_agenda:
            connection_pool.putconn(conn_agenda)

    comissao_dia = 0
    comissao_mes = 0
    conn_comissao = None
    try:
        conn_comissao = connection_pool.getconn()
        cur = conn_comissao.cursor()
        # Comissão do dia selecionado
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_comissao
            WHERE profissional_id = %s AND data = %s AND id_prestador = %s
        """, (user_id, data_selecionada, id_prestador))
        print(f"[DEBUG] Comissão do dia query executed for profissional_id={user_id}, data={data_selecionada}, id_prestador={id_prestador}")
        comissao_dia = cur.fetchone()[0]
        # Comissão do mês da data selecionada
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_comissao
            WHERE profissional_id = %s AND date_trunc('month', data) = date_trunc('month', %s) AND id_prestador = %s
        """, (user_id, data_selecionada, id_prestador   ))
        print(f"[DEBUG] Comissão do mês query executed for profissional_id={user_id}, data={data_selecionada}, id_prestador={id_prestador}")
        comissao_mes = cur.fetchone()[0]
        cur.close()
    except Exception as e:
        logging.error(f"Erro ao buscar comissões para profissional_id={user_id}, data={data_selecionada}, id_prestador={id_prestador}: {e}")
        return f"<h2>Erro ao acessar o banco: {e}</h2>"
    finally:
        if conn_comissao:
            connection_pool.putconn(conn_comissao)

    data_hoje = data_selecionada
    data_ant = (data_hoje - timedelta(days=1)).strftime('%Y-%m-%d')
    data_prox = (data_hoje + timedelta(days=1)).strftime('%Y-%m-%d')
    # Corrigir hora para garantir que é datetime.time
    def format_hora(h):
        if hasattr(h, 'strftime'):
            return h.strftime('%H:%M')
        try:
            return datetime.strptime(h, '%H:%M:%S').strftime('%H:%M')
        except Exception:
            return str(h)

    html = f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comissão</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Roboto', Arial, sans-serif;
                background: #1565c0;
                margin: 0;
                min-height: 100vh;
            }}
            .container {{
                max-width: 480px;
                margin: 60px auto;
                background: #f4f8fb;
                padding: 36px 28px 28px 28px;
                border-radius: 16px;
                box-shadow: 0 4px 24px rgba(21,101,192,0.13);
                text-align: center;
            }}
            .cabecalho-empresa {{
                font-size: 1.1rem;
                color: #1976d2;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            .titulo {{
                font-size: 2.1rem;
                font-weight: 700;
                color: #1565c0;
                margin-bottom: 18px;
            }}
            .data-navegacao {{
                margin: 18px 0 18px 0;
                font-size: 1.2rem;
                font-weight: 700;
                color: #1565c0;
            }}
            .nav-btn {{
                display: inline-block;
                margin: 0 8px 0 8px;
                padding: 8px 18px;
                background: #1976d2;
                color: #fff;
                border: none;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 700;
                text-decoration: none;
                transition: background 0.2s;
                cursor: pointer;
            }}
            .nav-btn:hover {{
                background: #0d47a1;
            }}
            .valor {{
                font-size: 1.4rem;
                margin: 18px 0 8px 0;
                color: #1976d2;
            }}
            .valor strong {{
                color: #0d47a1;
                font-size: 2rem;
            }}
            .logout-btn {{
                display: inline-block;
                margin-top: 32px;
                padding: 12px 32px;
                background: #1976d2;
                color: #fff;
                border: none;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 700;
                text-decoration: none;
                transition: background 0.2s;
                cursor: pointer;
            }}
            .logout-btn:hover {{
                background: #0d47a1;
            }}
            .agenda-section {{
                margin-top: 32px;
                text-align: left;
            }}
            .agenda-title {{
                font-size: 1.2rem;
                color: #1976d2;
                margin-bottom: 8px;
                font-weight: 700;
                text-align: center;
            }}
            .agenda-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .agenda-item {{
                background: #e3eaf5;
                border-radius: 6px;
                margin-bottom: 10px;
                padding: 12px 16px;
                box-shadow: 0 1px 3px rgba(21,101,192,0.04);
            }}
            .agenda-hora {{
                font-weight: 700;
                color: #1565c0;
            }}
            .agenda-desc {{
                color: #333;
                margin-left: 8px;
            }}
            .agenda-valor {{
                float: right;
                color: #1976d2;
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="cabecalho-empresa">{session.get('nome_fantasia', '')} | CNPJ: {session.get('cnpj', '')}</div>
            <div class="titulo">Olá, {session['username']}!</div>
            <div class="valor">Comissão do dia:<br><strong>R$ {comissao_dia:.2f}</strong></div>
            <div class="valor">Comissão do mês:<br><strong>R$ {comissao_mes:.2f}</strong></div>
            <div class="data-navegacao">
                <a href="/comissao?data={(data_selecionada - timedelta(days=1)).strftime('%Y-%m-%d')}" class="nav-btn">◀</a>
                <span>{data_selecionada.strftime('%d/%m/%Y')}</span>
                <a href="/comissao?data={(data_selecionada + timedelta(days=1)).strftime('%Y-%m-%d')}" class="nav-btn">▶</a>
            </div>
            <div class="agenda-section">
                <div class="agenda-title">Agenda do dia</div>
                <ul class="agenda-list">
                    {''.join([
                        f'<li class="agenda-item"><span class="agenda-hora">{format_hora(hora)}</span> <span class="agenda-desc">{descricao if descricao else "Serviço não informado"}</span> <span class="agenda-valor">R$ {valor_comissao if valor_comissao is not None else 0:.2f}</span></li>'
                        for (_, _, hora, descricao, valor_comissao) in agenda
                    ]) if agenda else '<li class="agenda-item">Nenhum agendamento para este dia.</li>'}
                </ul>
            </div>
            <a href="/logout" class="logout-btn">Sair</a>
        </div>
    </body>
    </html>
    '''
    return html
print("[DEBUG] Comissão page rendered")
# Rota de logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Only use ngrok if you are in a Colab environment
    # run_with_ngrok(app) 
    
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        if connection_pool:
            connection_pool.closeall()