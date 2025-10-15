import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import date, datetime
from flask import send_file
import io
from io import BytesIO
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import calendar
from collections import defaultdict
import calendar
from datetime import datetime, date, timedelta


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
try:
    db = mysql.connector.connect(
        host="localhost",
        user="biometrico_db",
        password="bio2527",
        database="biometrico_db"
    )
    cursor = db.cursor(dictionary=True)  # cursor devuelve diccionarios
    print("✅ Conexión exitosa")
except mysql.connector.Error as err:
    print("❌ Error de conexión:", err)

# -------------------------------
# Rutas principales
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# Ruta para buscar empleado (simulación de huella)
@app.route('/buscar_empleado', methods=['POST'])
def buscar_empleado():
    id_huella = request.json.get('id_huella', 3)
    cursor.execute("SELECT * FROM personal WHERE id = %s", (id_huella,))
    empleado = cursor.fetchone()
    if not empleado:
        return jsonify({"error": "Empleado no encontrado"}), 404

    hora_actual = datetime.now().strftime("%H:%M:%S")

    # Determinar tipo de registro según horario
    hora_dt = datetime.strptime(hora_actual, "%H:%M:%S")
    if hora_dt < datetime.strptime("14:00:00", "%H:%M:%S"):
        tipo = "entrada_manana"
    elif hora_dt < datetime.strptime("16:00:00", "%H:%M:%S"):
        tipo = "salida_comida"
    elif hora_dt < datetime.strptime("19:00:00", "%H:%M:%S"):
        tipo = "entrada_tarde"
    else:
        tipo = "salida_tarde"

    # Insertar o actualizar registro del día
    cursor.execute("""
        INSERT INTO asistencia (personal_id, tipo, hora, fecha)
        VALUES (%s, %s, %s, CURDATE())
        ON DUPLICATE KEY UPDATE hora=%s
    """, (id_huella, tipo, hora_actual, hora_actual))
    db.commit()

    retraso_min = max(0, int((hora_dt - datetime.strptime("09:00:00", "%H:%M:%S")).total_seconds() / 60))

    return jsonify({
        "nombre": empleado['nombre'],
        "puesto": empleado['puesto'],
        "foto": empleado['foto'],
        "hora": hora_actual,
        "tipo": tipo,
        "retraso": f"{retraso_min} min" if retraso_min > 0 else "A tiempo"
    })



