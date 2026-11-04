from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
from flask_mail import Message
from app.extensions import db, mail, oauth
from email.header import Header
from app.models import Usuario
from datetime import datetime, timedelta

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


@auth_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('auth.authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/authorize')
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        email = user_info['email']
        nombres = user_info['name']
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        # Si el usuario de Google no existe en nuestra base de datos, lo registramos automáticamente
        if not usuario:
            nuevo_usuario = Usuario(
                nombres=nombres,
                tipo_documento='PG', # Pasaporte Google / Placeholder
                documento=f"G-{secrets.token_hex(4).upper()}", # Documento aleatorio temporal
                telefono='0000000000',
                fecha_nacimiento='2000-01-01',
                email=email,
                password_hash=generate_password_hash(secrets.token_urlsafe(16)), # Contraseña inaccesible
                rol='usuario'
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            usuario = nuevo_usuario
        
        # Iniciar sesión
        session['user_id'] = usuario.id
        session['user_nombre'] = usuario.nombres
        session['user_email'] = usuario.email
        session['user_rol'] = usuario.rol

        flash(f'Sesión iniciada correctamente con Google, {usuario.nombres}', 'success')
        
        if usuario.rol == 'admin':
            return redirect(url_for('admin.panel'))
        elif usuario.rol == 'delegado':
            return redirect(url_for('delegado.panel'))
        else:
            return redirect(url_for('main.index'))
            
    flash('Error al intentar iniciar sesión con Google.', 'danger')
    return redirect(url_for('auth.login'))

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


import secrets
from datetime import datetime, timedelta
from flask_mail import Message
from app.extensions import mail, db

@auth_bp.route('/solicitar-recuperacion', methods=['GET', 'POST'])
def solicitar_recuperacion():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            # Generar token único de 32 caracteres y expiración de 1 hora
            token = secrets.token_urlsafe(32)
            usuario.reset_token = token
            usuario.token_expiracion = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Crear y enviar el correo con codificación segura ASCII en el asunto y UTF-8 en el cuerpo
            enlace = url_for('auth.reset_password', token=token, _external=True)
            
            msg = Message(
                subject='Recuperacion de Contrasena - Copa Mas Que Amigos', # Sin tildes ni eñes en el asunto para evitar bloqueos SMTP
                sender='tu_correo@gmail.com', # Mismo correo de tu configuración
                recipients=[email]
            )
            
            # Cuerpo codificado explícitamente en bytes UTF-8
            cuerpo_texto = f"Hola {usuario.nombres},\n\nPara restablecer tu contraseña haz clic en el siguiente enlace:\n{enlace}\n\nEste enlace expirará en 1 hora."
            msg.body = cuerpo_texto
            
            # Forzamos el envío limpio
            mail.send(msg)
            
        # Mensaje genérico por seguridad
        flash('Si el correo existe en nuestro sistema, hemos enviado las instrucciones.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/solicitar.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    usuario = Usuario.query.filter_by(reset_token=token).first()
    
    # Validar que el token exista y no esté vencido
    if not usuario or usuario.token_expiracion < datetime.utcnow():
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.solicitar_recuperacion'))
        
    if request.method == 'POST':
        nuevo_pass = request.form.get('password')
        
        # Reutilizamos tu validador de contraseña segura
        error_pass = es_contrasena_segura(nuevo_pass)
        if error_pass:
            flash(error_pass, 'danger')
            return redirect(url_for('auth.reset_password', token=token))
            
        usuario.password_hash = generate_password_hash(nuevo_pass)
        usuario.reset_token = None
        usuario.token_expiracion = None
        db.session.commit()
        
        flash('Tu contraseña ha sido actualizada correctamente. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset.html', token=token)



@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))