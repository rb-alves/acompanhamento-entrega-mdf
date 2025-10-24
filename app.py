from flask import Flask, jsonify, request, render_template
import mysql.connector
from decouple import config
from datetime import datetime
import requests

# Importa funções das APIs uMov.me
from api_umov_entrega import fetch_entrega
from api_umov_montagem import fetch_montagem

app = Flask(__name__)

# 🔐 Chave secreta do Flask 
app.secret_key = config("SECRET_KEY", default="chave-padrao")

# ============================================================
# 🔗 Conexão com o banco
# ============================================================
def get_connection():
    return mysql.connector.connect(
        host=config("DB_HOST"),
        user=config("DB_USER"),
        password=config("DB_PASS"),
        database=config("DB_NAME"),
        port=config("DB_PORT", cast=int, default=3306),
    )

# ============================================================
# 🧭 Função auxiliar — formata datas
# ============================================================
def formatar_data_api(data_str):
    """Converte 'YYYY-mm-dd HH:MM:SS' para 'dd/mm/YYYY HH:MM:SS'"""
    if not data_str or data_str == "—":
        return "—"
    try:
        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return data_str

# ============================================================
# 🌐 Página principal
# ============================================================
@app.route("/")
def index():
    return render_template("index.html", RECAPTCHA_SITE_KEY=config("RECAPTCHA_SITE_KEY"))

