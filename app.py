from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)

app.secret_key = "pepinos_locos_123"


def conectar():
    conexion = sqlite3.connect("pepinos.db")
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_base_datos():
    conexion = conectar()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            numero INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL,
            confirmado INTEGER DEFAULT 0
        )
    """)

    conexion.commit()
    conexion.close()


@app.route("/")
def inicio():
    return render_template("inicio.html")


@app.route("/cliente")
def menu_cliente():
    return render_template("cliente.html")


@app.route("/menu", methods=["POST"])
def menu():
    nombre = request.form["nombre"]

    return render_template(
        "index.html",
        nombre=nombre
    )


@app.route("/pedido", methods=["POST"])
def pedido():

    nombre = request.form["nombre"]
    producto = request.form["producto"]
    cantidad = int(request.form["cantidad"])

    if producto == "Pepino Loco":
        precio = 0.50
    else:
        precio = 0.75

    total = cantidad * precio

    conexion = conectar()

    cursor = conexion.execute("""
        INSERT INTO pedidos
        (nombre, producto, cantidad, total)
        VALUES (?, ?, ?, ?)
    """, (nombre, producto, cantidad, total))

    numero = cursor.lastrowid

    conexion.commit()
    conexion.close()

    pedido_nuevo = {
        "numero": numero,
        "nombre": nombre,
        "producto": producto,
        "cantidad": cantidad,
        "total": total,
        "confirmado": False
    }

    return render_template(
        "pedido.html",
        pedido=pedido_nuevo
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        if usuario == "pepinos" and contraseña == "505":
            session["dueño"] = True
            return redirect(url_for("admin"))

        else:
            return render_template(
                "login.html",
                error="Usuario o contraseña incorrectos"
            )

    return render_template("login.html")


@app.route("/admin")
def admin():

    if "dueño" not in session:
        return redirect(url_for("login"))

    conexion = conectar()

    pedidos = conexion.execute(
        "SELECT * FROM pedidos ORDER BY numero DESC"
    ).fetchall()

    conexion.close()

    return render_template(
        "admin.html",
        pedidos=pedidos
    )


@app.route("/confirmar/<int:numero>", methods=["POST"])
def confirmar(numero):

    if "dueño" not in session:
        return redirect(url_for("login"))

    conexion = conectar()

    conexion.execute("""
        UPDATE pedidos
        SET confirmado = 1
        WHERE numero = ?
    """, (numero,))

    conexion.commit()
    conexion.close()

    return redirect(url_for("admin"))


@app.route("/eliminar/<int:numero>", methods=["POST"])
def eliminar(numero):

    if "dueño" not in session:
        return redirect(url_for("login"))

    conexion = conectar()

    conexion.execute(
        "DELETE FROM pedidos WHERE numero = ?",
        (numero,)
    )

    conexion.commit()
    conexion.close()

    return redirect(url_for("admin"))


@app.route("/factura/<int:numero>")
def factura(numero):

    origen = request.args.get("origen", "cliente")

    conexion = conectar()

    pedido = conexion.execute(
        "SELECT * FROM pedidos WHERE numero = ?",
        (numero,)
    ).fetchone()

    conexion.close()

    if pedido is None:
        return "Pedido no encontrado"

    return render_template(
        "factura.html",
        pedido=pedido,
        origen=origen
    )


@app.route("/consulta")
def consulta():
    return render_template("consulta.html")


@app.route("/consultar", methods=["POST"])
def consultar():

    numero = int(request.form["numero"])

    conexion = conectar()

    pedido = conexion.execute(
        "SELECT * FROM pedidos WHERE numero = ?",
        (numero,)
    ).fetchone()

    conexion.close()

    if pedido is None:
        return render_template(
            "consulta.html",
            error="No encontramos ese pedido."
        )

    return render_template(
        "estado.html",
        pedido=pedido
    )


@app.route("/logout")
def logout():

    session.pop("dueño", None)

    return redirect(url_for("inicio"))


if __name__ == "__main__":
    crear_base_datos()
    app.run(debug=True)