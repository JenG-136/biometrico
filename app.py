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
from flask import Response
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#------------------------------------------------------------------------




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
        user="root",
        password="",
        database="biometrico_db"
    )
    cursor = db.cursor(dictionary=True)  # cursor devuelve diccionarios
    print("Conexión exitosa")
except mysql.connector.Error as err:
    print("Error de conexión:", err)

# -------------------------------
# Rutas principales
# -------------------------------

# Página inicial (lector de huella)
@app.route("/")
def inicio():
    return render_template("inicio.html")

# Página secundaria solo parav administrador 
@app.route("/admin_index")
def admin_index():
    return render_template("admin_index.html")

# Ruta para acceso de admin
@app.route("/admin_access_post", methods=["POST"])
def admin_access_post():
    password = request.form["password"]
    if password == ADMIN_PASSWORD:
        return redirect(url_for("admin_index"))  # <-- aquí
    else:
        flash("Contraseña incorrecta", "error")
        return redirect(url_for("inicio"))



#---------------------------------------------------------------------------
# Registro de asistencia con rangos de tolerancia personalizados
#---------------------------------------------------------------------------

@app.route("/buscar_empleado", methods=["POST"])
def buscar_empleado():
    id_huella = request.json.get("id_huella", 3)
    cursor.execute("SELECT * FROM personal WHERE id = %s", (id_huella,))
    empleado = cursor.fetchone()

    if not empleado:
        return jsonify({"error": "Empleado no encontrado"}), 404

    hora_actual = datetime.now().strftime("%H:%M:%S")
    hora_dt = datetime.strptime(hora_actual, "%H:%M:%S")
    fecha_hoy = date.today()

    # Verificar si ya hay registro para hoy
    cursor.execute("SELECT * FROM asistencia WHERE personal_id=%s AND fecha=%s", (id_huella, fecha_hoy))
    registro = cursor.fetchone()

    # RANGOS DE TIEMPO
    entrada_inicio = datetime.strptime("08:55:00", "%H:%M:%S")
    entrada_fin = datetime.strptime("10:30:00", "%H:%M:%S")
    salida_comida_inicio = datetime.strptime("14:00:00", "%H:%M:%S")
    salida_comida_fin = datetime.strptime("14:30:00", "%H:%M:%S")
    entrada_tarde_inicio = datetime.strptime("15:55:00", "%H:%M:%S")
    entrada_tarde_fin = datetime.strptime("17:00:00", "%H:%M:%S")
    salida_inicio = datetime.strptime("19:00:00", "%H:%M:%S")
    hora_extra_inicio = datetime.strptime("20:00:00", "%H:%M:%S")

    if not registro:
        # Si no hay registro hoy y la hora está en el rango de entrada de la mañana
        if entrada_inicio <= hora_dt <= entrada_fin:
            cursor.execute("""
                INSERT INTO asistencia (personal_id, fecha, hora_entrada)
                VALUES (%s, %s, %s)
            """, (id_huella, fecha_hoy, hora_actual))
            tipo = "entrada_mañana"
        else:
            return jsonify({"error": "Fuera de rango de entrada"}), 400
        db.commit()

    else:
        # Ya existe registro → verificar siguiente campo
        if not registro["salida_comida"] and salida_comida_inicio <= hora_dt <= salida_comida_fin:
            cursor.execute("UPDATE asistencia SET salida_comida=%s WHERE id=%s", (hora_actual, registro["id"]))
            tipo = "salida_comida"

        elif not registro["entrada_tarde"] and entrada_tarde_inicio <= hora_dt <= entrada_tarde_fin:
            cursor.execute("UPDATE asistencia SET entrada_tarde=%s WHERE id=%s", (hora_actual, registro["id"]))
            tipo = "entrada_tarde"

        elif not registro["hora_salida"] and hora_dt >= salida_inicio:
            cursor.execute("UPDATE asistencia SET hora_salida=%s WHERE id=%s", (hora_actual, registro["id"]))
            tipo = "salida_tarde"

            # Calcular horas extra si sale después de las 20:00
            if hora_dt > hora_extra_inicio:
                diferencia = (hora_dt - hora_extra_inicio).seconds / 3600
                horas_extra = round(diferencia, 2)
                cursor.execute("""
                    UPDATE asistencia 
                    SET hora_extra = SEC_TO_TIME(ROUND(%s * 3600))
                    WHERE id=%s
                """, (horas_extra, registro["id"]))
                tipo = "salida_tarde_con_extra"

        else:
            tipo = "fuera_de_rango"  # Si intenta registrar fuera del rango válido

        db.commit()

    # Cálculo del retraso respecto a las 09:00
    retraso_min = max(
        0,
        int((hora_dt - datetime.strptime("09:00:00", "%H:%M:%S")).total_seconds() / 60)
    )

    return jsonify({
        "nombre": empleado["nombre"],
        "puesto": empleado["puesto"],
        "foto": empleado["foto"],
        "hora": hora_actual,
        "tipo": tipo,
        "retraso": f"{retraso_min} min" if retraso_min > 0 else "A tiempo"
    })


