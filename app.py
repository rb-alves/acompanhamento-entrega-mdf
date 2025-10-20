from flask import Flask, jsonify, request, render_template
import mysql.connector
from datetime import datetime

# Importa funções da API uMov.me
from api_umov import fetch_entrega

app = Flask(__name__)

# ============================================================
# 🔗 Conexão com o banco
# ============================================================
def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="mdf@123",
        database="pedidos"
    )

# ============================================================
# 🧭 Função auxiliar — formata datas
# ============================================================
def formatar_data_api(data_str):
    """Converte '2025-10-15 16:10:35' para '15/10/2025 16:10:35'"""
    if not data_str or data_str == "—":
        return "—"
    try:
        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return data_str  # retorna original se não conseguir converter

# ============================================================
# 🌐 Página principal
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")

# ============================================================
# 🧾 API /api/pedidos — retorna pedidos + situação atual
# ============================================================
@app.route("/api/pedidos")
def pedidos():
    cpf = request.args.get("cpf")

    if not cpf:
        return jsonify({"error": "CPF não informado"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 1) Busca pedidos do cliente
    query_pedidos = """
        SELECT *
        FROM pedidos
        WHERE cpf = %s
        ORDER BY pedido DESC
    """
    cursor.execute(query_pedidos, (cpf,))
    pedidos = cursor.fetchall()

    if not pedidos:
        cursor.close()
        conn.close()
        return jsonify([])

    # 🔹 2) Última situação (local)
    query_situacoes = """
        SELECT 
            s.xano AS transacao,
            s.situacao,
            s.date,
            s.time
        FROM situacao_pedidos s
        INNER JOIN (
            SELECT xano, MAX(date * 1000000 + time) AS ultima
            FROM situacao_pedidos
            GROUP BY xano
        ) ult
            ON s.xano = ult.xano 
            AND (s.date * 1000000 + s.time) = ult.ultima
        JOIN pedidos p
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

    # 🔹 3) Itens
    query_itens = """
        SELECT 
            pp.loja,
            pp.pedido,
            pp.item,
            pp.produto,
            pp.quantidade,
            pp.preco
        FROM produtos_pedidos pp
        JOIN pedidos p
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

    # 🔹 4) Monta resultado final + integração uMov
    for p in pedidos:
        ultima_etapa = situacao_por_transacao.get(p["transacao"], {"situacao": "—", "data_hora": "—"})
        situacao_final = ultima_etapa["situacao"]
        data_final = ultima_etapa["data_hora"]

        try:
            umov_data = fetch_entrega(p["transacao"])

            if umov_data:
                # 🔹 Ordena por data mais recente
                def parse_datetime(dt):
                    try:
                        return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                    except:
                        return datetime.min

                umov_data.sort(key=lambda x: parse_datetime(x.get("finish_time") or x.get("insert_time") or ""), reverse=True)
                ultima = umov_data[0]

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

        except Exception as e:
            print(f"[ERRO uMov.me - Pedido {p['transacao']}] {e}")

        # 📅 Formata data do pedido
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
        "SELECT * FROM pedidos WHERE cpf=%s AND loja=%s AND pedido=%s",
        (cpf, loja, pedido)
    )
    pedido_info = cursor.fetchone()
    if not pedido_info:
        cursor.close()
        conn.close()
        return jsonify({"error": "Pedido não encontrado"}), 404

    cursor.execute(
        "SELECT produto, quantidade, preco FROM produtos_pedidos WHERE loja=%s AND pedido=%s",
        (loja, pedido)
    )
    pedido_info["itens"] = cursor.fetchall()

    cursor.execute(
        """
        SELECT situacao, date, time
        FROM situacao_pedidos
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

    # 🔹 Etapas adicionais da API
    try:
        umov_data = fetch_entrega(pedido_info["transacao"])
        if umov_data:
            for entrega in umov_data:
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
        print(f"[ERRO uMov.me - Detalhes {pedido_info['transacao']}] {e}")

    pedido_info["etapas"] = sorted(etapas, key=lambda x: x["data_formatada"])

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
