from flask import Flask, render_template_string, request, redirect, url_for, session
import psycopg2

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

LOGIN_HTML = open('static/login.html').read()

def get_prestador_info():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT fantasia, cnpj FROM prestador LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {'nome_fantasia': row[0], 'cnpj': row[1]}
    except Exception as e:
        print("Erro ao buscar prestador:", e)
    return {'nome_fantasia': '', 'cnpj': ''}

DB_CONFIG = {
    'host': 'aws-1-sa-east-1.pooler.supabase.com',
    'dbname': 'postgres',
    'user': 'postgres.zlxlrpejtgrqxmpixwdq',
    'password': 'Odisseia2001FIM',
    'port': 5432
}

def check_user(username, password):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT profissional_id, login FROM usuarios WHERE login=%s AND senha=%s", (username, password))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return {'profissional_id': result[0], 'login': result[1]}
        return None
    except Exception as e:
        print("Erro ao acessar o banco:", e)
        return False

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    prestador = get_prestador_info()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = check_user(username, password)
        if user:
            session['user_id'] = user['profissional_id']
            session['username'] = user['login']
            return redirect(url_for('comissao'))
        else:
            error = 'Usuário ou senha inválidos.'
    return render_template_string(LOGIN_HTML, error=error, nome_fantasia=prestador['nome_fantasia'], cnpj=prestador['cnpj'])


# Nova rota para exibir comissão

from datetime import date, timedelta, datetime

@app.route('/comissao', methods=['GET'])
def comissao():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    # Data selecionada via query param, padrão: hoje
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()
    print(f"[DEBUG] user_id: {user_id}, data_selecionada: {data_selecionada}")

    # Consulta agenda do dia
    agenda = []
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT profissional_id, data, hora, produto_descricao, valor_comissao
            FROM vw_agenda_dia
            WHERE profissional_id = %s AND data = %s
            ORDER BY hora
        """, (user_id, data_selecionada))
        agenda = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return f"<h2>Erro ao acessar o banco: {e}</h2>"

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Comissão do dia selecionado
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_agenda_produtos
            WHERE profissional_id = %s AND data = %s
        """, (user_id, data_selecionada))
        comissao_dia = cur.fetchone()[0]
        # Comissão do mês da data selecionada
        cur.execute("""
            SELECT COALESCE(SUM(valor_comissao), 0)
            FROM vw_agenda_produtos
            WHERE profissional_id = %s AND date_trunc('month', data) = date_trunc('month', %s)
        """, (user_id, data_selecionada))
        comissao_mes = cur.fetchone()[0]
        # Agenda removida
        # print removido
        cur.close()
        conn.close()
    except Exception as e:
        return f"<h2>Erro ao acessar o banco: {e}</h2>"
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
    app.run(host='0.0.0.0', port=5000, debug=True)