#acceso de administrador
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

        #Validación: Turno 2 exclusivo para policías 
        if turno == "turno2" and puesto.strip().lower() != "policía":
            flash("El turno 2 es exclusivo para pilicías.", "danger")
            return redirect(url_for('agregar_personal'))

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
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM personal 
        ORDER BY puesto, apellido_p, apellido_m, nombre
    """)
    personal = cursor.fetchall()
    return render_template("ver_personal.html", personal=personal)


# -------------------------------
# Ver detalles de un empleado
# -------------------------------
@app.route("/detalle/<int:id>")
def detalle_personal(id):
    cursor.execute("SELECT * FROM personal WHERE id = %s", (id,))
    empleado = cursor.fetchone()  # ya devuelve un diccionario
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
    cursor.execute("SELECT id, nombre, apellido_p, apellido_m, puesto FROM personal")
    personal = cursor.fetchall()  # ahora es lista de diccionarios

    # Obtener registros solo del día actual
    cursor.execute("""
        SELECT p.id, p.nombre, p.apellido_p, p.apellido_m, p.puesto,
               MAX(CASE WHEN a.tipo='entrada_manana' THEN a.hora END) AS entrada_manana,
               MAX(CASE WHEN a.tipo='salida_comida' THEN a.hora END) AS salida_comida,
               MAX(CASE WHEN a.tipo='entrada_tarde' THEN a.hora END) AS entrada_tarde,
               MAX(CASE WHEN a.tipo='salida_tarde' THEN a.hora END) AS salida_tarde,
               SUM(CASE WHEN a.tipo='hora_extra' THEN a.hora ELSE 0 END) AS horas_extra
        FROM personal p
        LEFT JOIN asistencia a
            ON p.id = a.personal_id AND a.fecha = CURDATE()
        GROUP BY p.id, p.nombre, p.apellido_p, p.apellido_m, p.puesto
        ORDER BY p.nombre, p.apellido_p
    """)
    registros = cursor.fetchall()  # lista de diccionarios

    lista_registros = []
    hoy = datetime.today()
    dia_semana = hoy.weekday()  # 0=lunes, ..., 5=sábado, 6=domingo

    for r in registros:
        puesto = r['puesto'].lower()
        
        if dia_semana == 6 and puesto != "policía":  # Domingo y no es policía
            entrada_manana = salida_comida = entrada_tarde = salida_tarde = "No laboral"
        elif dia_semana == 5 and puesto != "policía":  # Sábado
            entrada_manana = r['entrada_manana'] if r['entrada_manana'] else "-"
            salida_comida = r['salida_comida'] if r['salida_comida'] else "13:00"  # salida directa a la 1
            entrada_tarde = "-"
            salida_tarde = "-"
        else:  # Lunes a viernes o policía
            entrada_manana = r['entrada_manana'] if r['entrada_manana'] else "-"
            salida_comida = r['salida_comida'] if r['salida_comida'] else "-"
            entrada_tarde = r['entrada_tarde'] if r['entrada_tarde'] else "-"
            salida_tarde = r['salida_tarde'] if r['salida_tarde'] else "-"

        lista_registros.append({
            'id': r['id'],
            'nombre': r['nombre'],
            'apellido_p': r['apellido_p'],
            'apellido_m': r['apellido_m'],
            'entrada_manana': entrada_manana,
            'salida_comida': salida_comida,
            'entrada_tarde': entrada_tarde,
            'salida_tarde': salida_tarde,
            'horas_extra': r['horas_extra'] if r['horas_extra'] else 0
        })

    fecha_actual = date.today().strftime("%d/%m/%Y")

    return render_template("ver_registros.html", registros=lista_registros, personal=personal, fecha_actual=fecha_actual)

#-------------------------------
#Editar registro de asistencia
#-------------------------------
@app.route('/editar_registro', methods=["POST"])
def editar_registro():
    try:
        id_personal = request.form['id']
        entrada_manana = request.form.get('entrada_manana')
        salida_comida = request.form.get('salida_manana')
        entrada_tarde = request.form.get('entrada_tarde')
        salida_tarde = request.form.get('salida_tarde')

        fecha_hoy = datetime.now().date()

        #Validaciones basicas (opcional)
        if not any([entrada_manana, salida_comida, entrada_tarde, salida_tarde]):
            flash("No se ingresó ningún horario para actualizar", "warning")
            return redirect(url_for('ver_registros'))
        
        #Actualizar o insertar cada campo segun corresponda
        for tipo, hora in[
            ('entrada_manana', entrada_manana),
            ('salida_comida', salida_comida),
            ('entrada_tarde', entrada_tarde),
            ('salida_tarde', salida_tarde)
        ]:
            if hora:
                cursor.execute("""
                    INSERT INTO asistencia (personal_id, tipo, hora, fecha)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE hora=%s
                """, (id_personal, tipo, hora, fecha_hoy, hora))
        
        db.commit()
        flash("Registro actualizado correctamente", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error al actualizar registro: {str(e)}", "danger")

    return redirect(url_for("ver_registros"))



# -------------------------------
# Agregar horas extra
# -------------------------------
@app.route("/agregar_extra", methods=["POST"])
def agregar_extra():
    try:
        id_personal = request.form['id']
        horas_extra = request.form['horas_extra']

        if not horas_extra or int(horas_extra) <= 0:
            flash("Debe ingresar una cantidad válida de horas extra", "warning")
            return redirect(url_for('ver_registros'))

        # Insertar nueva hora extra
        cursor.execute("""
            INSERT INTO asistencia (personal_id, tipo, hora, fecha)
            VALUES (%s, 'hora_extra', %s, CURDATE())
        """, (id_personal, horas_extra))

        db.commit()
        flash("Horas extra agregadas correctamente", "success")

    except Exception as e:
        db.rollback()
        flash(f"Error al agregar horas extra: {str(e)}", "danger")

    return redirect(url_for('ver_registros'))




# -------------------------------
# Generar reporte día, quincenal y mensual
# -------------------------------
@app.route("/generar_reporte", methods=["GET"])
def generar_reporte():
    # --- Parámetros ---
    tipo_reporte = request.args.get('tipo_reporte', 'diario')
    mes = int(request.args.get('mes', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    quincena = int(request.args.get('quincena', 1))
    exportar_pdf = request.args.get('exportar_pdf')  # 🔸 nuevo parámetro

    calendario = defaultdict(list)
    reporte = []

    # --- Reporte diario ---
    if tipo_reporte == 'diario':
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
            fecha = fila['fecha']
            if fecha is None:
                continue

            fecha_str = fecha.strftime("%Y-%m-%d")
            dia_semana = fecha.weekday()  # 0=lunes, 6=domingo
            horas_extra = fila['horas_extra'] if fila['horas_extra'] is not None else 0

            # Lunes a viernes
            if dia_semana < 5:
                calendario[fecha_str].append({
                    'id': fila['id'],
                    'nombre_completo': f"{fila['nombre']} {fila['apellido_p']} {fila['apellido_m']}",
                    'entrada_manana': str(fila['entrada_manana']) if fila['entrada_manana'] else '-',
                    'salida_comida': str(fila['salida_comida']) if fila['salida_comida'] else '-',
                    'entrada_tarde': str(fila['entrada_tarde']) if fila['entrada_tarde'] else '-',
                    'salida_tarde': str(fila['salida_tarde']) if fila['salida_tarde'] else '-',
                    'horas_extra': horas_extra
                })
            # Sábado
            elif dia_semana == 5:
                entrada_manana = str(fila['entrada_manana']) if fila['entrada_manana'] else '-'
                salida_tarde = str(fila['salida_tarde']) if fila['salida_tarde'] else '-'

                if entrada_manana != '-' and entrada_manana < "09:00:00":
                    entrada_manana = "09:00:00"
                if salida_tarde != '-' and salida_tarde > "13:00:00":
                    salida_tarde = "13:00:00"

                calendario[fecha_str].append({
                    'id': fila['id'],
                    'nombre_completo': f"{fila['nombre']} {fila['apellido_p']} {fila['apellido_m']}",
                    'entrada_manana': entrada_manana,
                    'salida_comida': '-',
                    'entrada_tarde': '-',
                    'salida_tarde': salida_tarde,
                    'horas_extra': horas_extra
                })
            # Domingo se omite
            else:
                continue

    # --- Reporte quincenal o mensual ---
    else:
        if tipo_reporte == 'quincenal':
            if quincena == 1:
                inicio = f"{year}-{mes:02d}-01"
                fin = f"{year}-{mes:02d}-15"
            else:
                ultimo_dia = calendar.monthrange(year, mes)[1]
                inicio = f"{year}-{mes:02d}-16"
                fin = f"{year}-{mes:02d}-{ultimo_dia}"
        else:  # mensual
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
                'nombre': r['nombre'],
                'apellido_p': r['apellido_p'],
                'apellido_m': r['apellido_m'],
                'dias_asistidos': r['dias_asistidos'] or 0,
                'permisos': r['permisos'] or 0,
                'horas_extra': r['horas_extra'] or 0
            })

    # --- 🔸 NUEVA SECCIÓN: Generar y descargar PDF ---
    if exportar_pdf and tipo_reporte in ('quincenal', 'mensual'):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)


        # Agregar logos
        p.drawImage('static/img/escudomx.png', 50, 705, width=80, height=70)  # Logo izquierdo superior
        p.drawImage('static/img/Logousila2.png', 470, 705, width=80, height=70)  # Logo derecho superior
        
        # Título 
        titulo = ""
        if tipo_reporte == 'quincenal':
            if quincena == 1:
                titulo = f"Reporte Quincenal 1-15 de {mes}/{year}"
            else:
                titulo = f"Reporte Quincenal 16-fin de mes de {mes}/{year}"
        elif tipo_reporte == 'mensual':
            titulo = f"Reporte Mensual de {mes}/{year}"

        p.setFont("Helvetica-Bold", 14)
        p.drawString(200, 720, f"Reporte {tipo_reporte.capitalize()} - {mes}/{year}")
        p.setFont("Helvetica", 11)
        y = 680

         # Encabezado de tabla
        p.drawString(70, y, "Empleado")
        p.drawString(250, y, "Días asistidos")
        p.drawString(350, y, "Permisos")
        p.drawString(450, y, "Horas extra")
        y -= 20  # Espacio para los datos
        
        for r in reporte:
            nombre_completo = f"{r['nombre']} {r['apellido_p']} {r['apellido_m']}"
            p.drawString(70, y, nombre_completo)
            p.drawString(250, y, str(r['dias_asistidos']))
            p.drawString(350, y, str(r['permisos']))
            p.drawString(450, y, str(r['horas_extra']))
            y -= 18
            if y < 60:
                p.showPage()
                y = 750  # Reiniciar y para la nueva página

        p.save()
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"reporte_{tipo_reporte}_{mes}_{year}.pdf",
            mimetype='application/pdf'
        )

    # --- Renderizado normal ---
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
