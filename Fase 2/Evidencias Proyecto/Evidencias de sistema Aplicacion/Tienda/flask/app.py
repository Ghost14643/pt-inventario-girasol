import os
import mysql.connector
import sqlite3
from flask import Flask, render_template, request, redirect, url_for,session,jsonify
from datetime import datetime, timedelta
#from werkzeug.security import check_password_hash       
import hashlib
import hmac
#Isa podrias borrar en la template de dashboard los top items y las recent sales?
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("Configura FLASK_SECRET_KEY")
UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_PATH = os.getenv("GIRASOL_DB_PATH", "reuso.db")

def hashear_contraseña(contraseña):
    hash_obj = hashlib.sha256(contraseña.encode('utf-8'))
    return hash_obj.hexdigest()

# Conexión a MySQL
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mariadb"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "app_user"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "tienda_online")
    )
def get_sqlite():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

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
        cursor.execute("SELECT RUT, PASSWORD FROM usuario WHERE RUT = %s", (username,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        # Validación con hash
        if usuario and hmac.compare_digest(str(usuario["PASSWORD"]), hashear_contraseña(password)):
            session["username"] = username
            return redirect(url_for("index"))
        else:
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
    con = get_sqlite()
    today     = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    def stats(date):
        r = con.execute("""
            SELECT
                COALESCE(SUM(b.totalFinal), 0)       AS revenue,
                COUNT(DISTINCT b.idBoleta)            AS orders,
                COALESCE(SUM(db.cantidad), 0)         AS units
            FROM boleta b
            INNER JOIN detalleBoleta db
                ON b.idBoleta = db.idBoleta
            WHERE b.fechaHora LIKE ?
        """, (date + "%",)).fetchone()
        return dict(r)

    t, y = stats(today), stats(yesterday)
    con.close()

    def pct(a, b):
        return round((a - b) / b * 100, 1) if b else 0

    return jsonify({
        "revenue":    {"value": round(t["revenue"], 2),  "delta": pct(t["revenue"],  y["revenue"])},
        "orders":     {"value": t["orders"],              "delta": pct(t["orders"],   y["orders"])},
        "units":      {"value": t["units"],               "delta": pct(t["units"],    y["units"])},
        "avg_ticket": {"value": round(t["revenue"] / t["orders"], 2) if t["orders"] else 0,
                       "delta": 0},
    })



@app.route("/api/weekly")
def api_weekly():
    con = get_sqlite()
    rows = con.execute("""
        SELECT 
            DATE(fechaHora) AS day,
            ROUND(SUM(totalFinal),2) AS revenue
        FROM boleta
        WHERE fechaHora >= DATE('now','-6 days')
        GROUP BY day
        ORDER BY day
    """).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])
#------------------------------------------------
@app.route('/roles', methods=['POST', 'GET'])
def roles():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT nombre, id_rol
        FROM usuario;
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

        cursor.execute("""
        insert into usuario (rut, digito_ver, nombre, id_rol, password)
        VALUES(%s,%s,%s,%s,%s)
        """,(rut,dv,usuario,rol,psshash,))

    else:

        if password != "":
            cursor.execute("""
            UPDATE usuario
            SET password=%s, id_rol=%s
            WHERE nombre=%s
            """,(psshash,rol,usuario))
        else:
            cursor.execute("""
            UPDATE usuario
            SET id_rol=%s
            WHERE nombre=%s
            """,(rol,usuario))

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

