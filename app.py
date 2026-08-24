from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from urllib.parse import quote
import os

app = Flask(__name__)

app.secret_key = "pepinos_locos_123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "pepinos.db")


def conectar():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_base_datos():

    conexion = conectar()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            numero INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL,
            confirmado INTEGER DEFAULT 0
        )
    """)

    columnas = conexion.execute(
        "PRAGMA table_info(pedidos)"
    ).fetchall()

    nombres_columnas = [
        columna["name"]
        for columna in columnas
    ]

    if "telefono" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE pedidos
            ADD COLUMN telefono TEXT DEFAULT ''
        """)

    if "confirmado" not in nombres_columnas:
        conexion.execute("""
            ALTER TABLE pedidos
            ADD COLUMN confirmado INTEGER DEFAULT 0
        """)

    conexion.commit()
    conexion.close()


crear_base_datos()


def preparar_telefono(telefono):

    if not telefono:
        return None

    telefono = str(telefono).strip()

    telefono = "".join(
        caracter
        for caracter in telefono
        if caracter.isdigit()
    )

    if telefono.startswith("503") and len(telefono) == 11:
        telefono = telefono[3:]

    if len(telefono) != 8:
        return None

    if telefono[0] not in "6789":
        return None

    return "503" + telefono


@app.route("/")
def inicio():
    return render_template("inicio.html")


@app.route("/cliente")
def menu_cliente():
    return render_template("cliente.html")


@app.route("/menu", methods=["POST"])
def menu():

    nombre = request.form.get(
        "nombre",
        ""
    ).strip()

    telefono_original = request.form.get(
        "telefono",
        ""
    ).strip()

    telefono = preparar_telefono(
        telefono_original
    )

    if telefono is None:
        return render_template(
            "cliente.html",
            error="Debes escribir exactamente 8 números. Ejemplo: 78451234."
        )

    return render_template(
        "index.html",
        nombre=nombre,
        telefono=telefono
    )


@app.route("/pedido", methods=["POST"])
def pedido():

    nombre = request.form.get(
        "nombre",
        ""
    ).strip()

    telefono_original = request.form.get(
        "telefono",
        ""
    ).strip()

    producto = request.form.get(
        "producto",
        ""
    ).strip()

    cantidad_texto = request.form.get(
        "cantidad",
        "1"
    )

    if not nombre:
        return render_template(
            "cliente.html",
            error="Debes escribir tu nombre."
        )

    telefono = preparar_telefono(
        telefono_original
    )

    if telefono is None:
        return render_template(
            "cliente.html",
            error="El número de teléfono no es válido."
        )

    if producto not in [
        "Pepino Loco",
        "Pepino Loco con Gomitas"
    ]:
        return render_template(
            "index.html",
            nombre=nombre,
            telefono=telefono,
            error="Debes seleccionar un producto."
        )

    try:
        cantidad = int(cantidad_texto)
    except (ValueError, TypeError):
        cantidad = 1

    if cantidad < 1:
        cantidad = 1

    if producto == "Pepino Loco":
        precio = 0.50
    else:
        precio = 0.75

    total = cantidad * precio

    try:

        conexion = conectar()

        crear_base_datos()

        cursor = conexion.execute("""
            INSERT INTO pedidos
            (
                nombre,
                telefono,
                producto,
                cantidad,
                total,
                confirmado
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nombre,
            telefono,
            producto,
            cantidad,
            total,
            0
        ))

        numero = cursor.lastrowid

        conexion.commit()
        conexion.close()

    except Exception as error:

        print(error)

        try:
            conexion.close()
        except:
            pass

        return """
        <h1>Error al guardar el pedido</h1>
        <p>Ocurrió un problema con la base de datos.</p>
        <a href="/cliente">Volver al área del cliente</a>
        """

    pedido_nuevo = {
        "numero": numero,
        "nombre": nombre,
        "telefono": telefono,
        "producto": producto,
        "cantidad": cantidad,
        "total": total,
        "confirmado": 0
    }

    return render_template(
        "pedido.html",
        pedido=pedido_nuevo
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        )

        contraseña = request.form.get(
            "contraseña",
            ""
        )

        if usuario == "pepinos" and contraseña == "505":

            session["dueño"] = True

            return redirect(
                url_for("admin")
            )

        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos"
        )

    return render_template(
        "login.html"
    )


@app.route("/admin")
def admin():

    if "dueño" not in session:
        return redirect(
            url_for("login")
        )

    crear_base_datos()

    conexion = conectar()

    pedidos = conexion.execute("""
        SELECT *
        FROM pedidos
        ORDER BY numero DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "admin.html",
        pedidos=pedidos
    )


