from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from urllib.parse import quote

app = Flask(__name__)

app.secret_key = "pepinos_locos_123"


# ==========================================
# BASE DE DATOS
# ==========================================

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


# ==========================================
# PREPARAR TELÉFONO
# ==========================================

def preparar_telefono(telefono):

    if telefono is None:
        return None

    telefono = str(telefono).strip()

    # Quitar todo lo que no sea número
    telefono = "".join(
        caracter
        for caracter in telefono
        if caracter.isdigit()
    )

    # Aceptar EXACTAMENTE 8 números
    if len(telefono) != 8:
        return None

    # Agregar código de El Salvador
    return "503" + telefono


# ==========================================
# INICIO
# ==========================================

@app.route("/")
def inicio():

    return render_template("inicio.html")


# ==========================================
# CLIENTE
# ==========================================

@app.route("/cliente")
def menu_cliente():

    return render_template("cliente.html")


# ==========================================
# RECIBIR NOMBRE Y TELÉFONO
# ==========================================

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

    print("================================")
    print("TELEFONO RECIBIDO:", repr(telefono_original))
    print("CANTIDAD DE CARACTERES:", len(telefono_original))
    print("================================")

    telefono = preparar_telefono(
        telefono_original
    )

    # Si el teléfono no tiene exactamente 8 números
    if telefono is None:

        return render_template(
            "cliente.html",
            error="Debes escribir exactamente 8 números. Ejemplo: 78451234."
        )

    # Si está correcto, pasar al menú
    return render_template(
        "index.html",
        nombre=nombre,
        telefono=telefono
    )


# ==========================================
# CREAR PEDIDO
# ==========================================

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
    )

    try:

        cantidad = int(
            request.form.get(
                "cantidad",
                1
            )
        )

    except (ValueError, TypeError):

        cantidad = 1

    telefono = preparar_telefono(
        telefono_original
    )

    if telefono is None:

        return render_template(
            "cliente.html",
            error="Debes escribir exactamente 8 números. Ejemplo: 78451234."
        )

    # ==========================================
    # PRECIO
    # ==========================================

    if producto == "Pepino Loco":

        precio = 0.50

    else:

        precio = 0.75

    # ==========================================
    # TOTAL
    # ==========================================

    total = cantidad * precio

    # ==========================================
    # GUARDAR PEDIDO
    # ==========================================

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


# ==========================================
# LOGIN
# ==========================================

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


# ==========================================
# ADMIN
# ==========================================

@app.route("/admin")
def admin():

    if "dueño" not in session:

        return redirect(
            url_for("login")
        )

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


# ==========================================
# CONFIRMAR
# ==========================================

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


# ==========================================
# ELIMINAR
# ==========================================

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


# ==========================================
# FACTURA
# ==========================================

@app.route("/factura/<int:numero>")
def factura(numero):

    origen = request.args.get(
        "origen",
        "cliente"
    )

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


# ==========================================
# WHATSAPP
# ==========================================

@app.route("/whatsapp/<int:numero>")
def whatsapp(numero):

    if "dueño" not in session:

        return redirect(
            url_for("login")
        )

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


# ==========================================
# CONSULTA
# ==========================================

@app.route("/consulta")
def consulta():

    return render_template(
        "consulta.html"
    )


# ==========================================
# CONSULTAR PEDIDO
# ==========================================

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


# ==========================================
# CERRAR SESIÓN
# ==========================================

@app.route("/logout")
def logout():

    session.pop(
        "dueño",
        None
    )

    return redirect(
        url_for("inicio")
    )


# ==========================================
# INICIAR APLICACIÓN
# ==========================================

if __name__ == "__main__":

    crear_base_datos()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