# ============================================================
# 🧾 API /api/pedidos — retorna pedidos + situação atual
# ============================================================
@app.route("/api/pedidos")
def pedidos():
    cpf = request.args.get("cpf")
    captcha_token = request.args.get("captcha")

    if not cpf:
        return jsonify({"error": "CPF não informado"}), 400

    if not captcha_token:
        return jsonify({"error": "Captcha ausente"}), 403

    # 🔹 Verifica o captcha com o Google
    secret_key = config("RECAPTCHA_SECRET_KEY")
    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret_key, "response": captcha_token}
    captcha_resp = requests.post(verify_url, data=payload).json()

    if not captcha_resp.get("success"):
        return jsonify({"error": "Falha na verificação do CAPTCHA"}), 403

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 1) Busca pedidos do cliente
    query_pedidos = """
        SELECT *
        FROM starmoveis_custom.vw_pedidos
        WHERE cpf = %s
        ORDER BY pedido DESC
    """
    cursor.execute(query_pedidos, (cpf,))
    pedidos = cursor.fetchall()

    if not pedidos:
        cursor.close()
        conn.close()
        return jsonify([])

    # 🔹 2) Última situação do banco
    query_situacoes = """
        SELECT 
            s.xano AS transacao,
            s.situacao,
            s.date,
            s.time
        FROM starmoveis_custom.vw_situacoes_pedidos s
        INNER JOIN (
            SELECT xano, MAX(date * 1000000 + time) AS ultima
            FROM starmoveis_custom.vw_situacoes_pedidos
            GROUP BY xano
        ) ult
            ON s.xano = ult.xano 
            AND (s.date * 1000000 + s.time) = ult.ultima
        JOIN starmoveis_custom.vw_pedidos p
            ON p.transacao = s.xano
        WHERE p.cpf = %s
    """
    cursor.execute(query_situacoes, (cpf,))
    situacoes = cursor.fetchall()

    situacao_por_transacao = {}
    for s in situacoes:
        try:
            total_segundos = s["time"]
            horas = total_segundos // 3600
            resto = total_segundos % 3600
            minutos = resto // 60
            segundos = resto % 60
            data_formatada = f"{datetime.strptime(str(s['date']), '%Y%m%d').strftime('%d/%m/%Y')} {horas:02d}:{minutos:02d}:{segundos:02d}"
        except Exception:
            data_formatada = "—"

        situacao_por_transacao[s["transacao"]] = {
            "situacao": s["situacao"],
            "data_hora": data_formatada
        }

    # 🔹 3) Itens do pedido
    query_itens = """
        SELECT 
            pp.loja,
            pp.pedido,
            pp.item,
            pp.produto,
            pp.quantidade,
            pp.preco
        FROM starmoveis_custom.vw_produtos_pedidos pp
        JOIN starmoveis_custom.vw_pedidos p
            ON pp.loja = p.loja AND pp.pedido = p.pedido
        WHERE p.cpf = %s
        ORDER BY pp.pedido
    """
    cursor.execute(query_itens, (cpf,))
    itens = cursor.fetchall()

    itens_por_pedido = {}
    for item in itens:
        chave = f"{item['loja']}-{item['pedido']}"
        itens_por_pedido.setdefault(chave, []).append({
            "item": item["produto"],
            "quantidade": item["quantidade"],
            "preco": item["preco"]
        })

    # 🔹 4) Monta resultado final com integrações uMov
    for p in pedidos:
        ultima_etapa = situacao_por_transacao.get(p["transacao"], {"situacao": "—", "data_hora": "—"})
        situacao_final = ultima_etapa["situacao"]
        data_final = ultima_etapa["data_hora"]

        try:
            # 🟢 API Entrega
            umov_entrega = fetch_entrega(p["transacao"])
            if umov_entrega:
                def parse_datetime(dt):
                    try:
                        return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                    except:
                        return datetime.min

                umov_entrega.sort(key=lambda x: parse_datetime(x.get("finish_time") or x.get("insert_time") or ""), reverse=True)
                ultima = umov_entrega[0]

                if ultima["situacao"] != "Retornada de Campo":
                    situacao_final = "SAIU PARA A ENTREGA"
                    data_final = formatar_data_api(ultima.get("insert_time"))
                else:
                    if ultima.get("activity_description") == "Entrega":
                        situacao_final = "ENTREGUE"
                        data_final = formatar_data_api(ultima.get("finish_time"))
                    elif ultima.get("activity_description") == "Entrega não realizada":
                        situacao_final = "NÃO ENTREGUE"
                        data_final = formatar_data_api(ultima.get("finish_time"))

            # 🟡 API Montagem — corrigida
            umov_montagem = fetch_montagem(p["transacao"])
            if umov_montagem:
                def parse_datetime(dt):
                    try:
                        return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                    except:
                        return datetime.min

                # Ordena por data crescente para analisar sequência lógica
                umov_montagem.sort(key=lambda x: parse_datetime(x.get("insert_time") or x.get("finish_time") or ""))

                # Define padrão inicial
                situacao_final = "AGUARDANDO MONTAGEM"
                data_final = formatar_data_api(umov_montagem[0].get("insert_time"))

                for atividade in umov_montagem:
                    desc = atividade.get("activity_description")
                    situacao = atividade.get("situacao")

                    # Caso esteja em deslocamento
                    if desc == "Início do deslocamento":
                        situacao_final = "SAIU PARA A MONTAGEM"
                        data_final = formatar_data_api(atividade.get("finish_time"))

                    # Caso tenha retornado de campo
                    elif situacao == "Retornada de Campo":
                        if desc == "Montagem":
                            situacao_final = "MONTADO"
                            data_final = formatar_data_api(atividade.get("finish_time"))
                        elif desc == "Montagem não realizada":
                            situacao_final = "NÃO MONTADO"
                            data_final = formatar_data_api(atividade.get("finish_time"))

        except Exception as e:
            print(f"[ERRO uMov.me - Pedido {p['transacao']}] {e}")

        # 📅 Formata data principal
        data_str = str(p["data"])
        if len(data_str) == 8:
            p["data"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")

        p["situacao_pedido"] = situacao_final
        p["data_situacao"] = data_final
        chave = f"{p['loja']}-{p['pedido']}"
        p["itens"] = itens_por_pedido.get(chave, [])

    cursor.close()
    conn.close()
    return jsonify(pedidos)

# ============================================================
# 🧾 API /api/detalhes — retorna pedido + itens + histórico
# ============================================================
@app.route("/api/detalhes")
def detalhes():
    cpf = request.args.get("cpf")
    loja = request.args.get("loja")
    pedido = request.args.get("pedido")

    if not all([cpf, loja, pedido]):
        return jsonify({"error": "Parâmetros insuficientes"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM starmoveis_custom.vw_pedidos WHERE cpf=%s AND loja=%s AND pedido=%s",
        (cpf, loja, pedido)
    )
    pedido_info = cursor.fetchone()
    if not pedido_info:
        cursor.close()
        conn.close()
        return jsonify({"error": "Pedido não encontrado"}), 404

    cursor.execute(
        "SELECT produto, quantidade, preco FROM starmoveis_custom.vw_produtos_pedidos WHERE loja=%s AND pedido=%s",
        (loja, pedido)
    )
    pedido_info["itens"] = cursor.fetchall()

    cursor.execute(
        """
        SELECT situacao, date, time
        FROM starmoveis_custom.vw_situacoes_pedidos
        WHERE xano = %s
        ORDER BY date, time
        """,
        (pedido_info["transacao"],)
    )
    historico = cursor.fetchall()

    etapas = []
    for h in historico:
        try:
            total_segundos = h["time"]
            horas = total_segundos // 3600
            resto = total_segundos % 3600
            minutos = resto // 60
            segundos = resto % 60
            data_formatada = f"{datetime.strptime(str(h['date']), '%Y%m%d').strftime('%d/%m/%Y')} {horas:02d}:{minutos:02d}:{segundos:02d}"
        except:
            data_formatada = "—"
        etapas.append({
            "situacao": h["situacao"],
            "data_formatada": data_formatada
        })

    # 🔹 Etapas da API Entrega
    try:
        umov_entrega = fetch_entrega(pedido_info["transacao"])
        if umov_entrega:
            for entrega in umov_entrega:
                etapas.append({
                    "situacao": "SAIU PARA A ENTREGA",
                    "data_formatada": formatar_data_api(entrega.get("insert_time"))
                })
                if entrega["situacao"] == "Retornada de Campo":
                    if entrega.get("activity_description") == "Entrega":
                        etapas.append({
                            "situacao": "ENTREGUE",
                            "data_formatada": formatar_data_api(entrega.get("finish_time"))
                        })
                    elif entrega.get("activity_description") == "Entrega não realizada":
                        etapas.append({
                            "situacao": "NÃO ENTREGUE",
                            "data_formatada": formatar_data_api(entrega.get("finish_time"))
                        })
    except Exception as e:
        print(f"[ERRO uMov.me - Entrega {pedido_info['transacao']}] {e}")

    # 🔹 Etapas da API Montagem 
    try:
        umov_montagem = fetch_montagem(pedido_info["transacao"])
        if umov_montagem:
            for montagem in umov_montagem:
                # Adiciona "Aguardando Montagem" para cada tarefa, conforme solicitado
                etapas.append({
                    "situacao": "AGUARDANDO MONTAGEM",
                    "data_formatada": formatar_data_api(montagem.get("insert_time"))
                })

                # Se iniciou deslocamento → Saiu para montagem
                if montagem.get("activity_description") == "Início do deslocamento":
                    etapas.append({
                        "situacao": "SAIU PARA A MONTAGEM",
                        "data_formatada": formatar_data_api(
                            montagem.get("finish_time") or montagem.get("insert_time")
                        )
                    })

                # Se retornou de campo → finalização
                if montagem["situacao"] == "Retornada de Campo":
                    if montagem.get("activity_description") == "Montagem":
                        etapas.append({
                            "situacao": "MONTADO",
                            "data_formatada": formatar_data_api(montagem.get("finish_time"))
                        })
                    elif montagem.get("activity_description") == "Montagem não realizada":
                        etapas.append({
                            "situacao": "NÃO MONTADO",
                            "data_formatada": formatar_data_api(montagem.get("finish_time"))
                        })
    except Exception as e:
        print(f"[ERRO uMov.me - Montagem {pedido_info['transacao']}] {e}")


    # 🔹 Ordenação cronológica real e Remoção de Duplicatas Exatas (a correção)
    def parse_data_hora(d):
        # Trata datas formatadas (dd/mm/YYYY HH:MM:SS) para fins de ordenação
        try:
            return datetime.strptime(d, "%d/%m/%Y %H:%M:%S")
        except:
            # Retorna data mínima para que entradas sem data válida ("—") fiquem no início, se aplicável
            return datetime.min

    # 1. Ordena todas as etapas cronologicamente
    todas_etapas = sorted(etapas, key=lambda x: parse_data_hora(x["data_formatada"]))

    # 2. Remove duplicatas exatas de (situacao, data_formatada)
    # Isso garante que, se duas fontes adicionarem a mesma entrada (situação e data) no mesmo momento,
    # apenas uma seja mantida, resolvendo a duplicação sequencial.
    etapas_filtradas = []
    vistas = set() 

    for etapa in todas_etapas:
        chave_unica = (etapa["situacao"], etapa["data_formatada"])
        
        if chave_unica not in vistas:
            etapas_filtradas.append(etapa)
            vistas.add(chave_unica)

    pedido_info["etapas"] = etapas_filtradas

    # 🔹 Formata data principal
    data_str = str(pedido_info.get("data"))
    if data_str and len(data_str) == 8:
        pedido_info["data"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")

    cursor.close()
    conn.close()
    return jsonify(pedido_info)

# ============================================================
# 🚀 Iniciar servidor
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
