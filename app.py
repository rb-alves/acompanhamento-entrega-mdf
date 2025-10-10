from flask import Flask, jsonify, request, render_template
import mysql.connector

app = Flask(__name__)

# Conexão com o banco de dados
def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="mdf@123",
        database="pedidos"
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/detalhes")
def detalhes():
    return render_template("detalhes.html")

@app.route("/api/pedidos")
def pedidos():
    cpf = request.args.get("cpf")

    if not cpf:
        return jsonify({"error": "CPF não informado"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT * FROM pedidos.pedidos
        WHERE cpf = %s
    """
    cursor.execute(query, (cpf,))
    pedidos = cursor.fetchall()


    cursor.close()
    conn.close()

    return jsonify(pedidos)

if __name__ == "__main__":
    app.run(debug=True)
