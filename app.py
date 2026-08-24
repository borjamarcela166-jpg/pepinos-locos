from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from urllib.parse import quote

app = Flask(__name__)

app.secret_key = "pepinos_locos_123"


def conectar():
    conexion = sqlite3.connect("pepinos.db")
    conexion.row_factory = sqlite3.Row
    return conexion


def preparar_telefono(telefono):

    telefono = telefono.strip()

    telefono = "".join(
        caracter
        for caracter in telefono
        if caracter.isdigit()
    )

    # Si el cliente escribe solamente los 8 números
    if len(telefono) == 8:
        telefono = "503" + telefono

    # Comprobar que sea un número de El Salvador
    if len(telefono) == 11 and telefono.startswith("503"):
        return telefono

    return None


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

    nombre = request.form.get(
        "nombre",
        ""
    ).strip()

    telefono = request.form.get(
        "telefono",
        ""
    ).strip()

    telefono = preparar_telefono(telefono)

    if telefono is None:

        return """
        <h2>Número de teléfono inválido</h2>
        <p>Debes escribir exactamente 8 números.</p>
        <a href="/cliente">Volver</a>
        """

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

    telefono = request.form.get(
        "telefono",
        ""
    ).strip()

    producto = request.form.get(
        "producto",
        ""
    )

    cantidad = int(
        request.form.get(
            "cantidad",
            1
        )
    )

    telefono = preparar_telefono(telefono)

    if telefono is None:

        return """
        <h2>Número de teléfono inválido</h2>
        <p>Debes escribir exactamente 8 números.</p>
        <a href="/cliente">Volver</a>
        """

    if producto == "Pepino Loco":

        precio = 0.50

    else:

        precio = 0.75

    total = cantidad * precio

    conexion = conectar()

    cursor = conexion.execute("""
        INSERT INTO pedidos
        (
            nombre,
            telefono,
            producto,
            cantidad,
            total
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        nombre,
        telefono,
        producto,
        cantidad,
        total
    ))

    numero = cursor.lastrowid

    conexion.commit()
    conexion.close()

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

        if (
            usuario == "pepinos"
            and contraseña == "505"
        ):

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

    conexion = conectar()

    pedidos = conexion.execute(
        """
        SELECT *
        FROM pedidos
        ORDER BY numero DESC
        """
    ).fetchall()

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

    conexion.execute(
        """
        UPDATE pedidos
        SET confirmado = 1
        WHERE numero = ?
        """,
        (numero,)
    )

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

    conexion.execute(
        """
        DELETE FROM pedidos
        WHERE numero = ?
        """,
        (numero,)
    )

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

    conexion = conectar()

    pedido = conexion.execute(
        """
        SELECT *
        FROM pedidos
        WHERE numero = ?
        """,
        (numero,)
    ).fetchone()

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

    conexion = conectar()

    pedido = conexion.execute(
        """
        SELECT *
        FROM pedidos
        WHERE numero = ?
        """,
        (numero,)
    ).fetchone()

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

    numero = int(
        request.form["numero"]
    )

    conexion = conectar()

    pedido = conexion.execute(
        """
        SELECT *
        FROM pedidos
        WHERE numero = ?
        """,
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

    session.pop(
        "dueño",
        None
    )

    return redirect(
        url_for("inicio")
    )


if __name__ == "__main__":

    crear_base_datos()

    app.run(
        debug=True
    )
