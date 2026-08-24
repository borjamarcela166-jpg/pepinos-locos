from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from urllib.parse import quote
import os

app = Flask(__name__)

app.secret_key = "pepinos_locos_123"


# =========================================================
# BASE DE DATOS
# =========================================================

# Guardamos la base de datos junto al app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "pepinos.db")


def conectar():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row
    return conexion


# =========================================================
# CREAR BASE DE DATOS
# =========================================================

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

    # Revisar columnas existentes
    columnas = conexion.execute(
        "PRAGMA table_info(pedidos)"
    ).fetchall()

    nombres_columnas = [
        columna["name"]
        for columna in columnas
    ]

    # Agregar telefono si la base vieja no lo tiene
    if "telefono" not in nombres_columnas:

        conexion.execute("""
            ALTER TABLE pedidos
            ADD COLUMN telefono TEXT DEFAULT ''
        """)

    # Agregar confirmado si la base vieja no lo tiene
    if "confirmado" not in nombres_columnas:

        conexion.execute("""
            ALTER TABLE pedidos
            ADD COLUMN confirmado INTEGER DEFAULT 0
        """)

    conexion.commit()
    conexion.close()


# =========================================================
# IMPORTANTE PARA RENDER
# =========================================================

# Crear la tabla cuando Gunicorn importa app.py
crear_base_datos()


# =========================================================
# PREPARAR TELÉFONO
# =========================================================

def preparar_telefono(telefono):

    if not telefono:
        return None

    telefono = str(telefono).strip()

    # Quitar cualquier cosa que no sea número
    telefono = "".join(
        caracter
        for caracter in telefono
        if caracter.isdigit()
    )

    # Si ya viene con 503, quitarlo
    if telefono.startswith("503") and len(telefono) == 11:
        telefono = telefono[3:]

    # Deben quedar exactamente 8 números
    if len(telefono) != 8:
        return None

    # Números móviles válidos
    if telefono[0] not in "6789":
        return None

    # Código de país de El Salvador
    return "503" + telefono


# =========================================================
# INICIO
# =========================================================

@app.route("/")
def inicio():

    return render_template("inicio.html")


# =========================================================
# ÁREA DEL CLIENTE
# =========================================================

@app.route("/cliente")
def menu_cliente():

    return render_template("cliente.html")


# =========================================================
# RECIBIR NOMBRE Y TELÉFONO
# =========================================================

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
    print("PEDIDO DEL CLIENTE")
    print("NOMBRE:", nombre)
    print("TELEFONO RECIBIDO:", repr(telefono_original))
    print("CANTIDAD DE CARACTERES:", len(telefono_original))
    print("================================")

    telefono = preparar_telefono(
        telefono_original
    )

    print("TELEFONO PREPARADO:", repr(telefono))

    # Comprobar teléfono
    if telefono is None:

        return render_template(
            "cliente.html",
            error="Debes escribir exactamente 8 números. Ejemplo: 78451234."
        )

    # Mostrar productos
    return render_template(
        "index.html",
        nombre=nombre,
        telefono=telefono
    )


# =========================================================
# CREAR PEDIDO
# =========================================================

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

    print("================================")
    print("PEDIDO RECIBIDO")
    print("NOMBRE:", nombre)
    print("TELEFONO:", telefono_original)
    print("PRODUCTO:", producto)
    print("CANTIDAD:", cantidad_texto)
    print("================================")

    # Validar nombre
    if not nombre:

        return render_template(
            "cliente.html",
            error="Debes escribir tu nombre."
        )

    # Preparar teléfono
    telefono = preparar_telefono(
        telefono_original
    )

    # Validar teléfono
    if telefono is None:

        return render_template(
            "cliente.html",
            error="El número de teléfono no es válido."
        )

    # Validar producto
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

    # Convertir cantidad
    try:

        cantidad = int(cantidad_texto)

    except (ValueError, TypeError):

        cantidad = 1

    # Validar cantidad
    if cantidad < 1:

        cantidad = 1

    # =====================================================
    # PRECIO
    # =====================================================

    if producto == "Pepino Loco":

        precio = 0.50

    else:

        precio = 0.75

    # =====================================================
    # TOTAL
    # =====================================================

    total = cantidad * precio

    # =====================================================
    # GUARDAR EN BASE DE DATOS
    # =====================================================

    try:

        conexion = conectar()

        # Asegurarnos nuevamente de que exista la tabla
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

        print("================================")
        print("ERROR AL GUARDAR PEDIDO")
        print(error)
        print("================================")

        try:
            conexion.close()
        except:
            pass

        return """
        <h1>Error al guardar el pedido</h1>
        <p>Ocurrió un problema con la base de datos.</p>
        <p>Revisa los logs de Render.</p>
        <a href="/cliente">Volver al área del cliente</a>
        """

    # =====================================================
    # INFORMACIÓN DEL PEDIDO
    # =====================================================

    pedido_nuevo = {

        "numero": numero,

        "nombre": nombre,

        "telefono": telefono,

        "producto": producto,

        "cantidad": cantidad,

        "total": total,

        "confirmado": 0
    }

    # =====================================================
    # MOSTRAR PEDIDO
    # =====================================================

    return render_template(
        "pedido.html",
        pedido=pedido_nuevo
    )


# =========================================================
# LOGIN DEL DUEÑO
# =========================================================

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


# =========================================================
# PANEL DEL DUEÑO
# =========================================================

@app.route("/admin")
def admin():

    if "dueño" not in session:

        return redirect(
            url_for("login")
        )

    # Asegurar que exista la base
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


# =========================================================
# CONFIRMAR PEDIDO
# =========================================================

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


# =========================================================
# ELIMINAR PEDIDO
# =========================================================

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


# =========================================================
# FACTURA
# =========================================================

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


# =========================================================
# WHATSAPP
# =========================================================

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


# =========================================================
# CONSULTAR PEDIDO
# =========================================================

@app.route("/consulta")
def consulta():

    return render_template(
        "consulta.html"
    )


# =========================================================
# BUSCAR PEDIDO
# =========================================================

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


# =========================================================
# CERRAR SESIÓN
# =========================================================

@app.route("/logout")
def logout():

    session.pop(
        "dueño",
        None
    )

    return redirect(
        url_for("inicio")
    )


# =========================================================
# INICIAR FLASK
# =========================================================

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