#acceso de administrador
@app.route('/admin_access', methods=['POST'])
def admin_access():
    password = request.form.get('password')
    accion = request.form.get('accion')  

    if password == ADMIN_PASSWORD:
        if accion == "ver_registros":
            return redirect(url_for('ver_registros'))
        elif accion == "agregar_personal":
            return redirect(url_for('agregar_personal'))
        elif accion == "generar_reporte":
            return redirect(url_for('generar_reporte'))
        elif accion == "ver_personal":
            return redirect(url_for('ver_personal'))
        else:
            flash("Acción no reconocida.", "danger")
            return redirect(url_for('admin_index'))  
    else:
        flash("Contraseña incorrecta.", "danger")
        return redirect(url_for('inicio'))





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
    ORDER BY puesto ASC, nombre ASC, apellido_p ASC, apellido_m ASC
""")
    registros = cursor.fetchall()

    # Agrupacion por puesto 
    personal_por_puesto = {}
    for p in registros:
        puesto = p['puesto']
        if puesto not in personal_por_puesto:
            personal_por_puesto[puesto] = []
        personal_por_puesto[puesto].append(p)

    return render_template("ver_personal.html", personal_por_puesto=personal_por_puesto)



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
# Editar información de un empleado (solo guardar)
# -------------------------------
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_personal(id):
    cursor = db.cursor(dictionary=True)

    if request.method == "GET":
        cursor.execute("SELECT * FROM personal WHERE id = %s", (id,))
        empleado = cursor.fetchone()
        if not empleado:
            return redirect(url_for('ver_personal'))
        return render_template("editar_personal.html", empleado=empleado)

    if request.method == "POST":
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre', '').strip()
            apellido_p = request.form.get('apellido_p', '').strip()
            apellido_m = request.form.get('apellido_m', '').strip()
            fecha_nac = request.form.get('fecha_nac', None)
            curp = request.form.get('curp', '').strip()
            edad = int(request.form.get('edad', 0) or 0)
            calle = request.form.get('calle', '').strip()
            colonia = request.form.get('colonia', '').strip()
            puesto = request.form.get('puesto', '').strip()
            telefono = request.form.get('telefono', '').strip()
            genero = request.form.get('genero', '').strip()
            estatus = request.form.get('estatus', '').strip()
            turno = request.form.get('turno', '').strip()
            fecha_ingreso = request.form.get('fecha_ingreso', None)

            # Manejo de foto
            foto = request.files.get('foto')
            if foto and foto.filename != '':
                filename = secure_filename(foto.filename)
                ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(ruta_completa)
                nombre_foto = filename
            else:
                cursor.execute("SELECT foto FROM personal WHERE id = %s", (id,))
                res = cursor.fetchone()
                nombre_foto = res['foto'] if res and res['foto'] else ''

            # Actualizacion en la bd 
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

        except Exception as e:
            db.rollback()
            print(f"Error al actualizar empleado {id}: {e}")

        # Rgresa en la vista de ver:personal
        return redirect(url_for("ver_personal"))


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
    try:
        # Obtener lista de empleados junto con su asistencia de hoy
        cursor.execute("""
            SELECT 
                p.id,
                p.nombre,
                p.apellido_p,
                p.apellido_m,
                p.puesto,
                a.hora_entrada,
                a.salida_comida,
                a.entrada_tarde,
                a.hora_salida,
                a.hora_extra
            FROM personal p
            LEFT JOIN asistencia a 
                ON p.id = a.personal_id AND a.fecha = CURDATE()
            ORDER BY p.nombre, p.apellido_p
        """)
        registros = cursor.fetchall()

        lista_registros = []
        hoy = datetime.today()
        dia_semana = hoy.weekday()  # 0=lunes, ..., 5=sábado, 6=domingo

        for r in registros:
            puesto = (r['puesto'] or "").lower()

            # Reglas según el día y el tipo de puesto
            if dia_semana == 6 and puesto != "policía":
                entrada_manana = salida_comida = entrada_tarde = salida_tarde = "No laboral"
            elif dia_semana == 5 and puesto != "policía":
                entrada_manana = r['hora_entrada'] or "-"
                salida_comida = r['salida_comida'] or "13:00"
                entrada_tarde = "-"
                salida_tarde = "-"
            else:
                entrada_manana = r['hora_entrada'] or "-"
                salida_comida = r['salida_comida'] or "-"
                entrada_tarde = r['entrada_tarde'] or "-"
                salida_tarde = r['hora_salida'] or "-"

            lista_registros.append({
                'id': r['id'],
                'nombre': r['nombre'],
                'apellido_p': r['apellido_p'],
                'apellido_m': r['apellido_m'],
                'entrada_manana': entrada_manana,
                'salida_comida': salida_comida,
                'entrada_tarde': entrada_tarde,
                'salida_tarde': salida_tarde,
                'horas_extra': r['hora_extra'] or "0:00"
            })
        
        # Obtener lista completa de empleados para el modal
        cursor.execute("SELECT id, nombre, apellido_p, apellido_m, puesto FROM personal ORDER BY nombre, apellido_p")
        personal = cursor.fetchall()

        fecha_actual = date.today().strftime("%d/%m/%Y")
        return render_template(
            "ver_registros.html",
            registros=lista_registros,
            personal=personal,  #la lista de empleados
            fecha_actual=fecha_actual
        )

    except Exception as e:
        print(f"Error en ver_registros: {e}")
        return f"Error al obtener los registros: {e}"


# -------------------------------
# Editar registro de asistencia
# -------------------------------
@app.route('/editar_registro', methods=["POST"])
def editar_registro():
    try:
        id_personal = request.form['id']
        fecha_hoy = datetime.now().date()

        # Obtener los valores del formulario
        hora_entrada = request.form.get('entrada_manana', '').strip() or None
        salida_comida = request.form.get('salida_comida', '').strip() or None
        entrada_tarde = request.form.get('entrada_tarde', '').strip() or None
        hora_salida = request.form.get('salida_tarde', '').strip() or None

        # Normalizar formato HH:MM:SS
        def normalizar(h):
            if not h:
                return None
            h = h.strip()
            if len(h) == 5 and ':' in h:  # HH:MM
                return f"{h}:00"
            return h

        hora_entrada = normalizar(hora_entrada)
        salida_comida = normalizar(salida_comida)
        entrada_tarde = normalizar(entrada_tarde)
        hora_salida = normalizar(hora_salida)

        # Insertar o actualizar registro del día
        cursor.execute("""
            INSERT INTO asistencia (personal_id, fecha, hora_entrada, salida_comida, entrada_tarde, hora_salida)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                hora_entrada = VALUES(hora_entrada),
                salida_comida = VALUES(salida_comida),
                entrada_tarde = VALUES(entrada_tarde),
                hora_salida = VALUES(hora_salida)
        """, (id_personal, fecha_hoy, hora_entrada, salida_comida, entrada_tarde, hora_salida))

        db.commit()
        return jsonify({"status": "success", "message": "Horas normales actualizadas correctamente."})

    except Exception as e:
        db.rollback()
        print(f"Error en editar_registro: {e}")
        return jsonify({"status": "error", "message": f"Error al guardar: {str(e)}"})
    
# ----------------------------------------
# Registrar permiso justificado
# ----------------------------------------
@app.route("/registrar_permiso", methods=["POST"])
def registrar_permiso():
    try:
        personal_id = request.form.get("empleado_id")
        fecha = request.form.get("fecha")
        motivo = request.form.get("motivo")

        if not personal_id or not fecha or not motivo:
            flash("Faltan datos requeridos", "error")
            return redirect(url_for("ver_registros"))

        cursor.execute("""
            INSERT INTO permisos (personal_id, fecha, motivo)
            VALUES (%s, %s, %s)
        """, (personal_id, fecha, motivo))

        db.commit()
        flash("Permiso registrado correctamente", "success")
        return redirect(url_for("ver_registros"))

    except mysql.connector.Error as err:
        print(f"Error al registrar el permiso: {err}")
        flash("Ocurrió un error al guardar el permiso", "error")
        return redirect(url_for("ver_registros"))

    

# -------------------------------
# Agregar horas extra
# -------------------------------
@app.route("/agregar_extra", methods=["POST"])
def agregar_extra():
    try:
        id_personal = request.form.get('id')
        horas_extra = request.form.get('horas_extra')

        if not id_personal:
            flash("ID del personal no proporcionado", "warning")
            return redirect(url_for('ver_registros'))

        if not horas_extra or not horas_extra.isdigit():
            flash("Debe ingresar una cantidad válida de horas extra (1 a 4)", "warning")
            return redirect(url_for('ver_registros'))

        horas_extra_int = int(horas_extra)
        if horas_extra_int <= 0 or horas_extra_int > 4:
            flash("Solo se permiten de 1 a 4 horas extra", "warning")
            return redirect(url_for('ver_registros'))

        # Formato HH:MM:SS
        hora_formateada = f"{horas_extra_int}:00:00"

        # Insertar o actualizar horas extra
        cursor.execute("""
            INSERT INTO asistencia (personal_id, fecha, hora_extra)
            VALUES (%s, CURDATE(), %s)
            ON DUPLICATE KEY UPDATE hora_extra = VALUES(hora_extra)
        """, (id_personal, hora_formateada))

        db.commit()
        flash("Horas extra registradas correctamente", "success")

    except Exception as e:
        db.rollback()
        flash(f"Error al agregar horas extra: {str(e)}", "danger")

    return redirect(url_for('ver_registros'))


# -------------------------------
# Generar reporte (Diario, Quincenal, Mensual)
# -------------------------------
@app.route("/generar_reporte", methods=["GET"])
def generar_reporte():
    tipo_reporte = request.args.get('tipo_reporte', 'diario')

    try:
        mes = int(request.args.get('mes', datetime.now().month))
    except ValueError:
        mes = datetime.now().month

    try:
        year = int(request.args.get('year', datetime.now().year))
    except ValueError:
        year = datetime.now().year

    try:
        quincena = int(request.args.get('quincena', 1))
    except ValueError:
        quincena = 1

    exportar_pdf = request.args.get('exportar_pdf')

    calendario = defaultdict(list)
    reporte = []

    # --------------------------------------------------------------------------
    # --- Reporte diario ---
    # --------------------------------------------------------------------------
    if tipo_reporte == 'diario':
        # Traer todos los empleados activos
        cursor.execute("SELECT id, nombre, apellido_p, apellido_m FROM personal ORDER BY id")
        empleados = cursor.fetchall()

        # Obtener todas las asistencias
        cursor.execute("""
            SELECT a.fecha, p.id, p.nombre, p.apellido_p, p.apellido_m,
                   a.hora_entrada, a.salida_comida, a.entrada_tarde, a.hora_salida, a.hora_extra
            FROM asistencia a
            INNER JOIN personal p ON a.personal_id = p.id
            WHERE MONTH(a.fecha) = %s AND YEAR(a.fecha) = %s
        """, (mes, year))
        registros_asistencia = cursor.fetchall()

        # Convertir a diccionario 
        asistencias_por_fecha = defaultdict(dict)
        for fila in registros_asistencia:
            fecha_str = fila['fecha'].strftime("%Y-%m-%d")
            asistencias_por_fecha[fecha_str][fila['id']] = fila

        # Generar calendario completo
        num_dias = calendar.monthrange(year, mes)[1]
        for dia in range(1, num_dias + 1):
            fecha = date(year, mes, dia)
            fecha_str = fecha.strftime("%Y-%m-%d")
            dia_semana = fecha.weekday()  # 0=lunes, 6=domingo

            # Omitir domingos
            if dia_semana == 6:
                continue

            # Para cada empleado, agregar su registro o vacío
            for emp in empleados:
                registro = asistencias_por_fecha.get(fecha_str, {}).get(emp['id'])

                if registro:  # Tiene asistencia
                    entrada_manana = str(registro['hora_entrada']) if registro['hora_entrada'] else '-'
                    salida_comida = str(registro['salida_comida']) if registro['salida_comida'] else '-'
                    entrada_tarde = str(registro['entrada_tarde']) if registro['entrada_tarde'] else '-'
                    salida_tarde = str(registro['hora_salida']) if registro['hora_salida'] else '-'
                    horas_extra = registro['hora_extra'] if registro['hora_extra'] else 0
                else:  # No registró asistencia ese día
                    entrada_manana = '-'
                    salida_comida = '-'
                    entrada_tarde = '-'
                    salida_tarde = '-'
                    horas_extra = 0

                calendario[fecha_str].append({
                    'id': emp['id'],
                    'nombre_completo': f"{emp['nombre']} {emp['apellido_p']} {emp['apellido_m']}",
                    'entrada_manana': entrada_manana,
                    'salida_comida': salida_comida,
                    'entrada_tarde': entrada_tarde,
                    'salida_tarde': salida_tarde,
                    'horas_extra': horas_extra
                })

    # --------------------------------------------------------------------------
    # --- Reporte quincenal o mensual ---
    # --------------------------------------------------------------------------
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

        # ✅ Incluye el ID y el puesto del empleado
        cursor.execute("""
            SELECT p.id, p.nombre, p.apellido_p, p.apellido_m, p.puesto,
                   COUNT(DISTINCT CASE WHEN a.hora_entrada IS NOT NULL OR a.entrada_tarde IS NOT NULL THEN a.fecha END) AS dias_asistidos,
                   SUM(CASE WHEN a.hora_extra IS NOT NULL THEN TIME_TO_SEC(a.hora_extra)/3600 ELSE 0 END) AS horas_extra,
                   COUNT(DISTINCT perm.id) AS permisos
            FROM personal p
            LEFT JOIN asistencia a 
                ON a.personal_id = p.id AND a.fecha BETWEEN %s AND %s
            LEFT JOIN permisos perm
                ON perm.personal_id = p.id AND perm.fecha BETWEEN %s AND %s
            GROUP BY p.id
            ORDER BY p.id
        """, (inicio, fin, inicio, fin))
        registros = cursor.fetchall()

        for r in registros:
            reporte.append({
                'id': r['id'],
                'nombre': r['nombre'],
                'apellido_p': r['apellido_p'],
                'apellido_m': r['apellido_m'],
                'puesto': r['puesto'] or 'No especificado',
                'dias_asistidos': r['dias_asistidos'] or 0,
                'horas_extra': round(r['horas_extra'], 2) if r['horas_extra'] else 0,
                'permisos': r['permisos'] or 0
            })

    # --------------------------------------------------------------------------
    # --- Generar PDF ---
    # --------------------------------------------------------------------------
    if exportar_pdf and tipo_reporte in ('quincenal', 'mensual'):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=80, bottomMargin=50)
        styles = getSampleStyleSheet()
        story = []

        # Logos y encabezado centrado
        logo_izq = 'static/img/escudomx.png'
        logo_der = 'static/img/Logousila2.png'

        encabezado = [
            [Image(logo_izq, width=1*inch, height=1*inch),
             Paragraph("<b>H. AYUNTAMIENTO CONSTITUCIONAL<br/>SAN FELIPE USILA, OAXACA 2025 – 2027</b>",
                       ParagraphStyle('encabezado', alignment=1, fontSize=10)),
             Image(logo_der, width=1*inch, height=1*inch)]
        ]
        tabla_encabezado = Table(encabezado, colWidths=[1.5*inch, 4*inch, 1.5*inch])
        tabla_encabezado.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(tabla_encabezado)
        story.append(Spacer(1, 5))

        # Fecha de emisión
        fecha_emision = datetime.now().strftime("%d/%m/%Y")
        story.append(Paragraph(f"<b>Fecha de emisión:</b> {fecha_emision}",
                               ParagraphStyle('fecha', alignment=2, fontSize=9)))
        story.append(Spacer(1, 10))

        # Título
        mes_nombre = calendar.month_name[mes].capitalize()
        if tipo_reporte == 'quincenal':
            titulo_texto = f"Reporte Quincenal del {'1 al 15' if quincena == 1 else '16 al fin'} de {mes_nombre} de {year}"
            total_dias_periodo = 15 if quincena == 1 else calendar.monthrange(year, mes)[1] - 15
        else:
            titulo_texto = f"Reporte Mensual de {mes_nombre} de {year}"
            total_dias_periodo = calendar.monthrange(year, mes)[1]

        story.append(Paragraph(f"<b>{titulo_texto}</b>", ParagraphStyle('titulo', fontSize=14, alignment=1, spaceAfter=12)))

        # Tabla de datos
        encabezados = ["ID", "Empleado", "Puesto / Departamento", "Días Presentes", "Días Ausentes", "Días con Permiso", "% Asistencia"]
        datos_tabla = [encabezados]

        for r in reporte:
            nombre_completo = f"{r['nombre']} {r['apellido_p']} {r['apellido_m']}"
            dias_presentes = r.get('dias_asistidos', 0)
            dias_permiso = r.get('permisos', 0)
            dias_ausentes = total_dias_periodo - dias_presentes - dias_permiso
            porcentaje = round(((dias_presentes + dias_permiso) / total_dias_periodo) * 100, 2) if total_dias_periodo > 0 else 0

            fila = [
                r.get('id', 'N/A'),
                nombre_completo,
                r.get('puesto', 'N/A'),
                dias_presentes,
                dias_ausentes,
                dias_permiso,
                f"{porcentaje} %"
            ]
            datos_tabla.append(fila)

        tabla = Table(datos_tabla, colWidths=[0.6*inch, 1.8*inch, 1.8*inch, 1*inch, 1*inch, 1.2*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(tabla)
        story.append(Spacer(1, 20))

        # Pie
        story.append(Spacer(1, 400))
        story.append(Paragraph(
            "<i>Documento confidencial. Contiene información sensible del personal del H. Ayuntamiento de San Felipe Usila.</i>",
            ParagraphStyle('confidencial', alignment=1, fontSize=8)
        ))

        def pie_pagina(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.drawString(40, 30, f"Página {doc.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"reporte_{tipo_reporte}_{mes}_{year}.pdf",
            mimetype='application/pdf'
        )

    # --------------------------------------------------------------------------
    # --- Render normal de la página ---
    # --------------------------------------------------------------------------
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


# -------------------------------------------------------------
# Ruta separada: actualizar asistencia desde el calendario diario
# -------------------------------------------------------------
@app.route('/actualizar_asistencia', methods=['POST'])
def actualizar_asistencia():
    id = request.form.get('id')
    fecha = request.form.get('fecha')
    entrada_manana = request.form.get('entrada_manana') or None
    salida_comida = request.form.get('salida_comida') or None
    entrada_tarde = request.form.get('entrada_tarde') or None
    salida_tarde = request.form.get('salida_tarde') or None
    horas_extra = request.form.get('horas_extra') or 0

    try:
        # Verificar si ya existe registro
        cursor.execute("SELECT id FROM asistencia WHERE personal_id = %s AND fecha = %s", (id, fecha))
        existe = cursor.fetchone()

        if existe:
            # Actualizar asistencia existente
            cursor.execute("""
                UPDATE asistencia
                SET hora_entrada = %s,
                    salida_comida = %s,
                    entrada_tarde = %s,
                    hora_salida = %s,
                    hora_extra = %s
                WHERE personal_id = %s AND fecha = %s
            """, (entrada_manana, salida_comida, entrada_tarde, salida_tarde, horas_extra, id, fecha))
        else:
            # Crear nuevo registro si no existe
            cursor.execute("""
                INSERT INTO asistencia (personal_id, fecha, hora_entrada, salida_comida, entrada_tarde, hora_salida, hora_extra)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id, fecha, entrada_manana, salida_comida, entrada_tarde, salida_tarde, horas_extra))

        db.commit()
        return jsonify({'status': 'success', 'message': 'Asistencia guardada correctamente.'})

    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


# -------------------------------
# Iniciar servidor
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
