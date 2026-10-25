from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import Usuario, Equipo, Configuracion, Traspaso, Jugador, Categoria

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/panel')
def panel():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    usuarios = Usuario.query.all()
    equipos = Equipo.query.all()
    jugadores = Jugador.query.all()
    categorias = Categoria.query.all() # <-- ASEGÚRATE DE PASAR ESTO
    config = Configuracion.query.first()
    traspasos_pendientes = Traspaso.query.filter_by(estado='Pendiente_Admin').all()
    
    return render_template('admin/paneladmin.html', 
                           usuarios=usuarios, 
                           equipos=equipos, 
                           jugadores=jugadores,
                           categorias=categorias, # <-- AQUÍ
                           config=config,
                           traspasos_pendientes=traspasos_pendientes)

@admin_bp.route('/categoria/crear', methods=['POST'])
def crear_categoria():
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    nombre = request.form.get('nombre')
    if nombre:
        nueva = Categoria(nombre=nombre)
        db.session.add(nueva)
        db.session.commit()
        flash('Categoría creada con éxito.', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/categoria/editar/<int:id>', methods=['POST'])
def editar_categoria(id):
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    cat = Categoria.query.get_or_404(id)
    cat.nombre = request.form.get('nombre')
    db.session.commit()
    flash('Categoría actualizada con éxito.', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/categoria/eliminar/<int:id>', methods=['POST'])
def eliminar_categoria(id):
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoría eliminada con éxito.', 'info')
    return redirect(url_for('admin.panel'))


# --- CRUD EQUIPOS ---
@admin_bp.route('/equipo/crear', methods=['POST'])
def crear_equipo():
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    nombre = request.form.get('nombre')
    categoria_id = request.form.get('categoria_id')
    
    if nombre:
        nuevo = Equipo(
            nombre=nombre, 
            categoria_id=int(categoria_id) if categoria_id else None
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Equipo creado con éxito.', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/equipo/editar/<int:id>', methods=['POST'])
def editar_equipo(id):
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    eq = Equipo.query.get_or_404(id)
    eq.nombre = request.form.get('nombre')
    cat_id = request.form.get('categoria_id')
    eq.categoria_id = int(cat_id) if cat_id else None
    
    db.session.commit()
    flash('Equipo actualizado con éxito.', 'success')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/equipo/eliminar/<int:id>', methods=['POST'])
def eliminar_equipo(id):
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    eq = Equipo.query.get_or_404(id)
    db.session.delete(eq)
    db.session.commit()
    flash('Equipo eliminado con éxito.', 'info')
    return redirect(url_for('admin.panel'))



# NUEVA RUTA: Para que el admin pueda reasignar el equipo de un jugador
@admin_bp.route('/reasignar-jugador/<int:jugador_id>', methods=['POST'])
def reasignar_jugador(jugador_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))

    jugador = Jugador.query.get_or_404(jugador_id)
    nuevo_equipo_id = request.form.get('equipo_id')

    # Convertir a entero si viene un ID válido, de lo contrario dejar como None
    if nuevo_equipo_id and nuevo_equipo_id.isdigit():
        jugador.equipo_id = int(nuevo_equipo_id)
    else:
        jugador.equipo_id = None

    db.session.commit()
    flash(f'Se ha actualizado el equipo para {jugador.nombre}.', 'success')
    return redirect(url_for('admin.panel'))


# NUEVA RUTA: Aprobar o rechazar definitivamente el traspaso
@admin_bp.route('/resolver-traspaso/<int:traspaso_id>/<string:accion>', methods=['POST'])
def resolver_traspaso(traspaso_id, accion):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))

    traspaso = Traspaso.query.get_or_404(traspaso_id)
    jugador = Jugador.query.get_or_404(traspaso.jugador_id)

    if accion == 'aprobar':
        # 1. Cambiar el equipo del jugador al equipo destino
        jugador.equipo_id = traspaso.equipo_destino_id
        
        # 2. Si se especificó una nueva fecha de contrato, actualizarla
        if traspaso.nuevo_fecha_fin:
            jugador.fecha_fin = traspaso.nuevo_fecha_fin
            
        # 3. Marcar el traspaso como Avalado / Aprobado
        traspaso.estado = 'Completado'
        db.session.commit()
        
        flash(f'Traspaso aprobado con éxito. {jugador.nombre} ahora pertenece a {traspaso.equipo_destino.nombre}.', 'success')
        
    elif accion == 'rechazar':
        traspaso.estado = 'Rechazado_Admin'
        db.session.commit()
        flash('El traspaso ha sido rechazado por la administración.', 'info')

    return redirect(url_for('admin.panel'))

@admin_bp.route('/toggle-mercado', methods=['POST'])
def toggle_mercado():
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    config = Configuracion.query.first()
    if config:
        # Invertimos el valor actual (Si es True pasa a False, y viceversa)
        config.mercado_abierto = not config.mercado_abierto
        db.session.commit()
        
        estado = "ABIERTO" if config.mercado_abierto else "CERRADO"
        flash(f'El mercado de fichajes ahora está {estado}.', 'success')
        
    return redirect(url_for('admin.panel'))

@admin_bp.route('/asignar-delegado/<int:equipo_id>', methods=['POST'])
def asignar_delegado(equipo_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    equipo = Equipo.query.get_or_404(equipo_id)
    usuario_id = request.form.get('usuario_id')
    
    if usuario_id:
        equipo.delegado_id = int(usuario_id)
        # Actualizar automáticamente el rol del usuario a 'delegado' si era un usuario común
        usuario = Usuario.query.get(usuario_id)
        if usuario and usuario.rol == 'usuario':
            usuario.rol = 'delegado'
        
        db.session.commit()
        flash(f'Delegado asignado correctamente a {equipo.nombre}.', 'success')
    else:
        equipo.delegado_id = None
        db.session.commit()
        flash(f'Se removió el delegado del equipo {equipo.nombre}.', 'info')
        
    return redirect(url_for('admin.panel'))