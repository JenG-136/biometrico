from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "clave_secreta"

# Contraseña del administrador
ADMIN_PASSWORD = "admin123"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin", methods=["POST"])
def admin_access():
    password = request.form.get("password")
    accion = request.form.get("accion")  # Saber qué botón se presionó

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

# Ruta de agregar personal
@app.route("/agregar_personal")
def agregar_personal():
    return render_template("agregar_personal.html")

# Rutas ejemplo para otros botones
@app.route("/ver_registros")
def ver_registros():
    return "<h2>Página de Ver Registros (en construcción)</h2>"

@app.route("/ver_personal")
def ver_personal():
    return "<h2>Página de Ver Personal (en construcción)</h2>"

@app.route("/generar_reporte")
def generar_reporte():
    return "<h2>Página de Generar Reporte (en construcción)</h2>"

if __name__ == "__main__":
    app.run(debug=True)
