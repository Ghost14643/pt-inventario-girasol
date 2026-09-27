import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import hashlib
import hmac

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("Configura FLASK_SECRET_KEY")
UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def hashear_contraseña(contraseña):
    hash_obj = hashlib.sha256(contraseña.encode('utf-8'))
    return hash_obj.hexdigest()


# Conexión única a MariaDB del proyecto. El esquema canónico es el definido en
# docker/mariadb/init/01-create-db.sql y 02-new-schema.sql.
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mariadb"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "app_user"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "tienda_online")
    )

@app.route('/')
def index():
    # Si el usuario ya está en sesión, mostrar index
    if "username" in session:
        return render_template("index.html", username=session["username"])
    # Si no, redirigir al login
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT rut_usuario, password FROM usuario WHERE rut_usuario = %s",
            (int(username),),
        )
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        if usuario and hmac.compare_digest(str(usuario["password"]), hashear_contraseña(password)):
            session["username"] = str(usuario["rut_usuario"])
            return redirect(url_for("index"))
        return "Usuario o contraseña incorrectos"

    if "username" in session:
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)  # Eliminar sesión
    return redirect(url_for("login"))

#------------------------------------------------
#        dashboard
#------------------------------------------------

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
    

@app.route("/api/summary")
def api_summary():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(v.total), 0) AS revenue,
            COUNT(v.id_venta) AS orders,
            COALESCE(SUM(dv.cantidad), 0) AS units
        FROM venta v
        LEFT JOIN detalle_venta dv ON dv.id_venta = v.id_venta
        WHERE DATE(v.fecha) = %s
        """,
        (today,),
    )
    row = cursor.fetchone() or {"revenue": 0, "orders": 0, "units": 0}
    cursor.close()
    conn.close()

    revenue = float(row["revenue"] or 0)
    orders = int(row["orders"] or 0)
    units = int(row["units"] or 0)
    avg_ticket = revenue / orders if orders else 0
    return jsonify({
        "revenue": {"value": revenue, "delta": 0},
        "orders": {"value": orders, "delta": 0},
        "units": {"value": units, "delta": 0},
        "avg_ticket": {"value": avg_ticket, "delta": 0},
    })


@app.route("/api/weekly")
def api_weekly():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT DATE(v.fecha) AS day,
               ROUND(SUM(v.total), 2) AS revenue
        FROM venta v
        WHERE v.fecha >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY DATE(v.fecha)
        ORDER BY DATE(v.fecha)
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)
#------------------------------------------------
@app.route('/roles', methods=['POST', 'GET'])
def roles():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT nombre, id_rol
        FROM usuario
        ORDER BY nombre;
    """)

    usuario = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('roles2.html', usuario=usuario)


@app.route('/guardar_usuario', methods=['POST'])
def guardar_usuario():

    data = request.get_json()

    rut= data ['rut']
    dv= data['dv']
    usuario = data['usuario']
    rol = data['rol']
    password = data['password']
    modo = data['modo']

    psshash=hashear_contraseña(password)

    conn = get_connection()
    cursor = conn.cursor()

    if modo == "nuevo":
        cursor.execute(
            """
            INSERT INTO usuario (rut_usuario, dvrut_usuario, nombre, id_rol, password)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (int(rut), str(dv), usuario, int(rol), psshash),
        )
    else:
        if password != "":
            cursor.execute(
                """
                UPDATE usuario
                SET password=%s, id_rol=%s
                WHERE nombre=%s
                """,
                (psshash, int(rol), usuario),
            )
        else:
            cursor.execute(
                """
                UPDATE usuario
                SET id_rol=%s
                WHERE nombre=%s
                """,
                (int(rol), usuario),
            )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"mensaje":"Guardado correctamente"})


@app.route('/facturas', methods =['GET', 'POST'])
def facturas():
    return render_template('subir_factura.html')

@app.route('/subir_factura', methods=['POST', 'GET'])
def subir_factura():
    if 'factura' not in request.files:
        return "No se seleccionó archivo"

    file = request.files['factura']
    if file.filename == '':
        return "Nombre de archivo vacío"

    # Guardar archivo en carpeta local
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Guardar referencia en MySQL
    conn = get_connection()
    cursor = conn.cursor()
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO factura (imagen, fecha_subida) VALUES (%s, %s)", (file.filename, fecha))
    conn.commit()
    cursor.close()
    conn.close()

    return render_template('subir_factura.html')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)

