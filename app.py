import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import date, datetime
from flask import send_file
import io
from fpdf import FPDF
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
    fecha_actual = date.today()
    reporte = []

    # Para diario
    if tipo_reporte == "diario":
        fecha_sel = request.args.get('fecha', fecha_actual.strftime("%Y-%m-%d"))
        cursor.execute("SELECT id, nombre, apellido_p, apellido_m FROM personal")
        personal = cursor.fetchall()

        for p in personal:
            # Verificar asistencia del día
            cursor.execute("""
                SELECT tipo, hora FROM asistencia
                WHERE personal_id=%s AND fecha=%s
            """, (p[0], fecha_sel))
            asistencias = cursor.fetchall()

            horas_extra = sum([h[1].hour + h[1].minute/60 for h in asistencias if h[0]=='hora_extra'])
            dias_asistidos = 1 if asistencias else 0

            # Ver permisos
            cursor.execute("""
                SELECT COUNT(*) FROM permisos
                WHERE personal_id=%s AND fecha=%s
            """, (p[0], fecha_sel))
            permisos = cursor.fetchone()[0]

            reporte.append({
                'nombre': p[1],
                'apellido_p': p[2],
                'apellido_m': p[3],
                'dias_asistidos': dias_asistidos,
                'horas_extra': horas_extra,
                'permisos': permisos
            })

    # Para quincenal
    elif tipo_reporte == "quincenal":
        mes = int(request.args.get('mes_quincena', fecha_actual.month))
        quincena = int(request.args.get('quincena', 1))
        _, dias_mes = calendar.monthrange(fecha_actual.year, mes)
        dia_inicio = 1 if quincena == 1 else 16
        dia_fin = 15 if quincena == 1 else dias_mes

        cursor.execute("SELECT id, nombre, apellido_p, apellido_m FROM personal")
        personal = cursor.fetchall()

        for p in personal:
            # Asistencias quincenales
            cursor.execute("""
                SELECT COUNT(DISTINCT fecha) FROM asistencia
                WHERE personal_id=%s AND fecha BETWEEN %s AND %s
            """, (p[0], f"{fecha_actual.year}-{mes:02d}-{dia_inicio:02d}", f"{fecha_actual.year}-{mes:02d}-{dia_fin:02d}"))
            dias_asistidos = cursor.fetchone()[0]

            cursor.execute("""
                SELECT SUM(TIME_TO_SEC(hora))/3600 FROM asistencia
                WHERE personal_id=%s AND tipo='hora_extra' AND fecha BETWEEN %s AND %s
            """, (p[0], f"{fecha_actual.year}-{mes:02d}-{dia_inicio:02d}", f"{fecha_actual.year}-{mes:02d}-{dia_fin:02d}"))
            horas_extra = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM permisos
                WHERE personal_id=%s AND fecha BETWEEN %s AND %s
            """, (p[0], f"{fecha_actual.year}-{mes:02d}-{dia_inicio:02d}", f"{fecha_actual.year}-{mes:02d}-{dia_fin:02d}"))
            permisos = cursor.fetchone()[0]

            reporte.append({
                'nombre': p[1],
                'apellido_p': p[2],
                'apellido_m': p[3],
                'dias_asistidos': dias_asistidos,
                'horas_extra': round(horas_extra, 2),
                'permisos': permisos
            })

    # Para mensual
    elif tipo_reporte == "mensual":
        mes = int(request.args.get('mes_mensual', fecha_actual.month))
        _, dias_mes = calendar.monthrange(fecha_actual.year, mes)

        cursor.execute("SELECT id, nombre, apellido_p, apellido_m FROM personal")
        personal = cursor.fetchall()

        for p in personal:
            # Asistencias mensuales
            cursor.execute("""
                SELECT COUNT(DISTINCT fecha) FROM asistencia
                WHERE personal_id=%s AND MONTH(fecha)=%s AND YEAR(fecha)=%s
            """, (p[0], mes, fecha_actual.year))
            dias_asistidos = cursor.fetchone()[0]

            cursor.execute("""
                SELECT SUM(TIME_TO_SEC(hora))/3600 FROM asistencia
                WHERE personal_id=%s AND tipo='hora_extra' AND MONTH(fecha)=%s AND YEAR(fecha)=%s
            """, (p[0], mes, fecha_actual.year))
            horas_extra = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM permisos
                WHERE personal_id=%s AND MONTH(fecha)=%s AND YEAR(fecha)=%s
            """, (p[0], mes, fecha_actual.year))
            permisos = cursor.fetchone()[0]

            reporte.append({
                'nombre': p[1],
                'apellido_p': p[2],
                'apellido_m': p[3],
                'dias_asistidos': dias_asistidos,
                'horas_extra': round(horas_extra, 2),
                'permisos': permisos
            })

    return render_template("generar_reporte.html", personal=personal, reporte=reporte,
                           tipo_reporte=tipo_reporte, fecha_actual=fecha_actual)


# -------------------------------
# Iniciar servidor
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
