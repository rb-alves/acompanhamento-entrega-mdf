from flask import Flask, jsonify, request, render_template
import mysql.connector
from datetime import datetime

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
# 🌐 Rotas de páginas
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# 🧾 API /api/pedidos — retorna pedidos + seus produtos
# ============================================================
@app.route("/api/pedidos")
def pedidos():
    cpf = request.args.get("cpf")

    if not cpf:
        return jsonify({"error": "CPF não informado"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 1) Busca os pedidos do cliente
    query_pedidos = """
        SELECT 
        *
        FROM pedidos
        WHERE cpf = %s
        ORDER BY pedido DESC
    """
    cursor.execute(query_pedidos, (cpf,))
    pedidos = cursor.fetchall()

    # 🔹 2) Busca todos os produtos dos pedidos desse CPF
    query_itens = """
        SELECT 
            pp.loja,
            pp.pedido,
            pp.item,
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

    # 🔹 3) Agrupa os itens por pedido (loja + pedido)
    itens_por_pedido = {}
    for item in itens:
        chave = f"{item['loja']}-{item['pedido']}"
        if chave not in itens_por_pedido:
            itens_por_pedido[chave] = []
        itens_por_pedido[chave].append({
            "item": item["item"],
            "quantidade": item["quantidade"],
            "preco": item["preco"]
        })

    # 🔹 4) Anexa os itens dentro de cada pedido
    for p in pedidos:
        # Formata a data e hora
        data_str = str(p["data"])
        if len(data_str) == 8:
            p["data"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")


        # Adiciona itens
        chave = f"{p['loja']}-{p['pedido']}"
        p["itens"] = itens_por_pedido.get(chave, [])

    cursor.close()
    conn.close()

    return jsonify(pedidos)

# ============================================================
# 🧾 API /api/Detalhes — retorna detalhes do pedido
# ============================================================
@app.route("/api/detalhes")
def detalhes():
    cpf = request.args.get("cpf")
    loja = request.args.get("loja")
    pedido = request.args.get("pedido")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Busca pedido
    query_pedido = """
        SELECT * FROM pedidos
        WHERE cpf=%s
            AND loja=%s
            AND pedido=%s
    """

    cursor.execute(query_pedido, (cpf, loja, pedido))
    pedido_info = cursor.fetchone()

    if not pedido_info:
        return jsonify({"error": "Pedido não encontrado"}), 404
    
    # Busca ítens
    query_itens = """
        SELECT 
            item,
            quantidade,
            preco 
        FROM produtos_pedidos
        WHERE loja=%s AND pedido=%s
    """
    cursor.execute(query_itens, (loja, pedido))
    itens = cursor.fetchall()
    pedido_info["itens"] = itens

    data_str = str(pedido_info.get("data"))
    if data_str and len(data_str) == 8:
        pedido_info["data"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")

    cursor.close()
    conn.close()
    
    return jsonify(pedido_info)

# ============================================================
# 🚀 Iniciar o servidor
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