@app.route(
    "/confirmar/<int:numero>",
    methods=["POST"]
)
def confirmar(numero):

    if "dueño" not in session:
        return redirect(
            url_for("login")
        )

    conexion = conectar()

    conexion.execute("""
        UPDATE pedidos
        SET confirmado = 1
        WHERE numero = ?
    """, (
        numero,
    ))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for("admin")
    )


@app.route(
    "/eliminar/<int:numero>",
    methods=["POST"]
)
def eliminar(numero):

    if "dueño" not in session:
        return redirect(
            url_for("login")
        )

    conexion = conectar()

    conexion.execute("""
        DELETE FROM pedidos
        WHERE numero = ?
    """, (
        numero,
    ))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for("admin")
    )


@app.route("/factura/<int:numero>")
def factura(numero):

    origen = request.args.get(
        "origen",
        "cliente"
    )

    crear_base_datos()

    conexion = conectar()

    pedido = conexion.execute("""
        SELECT *
        FROM pedidos
        WHERE numero = ?
    """, (
        numero,
    )).fetchone()

    conexion.close()

    if pedido is None:
        return "Pedido no encontrado"

    mensaje = (
        "PEPINOS LOCOS\n"
        "================================\n"
        "FACTURA DE COMPRA\n"
        "================================\n\n"
        f"Numero de pedido: #{pedido['numero']}\n"
        f"Cliente: {pedido['nombre']}\n"
        f"Telefono: {pedido['telefono']}\n\n"
        "DETALLE DEL PEDIDO\n"
        "--------------------------------\n"
        f"Producto: {pedido['producto']}\n"
        f"Cantidad: {pedido['cantidad']}\n"
        f"Total: ${pedido['total']:.2f}\n"
        "--------------------------------\n\n"
        f"TOTAL A PAGAR: ${pedido['total']:.2f}\n\n"
        "================================\n"
        "Gracias por comprar en Pepinos Locos.\n"
        "Esperamos que disfrutes tu pedido."
    )

    enlace_whatsapp = (
        f"https://wa.me/{pedido['telefono']}"
        f"?text={quote(mensaje)}"
    )

    return render_template(
        "factura.html",
        pedido=pedido,
        origen=origen,
        enlace_whatsapp=enlace_whatsapp
    )


@app.route("/whatsapp/<int:numero>")
def whatsapp(numero):

    if "dueño" not in session:
        return redirect(
            url_for("login")
        )

    crear_base_datos()

    conexion = conectar()

    pedido = conexion.execute("""
        SELECT *
        FROM pedidos
        WHERE numero = ?
    """, (
        numero,
    )).fetchone()

    conexion.close()

    if pedido is None:
        return "Pedido no encontrado"

    telefono = pedido["telefono"]

    if not telefono:
        return "Este pedido no tiene teléfono guardado."

    mensaje = (
        "PEPINOS LOCOS\n"
        "================================\n"
        "FACTURA DE COMPRA\n"
        "================================\n\n"
        f"Numero de pedido: #{pedido['numero']}\n"
        f"Cliente: {pedido['nombre']}\n"
        f"Telefono: {pedido['telefono']}\n\n"
        "DETALLE DEL PEDIDO\n"
        "--------------------------------\n"
        f"Producto: {pedido['producto']}\n"
        f"Cantidad: {pedido['cantidad']}\n"
        f"Total: ${pedido['total']:.2f}\n"
        "--------------------------------\n\n"
        f"TOTAL A PAGAR: ${pedido['total']:.2f}\n\n"
        "================================\n"
        "Gracias por comprar en Pepinos Locos.\n"
        "Esperamos que disfrutes tu pedido."
    )

    enlace_whatsapp = (
        f"https://wa.me/{telefono}"
        f"?text={quote(mensaje)}"
    )

    return redirect(
        enlace_whatsapp
    )


@app.route("/consulta")
def consulta():

    return render_template(
        "consulta.html"
    )


@app.route(
    "/consultar",
    methods=["POST"]
)
def consultar():

    try:

        numero = int(
            request.form["numero"]
        )

    except (ValueError, KeyError):

        return render_template(
            "consulta.html",
            error="Escribe un número de pedido válido."
        )

    crear_base_datos()

    conexion = conectar()

    pedido = conexion.execute("""
        SELECT *
        FROM pedidos
        WHERE numero = ?
    """, (
        numero,
    )).fetchone()

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

    session.pop(
        "dueño",
        None
    )

    return redirect(
        url_for("inicio")
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )
