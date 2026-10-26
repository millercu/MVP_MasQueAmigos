from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import Usuario, Equipo, Jugador, Configuracion, Traspaso

delegado_bp = Blueprint('delegado', __name__)

@delegado_bp.route('/panel')
def panel():
    if session.get('user_rol') not in ['delegado', 'admin']:
        flash('Acceso denegado. Se requiere rol de delegado.', 'danger')
        return redirect(url_for('main.index'))

    user_id = session.get('user_id')
    equipo = Equipo.query.filter_by(usuario_id=user_id).first()
    
    # Obtener estado del mercado
    config = Configuracion.query.first()
    
    jugadores = []
    mercado = []
    ofertas_recibidas = []
    ofertas_enviadas = []

    if equipo:
        jugadores = Jugador.query.filter_by(equipo_id=equipo.id).all()
        
        # Jugadores que NO son de este equipo (o que no tienen equipo)
        mercado = Jugador.query.filter(
            (Jugador.rol_equipo == 'Deportista') & 
            ((Jugador.equipo_id != equipo.id) | (Jugador.equipo_id == None))
        ).all()        
        # Ofertas donde este equipo es el dueño actual del jugador
        ofertas_recibidas = Traspaso.query.filter_by(equipo_origen_id=equipo.id).all()
        
        # Ofertas que este equipo ha realizado a otros
        ofertas_enviadas = Traspaso.query.filter_by(equipo_destino_id=equipo.id).all()

    return render_template('delegado/paneldelegado.html', 
                           equipo=equipo, 
                           jugadores=jugadores,
                           mercado=mercado,
                           ofertas_recibidas=ofertas_recibidas,
                           ofertas_enviadas=ofertas_enviadas,
                           config=config)


@delegado_bp.route('/agregar-jugador', methods=['POST'])
def agregar_jugador():
    if session.get('user_rol') not in ['delegado', 'admin']:
        return redirect(url_for('main.index'))

    user_id = session.get('user_id')
    equipo = Equipo.query.filter_by(usuario_id=user_id).first()

    if not equipo:
        flash('No tienes un equipo asignado actualmente.', 'danger')
        return redirect(url_for('delegado.panel'))

    # Capturar todos los datos del formulario respetando tu modelo
    nombre = request.form.get('nombre')
    documento = request.form.get('documento')
    eps = request.form.get('eps')
    rol_equipo = request.form.get('rol_equipo')
    posicion = request.form.get('posicion')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    clausula_str = request.form.get('clausula_rescision', '0')
    clausula_limpia = clausula_str.replace('.', '').replace(' ', '') # Quita puntos y espacios
    
    try:
        clausula = float(clausula_limpia)
    except ValueError:
        clausula = 0.0

    # Validación: Verificar que el documento no esté registrado ya
    if Jugador.query.filter_by(documento=documento).first():
        flash('Ya existe un jugador registrado con ese número de documento.', 'danger')
        return redirect(url_for('delegado.panel'))

    # Crear el nuevo registro del jugador
    nuevo_jugador = Jugador(
        nombre=nombre,
        documento=documento,
        eps=eps,
        rol_equipo=rol_equipo,
        posicion=posicion,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        clausula_rescision=clausula,
        equipo_id=equipo.id,
        estado_fichaje='Activo'
    )

    db.session.add(nuevo_jugador)
    db.session.commit()

    flash(f'El integrante {nombre} fue inscrito exitosamente en {equipo.nombre}.', 'success')
    return redirect(url_for('delegado.panel'))



@delegado_bp.route('/ofertar/<int:jugador_id>', methods=['POST'])
def ofertar(jugador_id):
    if session.get('user_rol') not in ['delegado', 'admin']:
        return redirect(url_for('main.index'))

    config = Configuracion.query.first()
    if not config or not config.mercado_abierto:
        flash('El mercado de fichajes se encuentra cerrado.', 'danger')
        return redirect(url_for('delegado.panel'))

    equipo_destino = Equipo.query.filter_by(usuario_id=session.get('user_id')).first()
    jugador_objetivo = Jugador.query.get_or_404(jugador_id)

    # Validación de seguridad: Asegurar que solo se puede ofertar por deportistas
    if jugador_objetivo.rol_equipo != 'Deportista':
        flash('No se pueden realizar ofertas por miembros del cuerpo técnico.', 'danger')
        return redirect(url_for('delegado.panel'))

    if not equipo_destino:
        flash('No tienes un equipo asignado actualmente.', 'danger')
        return redirect(url_for('delegado.panel'))

    # Capturar datos del formulario
    tipo = request.form.get('tipo')
    nuevo_fecha_fin = request.form.get('nuevo_fecha_fin')
    jugador_intercambio_id = request.form.get('jugador_intercambio_id')
    mensaje = request.form.get('mensaje')
    
    # Limpieza del monto ingresado (quitando puntos)
    monto_str = request.form.get('monto', '0')
    monto_limpio = monto_str.replace('.', '').replace(' ', '')
    try:
        monto_ofrecido = float(monto_limpio)
    except ValueError:
        monto_ofrecido = 0.0

    # NUEVA LÓGICA DE NEGOCIO: Sumar cláusula solo si es Compra
    valor_clausula = jugador_objetivo.clausula_rescision or 0.0
    
    if tipo == 'Compra':
        monto_final = monto_ofrecido + valor_clausula
    else:
        monto_final = monto_ofrecido # En préstamos no se cobra la cláusula

    # Validar jugador de intercambio
    if jugador_intercambio_id:
        j_intercambio = Jugador.query.get(jugador_intercambio_id)
        if not j_intercambio or j_intercambio.rol_equipo != 'Deportista':
            flash('El jugador seleccionado para intercambio no es válido.', 'danger')
            return redirect(url_for('delegado.panel'))
    else:
        jugador_intercambio_id = None

    # Crear el traspaso con el MONTO FINAL calculado
    nuevo_traspaso = Traspaso(
        jugador_id=jugador_objetivo.id,
        equipo_origen_id=jugador_objetivo.equipo_id,
        equipo_destino_id=equipo_destino.id,
        tipo=tipo,
        monto=monto_final,
        nuevo_fecha_fin=nuevo_fecha_fin,
        jugador_intercambio_id=jugador_intercambio_id,
        mensaje_negociacion=mensaje,
        estado='Pendiente'
    )

    db.session.add(nuevo_traspaso)
    db.session.commit()

    flash(f'Oferta enviada exitosamente por {jugador_objetivo.nombre}.', 'success')
    return redirect(url_for('delegado.panel'))

# (Mantenemos tu función agregar_jugador que ya tenías abajo)

@delegado_bp.route('/editar-jugador/<int:jugador_id>', methods=['GET', 'POST'])
def editar_jugador(jugador_id):
    if session.get('user_rol') not in ['delegado', 'admin']:
        return redirect(url_for('main.index'))

    # Si entra por GET (por ejemplo, recargando la página o un link viejo), lo devolvemos al panel
    if request.method == 'GET':
        return redirect(url_for('delegado.panel'))

    # Lógica exclusiva para POST (cuando se envía el formulario del Modal)
    jugador = Jugador.query.get_or_404(jugador_id)
    
    # Validar que el jugador pertenece al equipo de este delegado
    equipo = Equipo.query.filter_by(usuario_id=session.get('user_id')).first()
    if not equipo or jugador.equipo_id != equipo.id:
        flash('No tienes permiso para editar este jugador.', 'danger')
        return redirect(url_for('delegado.panel'))

    # Actualizar datos
    jugador.nombre = request.form.get('nombre')
    jugador.documento = request.form.get('documento')
    jugador.eps = request.form.get('eps')
    jugador.rol_equipo = request.form.get('rol_equipo')
    jugador.posicion = request.form.get('posicion')
    jugador.fecha_inicio = request.form.get('fecha_inicio')
    jugador.fecha_fin = request.form.get('fecha_fin')
    
    # Reemplaza la lógica antigua de clausula por esto:
    clausula_str = request.form.get('clausula_rescision', '0')
    clausula_limpia = clausula_str.replace('.', '').replace(' ', '')
    
    try:
        jugador.clausula_rescision = float(clausula_limpia)
    except ValueError:
        jugador.clausula_rescision = 0.0

    db.session.commit()
    flash('Datos del jugador actualizados correctamente.', 'success')
    
    return redirect(url_for('delegado.panel'))

@delegado_bp.route('/eliminar-jugador/<int:jugador_id>', methods=['POST'])
def eliminar_jugador(jugador_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    jugador = Jugador.query.get_or_404(jugador_id)
    db.session.delete(jugador)
    db.session.commit()
    return redirect(url_for('delegado.panel'))


@delegado_bp.route('/responder-oferta/<int:oferta_id>', methods=['POST'])
def responder_oferta(oferta_id):
    if session.get('user_rol') not in ['delegado', 'admin']: return redirect(url_for('main.index'))
    
    oferta = Traspaso.query.get_or_404(oferta_id)
    equipo_local = Equipo.query.filter_by(usuario_id=session.get('user_id')).first()
    accion = request.form.get('accion')

    # Si el que responde es el DUEÑO del jugador (Equipo Origen)
    if equipo_local and oferta.equipo_origen_id == equipo_local.id:
        if accion == 'aceptar':
            oferta.estado = 'Pendiente_Admin'
            flash('Has aceptado la oferta. Esperando validación del Administrador.', 'success')
        elif accion == 'rechazar':
            oferta.estado = 'Rechazado'
            flash('Has rechazado la oferta.', 'info')
        elif accion == 'renegociar':
            nuevo_monto_str = request.form.get('nuevo_monto', '0')
            nuevo_monto_limpio = nuevo_monto_str.replace('.', '').replace(' ', '')
            oferta.monto = float(nuevo_monto_limpio)
            oferta.mensaje_negociacion = request.form.get('nuevo_mensaje', '')
            oferta.estado = 'Contraoferta'
            flash('Contraoferta enviada al equipo comprador.', 'success')

    # Si el que responde es el COMPRADOR (Equipo Destino) evaluando la contraoferta
    elif equipo_local and oferta.equipo_destino_id == equipo_local.id:
        if accion == 'aceptar_contraoferta':
            oferta.estado = 'Pendiente_Admin'
            flash('Aceptaste la contraoferta. Esperando validación del Administrador.', 'success')
        elif accion == 'rechazar':
            oferta.estado = 'Rechazado'
            flash('Rechazaste la contraoferta.', 'info')

    db.session.commit()
    return redirect(url_for('delegado.panel'))