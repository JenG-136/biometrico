import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import date, datetime
from flask import send_file
import io
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import calendar


# -------------------------------
# Configuración Flask
# -------------------------------
app = Flask(__name__)
app.secret_key = "clave_secreta"

# Contraseña del administrador
ADMIN_PASSWORD = "admin123"

# Carpeta para guardar fotos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Conexión a la base de datos MySQL
# -------------------------------
db = mysql.connector.connect(
    host="localhost",
    user="biometrico_db",
    password="bio2527",
    database="biometrico_db"
)
cursor = db.cursor()

# -------------------------------
# Rutas principales
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin", methods=["POST"])
def admin_access():
    password = request.form.get("password")
    accion = request.form.get("accion")

    if password == ADMIN_PASSWORD:
        flash("Acceso concedido", "success")
        if accion == "agregar_personal":
            return redirect(url_for("agregar_personal"))
        elif accion == "ver_registros":
            return redirect(url_for("ver_registros"))
        elif accion == "ver_personal":
            return redirect(url_for("ver_personal"))
        elif accion == "generar_reporte":
            return redirect(url_for("generar_reporte"))
        else:
            return redirect(url_for("home"))
    else:
        flash("Contraseña incorrecta", "error")
        return redirect(url_for("home"))

# -------------------------------
# Página para agregar personal
# -------------------------------
@app.route("/agregar_personal")
def agregar_personal():
    return render_template("agregar_personal.html")

