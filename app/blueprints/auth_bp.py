from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
from app.extensions import db
from app.models import Usuario

auth_bp = Blueprint('auth', __name__)

# Función auxiliar para validar la exigencia estricta de la contraseña
def es_contrasena_segura(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe incluir al menos una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return "La contraseña debe incluir al menos una letra minúscula."
    if not re.search(r"\d", password):
        return "La contraseña debe incluir al menos un número."
    if not re.search(r"[@$!%*?&#]", password):
        return "La contraseña debe incluir al menos un carácter especial (ej. @, $, !, %, *, ?, &, #)."
    return None

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombres = request.form.get('nombres')
        tipo_documento = request.form.get('tipo_documento')
        documento = request.form.get('documento')
        telefono = request.form.get('telefono')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validar contraseñas iguales
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('auth.registro'))

        # Validar fortaleza de la contraseña
        error_pass = es_contrasena_segura(password)
        if error_pass:
            flash(error_pass, 'danger')
            return redirect(url_for('auth.registro'))

        # Verificar si el correo o documento ya existen
        if Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return redirect(url_for('auth.registro'))
        
        if Usuario.query.filter_by(documento=documento).first():
            flash('El número de documento ya se encuentra registrado.', 'danger')
            return redirect(url_for('auth.registro'))

        # Crear usuario con rol por defecto 'usuario' y contraseña encriptada
        nuevo_usuario = Usuario(
            nombres=nombres,
            tipo_documento=tipo_documento,
            documento=documento,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento,
            email=email,
            password_hash=generate_password_hash(password),
            rol='usuario'
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            session['user_id'] = usuario.id
            session['user_nombre'] = usuario.nombres
            session['user_email'] = usuario.email
            session['user_rol'] = usuario.rol

            flash(f'Bienvenido de nuevo, {usuario.nombres}', 'success')
            
            # Redirección según el rol gestionado
            # En la ruta login de auth_bp.py:
            if usuario.rol == 'admin':
                return redirect(url_for('admin.panel'))
            elif usuario.rol == 'delegado':
                return redirect(url_for('delegado.panel'))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))