# -------------------------------
# Registrar un nuevo empleado
# -------------------------------
@app.route("/registrar_personal", methods=["POST"])
def registrar_personal():
    try:
        # Datos del formulario
        nombre = request.form['nombre']
        apellido_p = request.form['apellido_p']
        apellido_m = request.form['apellido_m']
        fecha_nac = request.form['fecha_nac']
        curp = request.form['curp']
        edad = request.form['edad']
        calle = request.form['calle']
        colonia = request.form['colonia']
        puesto = request.form['puesto']
        telefono = request.form['telefono']
        genero = request.form['genero']
        estatus = request.form['status']
        turno = request.form['turno']
        fecha_ingreso = request.form['fecha_ingreso']

        # Guardar foto
        foto = request.files['foto']
        nombre_foto = None
        if foto and foto.filename != '':
            filename = secure_filename(foto.filename)
            ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(ruta_completa)
            nombre_foto = filename

        # Insertar personal
        sql = """
            INSERT INTO personal (
                nombre, apellido_p, apellido_m, fecha_nac, curp, edad, calle,
                colonia, puesto, telefono, genero, estatus, turno, fecha_ingreso, foto
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            nombre, apellido_p, apellido_m, fecha_nac, curp, edad, calle,
            colonia, puesto, telefono, genero, estatus, turno, fecha_ingreso,
            nombre_foto
        )
        cursor.execute(sql, valores)
        db.commit()

        flash("Personal registrado exitosamente", "success")
        return redirect(url_for('ver_personal'))

    except Exception as e:
        db.rollback()
        flash(f"Error al registrar: {str(e)}", "danger")
        return redirect(url_for('agregar_personal'))

# -------------------------------
# Mostrar todo el personal
# -------------------------------
@app.route("/ver_personal")
def ver_personal():
    cursor.execute("SELECT * FROM personal")
    datos = cursor.fetchall()
    return render_template('ver_personal.html', personal=datos)

# -------------------------------
# Ver detalles de un empleado
# -------------------------------
@app.route("/detalle/<int:id>")
def detalle_personal(id):
    cursor.execute("SELECT * FROM personal WHERE id = %s", (id,))
    empleado = cursor.fetchone()
    if not empleado:
        flash("Empleado no encontrado", "warning")
        return redirect(url_for('ver_personal'))
    return render_template('detalle_personal.html', empleado=empleado)

# -------------------------------
# Editar información de un empleado
# -------------------------------
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_personal(id):
    if request.method == "GET":
        cursor.execute("SELECT * FROM personal WHERE id = %s", (id,))
        empleado = cursor.fetchone()
        if not empleado:
            flash("Empleado no encontrado", "warning")
            return redirect(url_for('ver_personal'))
        return render_template("editar_personal.html", empleado=empleado)

    if request.method == "POST":
        try:
            nombre = request.form['nombre']
            apellido_p = request.form['apellido_p']
            apellido_m = request.form['apellido_m']
            fecha_nac = request.form['fecha_nac']
            curp = request.form['curp']
            edad = request.form['edad']
            calle = request.form['calle']
            colonia = request.form['colonia']
            puesto = request.form['puesto']
            telefono = request.form['telefono']
            genero = request.form['genero']
            estatus = request.form['estatus']
            turno = request.form['turno']
            fecha_ingreso = request.form['fecha_ingreso']

            # Actualizar foto
            foto = request.files['foto']
            if foto and foto.filename != '':
                filename = secure_filename(foto.filename)
                ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(ruta_completa)
                nombre_foto = filename
            else:
                cursor.execute("SELECT foto FROM personal WHERE id = %s", (id,))
                nombre_foto = cursor.fetchone()[0]

            sql = """
                UPDATE personal SET 
                nombre=%s, apellido_p=%s, apellido_m=%s, fecha_nac=%s, curp=%s,
                edad=%s, calle=%s, colonia=%s, puesto=%s, telefono=%s,
                genero=%s, estatus=%s, turno=%s, fecha_ingreso=%s, foto=%s
                WHERE id=%s
            """
            valores = (
                nombre, apellido_p, apellido_m, fecha_nac, curp, edad, calle, colonia,
                puesto, telefono, genero, estatus, turno, fecha_ingreso, nombre_foto, id
            )
            cursor.execute(sql, valores)
            db.commit()

            flash("Empleado actualizado correctamente", "success")
            return redirect(url_for('ver_personal'))

        except Exception as e:
            db.rollback()
            flash(f"Error al actualizar: {str(e)}", "danger")
            return redirect(url_for('editar_personal', id=id))

# -------------------------------
# Eliminar un empleado
# -------------------------------
@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_personal(id):
    try:
        cursor.execute("DELETE FROM personal WHERE id = %s", (id,))
        db.commit()
        flash("Empleado eliminado correctamente", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for('ver_personal'))

# -------------------------------
# Ver registros de asistencia
# -------------------------------
@app.route("/ver_registros")
def ver_registros():
    # Obtener lista de empleados
    cursor.execute("SELECT id, nombre, apellido_p, apellido_m FROM personal")
    personal = cursor.fetchall()

    # Obtener registros solo del día actual
    cursor.execute("""
        SELECT p.id, p.nombre, p.apellido_p, p.apellido_m,
               MAX(CASE WHEN a.tipo='entrada_manana' THEN a.hora END) AS entrada_manana,
               MAX(CASE WHEN a.tipo='salida_comida' THEN a.hora END) AS salida_comida,
               MAX(CASE WHEN a.tipo='entrada_tarde' THEN a.hora END) AS entrada_tarde,
               MAX(CASE WHEN a.tipo='salida_tarde' THEN a.hora END) AS salida_tarde,
               SUM(CASE WHEN a.tipo='hora_extra' THEN a.hora ELSE 0 END) AS horas_extra
        FROM personal p
        LEFT JOIN asistencia a
            ON p.id = a.personal_id AND a.fecha = CURDATE()
        GROUP BY p.id, p.nombre, p.apellido_p, p.apellido_m
        ORDER BY p.nombre, p.apellido_p
    """)
    registros = cursor.fetchall()

    lista_registros = []
    for r in registros:
        lista_registros.append({
            'id': r[0],
            'nombre': r[1],
            'apellido_p': r[2],
            'apellido_m': r[3],
            'entrada_manana': r[4] if r[4] else '-',
            'salida_comida': r[5] if r[5] else '-',
            'entrada_tarde': r[6] if r[6] else '-',
            'salida_tarde': r[7] if r[7] else '-',
            'horas_extra': r[8] if r[8] else 0
        })

    # Fecha actual
    from datetime import date
    fecha_actual = date.today().strftime("%d/%m/%Y")

    return render_template("ver_registros.html", registros=lista_registros, personal=personal, fecha_actual=fecha_actual)

# -------------------------------
# Editar registro de asistencia
# -------------------------------
@app.route('/editar_registro', methods=["POST"])
def editar_registro():
    try:
        id_personal = request.form['id']
        entrada_manana = request.form.get('entrada_manana')
        salida_comida = request.form.get('salida_comida')
        entrada_tarde = request.form.get('entrada_tarde')
        salida_tarde = request.form.get('salida_tarde')

        for tipo, hora in [('entrada_manana', entrada_manana), ('salida_comida', salida_comida),
                           ('entrada_tarde', entrada_tarde), ('salida_tarde', salida_tarde)]:
            if hora:
                cursor.execute("""
                    INSERT INTO asistencia (personal_id, tipo, hora, fecha)
                    VALUES (%s, %s, %s, CURDATE())
                    ON DUPLICATE KEY UPDATE hora=%s
                """, (id_personal, tipo, hora, hora))

        db.commit()
        flash("Registro actualizado correctamente", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error al actualizar registro: {str(e)}", "danger")
    return redirect(url_for('ver_registros'))

# -------------------------------
# Agregar horas extra
# -------------------------------
@app.route("/agregar_extra", methods=["POST"])
def agregar_extra():
    try:
        id_personal = request.form['id']
        horas_extra = request.form['horas_extra']

        if horas_extra:
            cursor.execute("""
                INSERT INTO asistencia (personal_id, tipo, hora, fecha)
                VALUES (%s, 'hora_extra', %s, CURDATE())
            """, (id_personal, horas_extra))
            db.commit()
            flash("Horas extra agregadas correctamente", "success")
        else:
            flash("Debe ingresar las horas extra", "warning")
    except Exception as e:
        db.rollback()
        flash(f"Error al agregar horas extra: {str(e)}", "danger")
    return redirect(url_for('ver_registros'))


# -------------------------------
# Generar reporte día, quincenal y mensual
# -------------------------------
@app.route("/generar_reporte", methods=["GET"])
def generar_reporte():
    tipo_reporte = request.args.get('tipo_reporte', 'diario')
    mes = int(request.args.get('mes', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    quincena = int(request.args.get('quincena', 1))

    import calendar
    from collections import defaultdict

    calendario = defaultdict(list)
    reporte = []

    if tipo_reporte == 'diario':
        # Obtener todos los registros de asistencia del mes
        cursor.execute("""
            SELECT a.fecha, p.id, p.nombre, p.apellido_p, p.apellido_m,
                   MAX(CASE WHEN a.tipo='entrada_manana' THEN a.hora END) AS entrada_manana,
                   MAX(CASE WHEN a.tipo='salida_comida' THEN a.hora END) AS salida_comida,
                   MAX(CASE WHEN a.tipo='entrada_tarde' THEN a.hora END) AS entrada_tarde,
                   MAX(CASE WHEN a.tipo='salida_tarde' THEN a.hora END) AS salida_tarde,
                   SUM(CASE WHEN a.tipo='hora_extra' THEN a.hora ELSE 0 END) AS horas_extra
            FROM personal p
            LEFT JOIN asistencia a ON p.id = a.personal_id AND MONTH(a.fecha) = %s AND YEAR(a.fecha) = %s
            GROUP BY a.fecha, p.id, p.nombre, p.apellido_p, p.apellido_m
        """, (mes, year))
        registros = cursor.fetchall()

        for fila in registros:
            fecha_str = fila[0].strftime("%Y-%m-%d") if fila[0] else None
            if fecha_str:
                calendario[fecha_str].append({
                    'id': fila[1],
                    'nombre_completo': f"{fila[2]} {fila[3]} {fila[4]}",
                    'entrada_manana': str(fila[5]) if fila[5] else '-',
                    'salida_comida': str(fila[6]) if fila[6] else '-',
                    'entrada_tarde': str(fila[7]) if fila[7] else '-',
                    'salida_tarde': str(fila[8]) if fila[8] else '-',
                    'horas_extra': fila[9] if fila[9] else 0
                })

    else:
        # Reporte quincenal o mensual
        if tipo_reporte == 'quincenal':
            if quincena == 1:
                inicio = f"{year}-{mes:02d}-01"
                fin = f"{year}-{mes:02d}-15"
            else:
                ultimo_dia = calendar.monthrange(year, mes)[1]
                inicio = f"{year}-{mes:02d}-16"
                fin = f"{year}-{mes:02d}-{ultimo_dia}"
        else:
            inicio = f"{year}-{mes:02d}-01"
            ultimo_dia = calendar.monthrange(year, mes)[1]
            fin = f"{year}-{mes:02d}-{ultimo_dia}"

        cursor.execute("""
            SELECT p.nombre, p.apellido_p, p.apellido_m,
                   SUM(CASE WHEN a.tipo IN ('entrada_manana','entrada_tarde') THEN 1 ELSE 0 END) as dias_asistidos,
                   SUM(CASE WHEN a.tipo='permiso' THEN 1 ELSE 0 END) as permisos,
                   SUM(CASE WHEN a.tipo='hora_extra' THEN a.hora ELSE 0 END) as horas_extra
            FROM personal p
            LEFT JOIN asistencia a ON a.personal_id = p.id AND a.fecha BETWEEN %s AND %s
            GROUP BY p.id
        """, (inicio, fin))
        registros = cursor.fetchall()

        for r in registros:
            reporte.append({
                'nombre': r[0],
                'apellido_p': r[1],
                'apellido_m': r[2],
                'dias_asistidos': r[3] or 0,
                'permisos': r[4] or 0,
                'horas_extra': r[5] or 0
            })

    return render_template(
        "generar_reporte.html",
        tipo_reporte=tipo_reporte,
        calendario=calendario,
        mes=mes,
        year=year,
        quincena=quincena,
        reporte=reporte if tipo_reporte != 'diario' else [],
        calendar=calendar
    )


# -------------------------------
# Iniciar servidor
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
