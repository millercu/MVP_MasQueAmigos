import random
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import Usuario, Equipo, Configuracion, Traspaso, Jugador, Categoria, Partido, DocumentoTorneo, Torneo, PodioEsports

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/panel')
def panel():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    usuarios = Usuario.query.all()
    jugadores = Jugador.query.all()
    config = Configuracion.query.first()
    traspasos_pendientes = Traspaso.query.filter_by(estado='Pendiente_Admin').all()
    
    torneos = Torneo.query.order_by(Torneo.fecha_creacion.desc()).all()
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    
    # AUTOCORRECCIÓN 1: Si no hay torneos creados, creamos uno principal por defecto
    if not torneo_activo:
        if not torneos:
            torneo_activo = Torneo(nombre="Torneo Principal", estado='Activo')
            db.session.add(torneo_activo)
            db.session.commit()
            torneos = [torneo_activo]
        else:
            torneo_activo = torneos[0]
            torneo_activo.estado = 'Activo'
            db.session.commit()

    # AUTOCORRECCIÓN 2: Rescatar automáticamente categorías antiguas sin torneo asignado
    categorias_huerfanas = Categoria.query.filter_by(torneo_id=None).all()
    if categorias_huerfanas:
        for cat in categorias_huerfanas:
            cat.torneo_id = torneo_activo.id
        db.session.commit()
    
    # Filtrar información del torneo activo
    categorias = Categoria.query.filter_by(torneo_id=torneo_activo.id).all()
    cat_ids = [c.id for c in categorias]
    
    equipos = Equipo.query.filter(Equipo.categoria_id.in_(cat_ids)).all() if cat_ids else []
    partidos = Partido.query.filter(Partido.categoria_id.in_(cat_ids)).all() if cat_ids else []
    documentos = DocumentoTorneo.query.filter_by(torneo_id=torneo_activo.id).order_by(DocumentoTorneo.fecha_subida.desc()).all()
    
    return render_template('admin/paneladmin.html', 
                           usuarios=usuarios, 
                           equipos=equipos, 
                           jugadores=jugadores,
                           categorias=categorias, 
                           config=config,
                           traspasos_pendientes=traspasos_pendientes,
                           partidos=partidos,
                           documentos=documentos,
                           torneos=torneos,
                           torneo_activo=torneo_activo)



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

        # NUEVO: Establecer la fecha de hoy como inicio del nuevo contrato
        jugador.fecha_inicio = datetime.today().strftime('%Y-%m-%d')

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
        equipo.usuario_id = int(usuario_id)
        # Actualizar automáticamente el rol del usuario a 'delegado' si era un usuario común
        usuario = Usuario.query.get(usuario_id)
        if usuario and usuario.rol == 'usuario':
            usuario.rol = 'delegado'
        
        db.session.commit()
        flash(f'Delegado asignado correctamente a {equipo.nombre}.', 'success')
    else:
        equipo.usuario_id = None
        db.session.commit()
        flash(f'Se removió el delegado del equipo {equipo.nombre}.', 'info')
        
    return redirect(url_for('admin.panel'))


@admin_bp.route('/generar-fixture/<int:categoria_id>', methods=['POST'])
def generar_fixture(categoria_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    categoria = Categoria.query.get_or_404(categoria_id)
    equipos = Equipo.query.filter_by(categoria_id=categoria_id).all()
    
    # Validar que no exista un fixture previo
    if Partido.query.filter_by(categoria_id=categoria_id).first():
        flash(f'El fixture para {categoria.nombre} ya fue generado anteriormente.', 'danger')
        return redirect(url_for('admin.panel'))

    # CATEGORÍA FEMENINA (Semifinal Directa: Requiere exactamente 4 equipos)
    if len(equipos) == 4:
        random.shuffle(equipos) # Sorteo aleatorio
        
        # Crear la Final y Tercer Puesto vacíos primero para poder enlazarlos
        final = Partido(categoria_id=categoria.id, fase='Final', info_local='Ganador Semi 1', info_visitante='Ganador Semi 2')
        tercer_puesto = Partido(categoria_id=categoria.id, fase='Tercer Puesto', info_local='Perdedor Semi 1', info_visitante='Perdedor Semi 2')
        db.session.add_all([final, tercer_puesto])
        db.session.commit() # Guardar para obtener sus IDs
        
        # Crear Semifinales y conectarlas a la final y tercer puesto
        semi1 = Partido(categoria_id=categoria.id, fase='Semifinal 1', equipo_local_id=equipos[0].id, equipo_visitante_id=equipos[1].id,
                        partido_siguiente_ganador_id=final.id, partido_siguiente_perdedor_id=tercer_puesto.id)
        semi2 = Partido(categoria_id=categoria.id, fase='Semifinal 2', equipo_local_id=equipos[2].id, equipo_visitante_id=equipos[3].id,
                        partido_siguiente_ganador_id=final.id, partido_siguiente_perdedor_id=tercer_puesto.id)
        
        db.session.add_all([semi1, semi2])
        db.session.commit()
        flash(f'Fixture generado con éxito para {categoria.nombre} (Sorteo Semifinal Directa).', 'success')

    # CATEGORÍA MASCULINA (Repechaje: Requiere exactamente 5 equipos)
    elif len(equipos) == 5:
        # El formulario enviará los IDs del 4to y 5to puesto para el repechaje
        id_repechaje_1 = int(request.form.get('equipo_4_id'))
        id_repechaje_2 = int(request.form.get('equipo_5_id'))
        
        if not id_repechaje_1 or not id_repechaje_2 or id_repechaje_1 == id_repechaje_2:
            flash('Debes seleccionar dos equipos distintos para el partido de repechaje.', 'danger')
            return redirect(url_for('admin.panel'))
            
        eq_repechaje = [e for e in equipos if e.id in [id_repechaje_1, id_repechaje_2]]
        eq_semis = [e for e in equipos if e.id not in [id_repechaje_1, id_repechaje_2]]
        
        random.shuffle(eq_semis) # Sorteo aleatorio de los 3 restantes
        
        # Crear Final y Tercer Puesto
        final = Partido(categoria_id=categoria.id, fase='Final', info_local='Ganador Semi 1', info_visitante='Ganador Semi 2')
        tercer_puesto = Partido(categoria_id=categoria.id, fase='Tercer Puesto', info_local='Perdedor Semi 1', info_visitante='Perdedor Semi 2')
        db.session.add_all([final, tercer_puesto])
        db.session.commit()
        
        # Crear Semifinales conectadas
        semi1 = Partido(categoria_id=categoria.id, fase='Semifinal 1', equipo_local_id=eq_semis[0].id, equipo_visitante_id=eq_semis[1].id,
                        partido_siguiente_ganador_id=final.id, partido_siguiente_perdedor_id=tercer_puesto.id)
        
        # Semifinal 2 espera al ganador del repechaje
        semi2 = Partido(categoria_id=categoria.id, fase='Semifinal 2', equipo_local_id=eq_semis[2].id, info_visitante='Ganador Repechaje',
                        partido_siguiente_ganador_id=final.id, partido_siguiente_perdedor_id=tercer_puesto.id)
        db.session.add_all([semi1, semi2])
        db.session.commit()
        
        # Crear Repechaje conectado a la Semifinal 2
        repechaje = Partido(categoria_id=categoria.id, fase='Repechaje', equipo_local_id=eq_repechaje[0].id, equipo_visitante_id=eq_repechaje[1].id,
                            partido_siguiente_ganador_id=semi2.id)
        db.session.add(repechaje)
        db.session.commit()
        
        flash(f'Fixture generado con éxito para {categoria.nombre} (Formato Repechaje).', 'success')
        
    else:
        flash(f'La categoría {categoria.nombre} tiene {len(equipos)} equipos. Se requieren exactamente 4 o 5 equipos para generar un fixture válido.', 'warning')

    return redirect(url_for('admin.panel'))

@admin_bp.route('/partido/programar/<int:partido_id>', methods=['POST'])
def programar_partido(partido_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    partido = Partido.query.get_or_404(partido_id)
    
    # Recibimos los datos del formulario
    partido.fecha = request.form.get('fecha')
    partido.hora = request.form.get('hora')
    partido.cancha = request.form.get('cancha')
    
    db.session.commit()
    flash('Partido programado con éxito.', 'success')
    return redirect(url_for('admin.panel'))


from app.models import Usuario, Equipo, Configuracion, Traspaso, Jugador, Categoria, Partido, EstadisticaPartido

@admin_bp.route('/partido/acta/<int:partido_id>', methods=['GET', 'POST'])
def acta_partido(partido_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    partido = Partido.query.get_or_404(partido_id)

    if not partido.fecha or not partido.hora:
        flash('No se puede registrar el acta de un partido que aún no ha sido programado.', 'danger')
        return redirect(url_for('admin.panel'))
    
    if request.method == 'POST':
        try:
            goles_local = int(request.form.get('goles_local', 0))
            goles_visitante = int(request.form.get('goles_visitante', 0))
            penales_local_str = request.form.get('penales_local')
            penales_visitante_str = request.form.get('penales_visitante')
            
            penales_local = int(penales_local_str) if penales_local_str and penales_local_str.isdigit() else None
            penales_visitante = int(penales_visitante_str) if penales_visitante_str and penales_visitante_str.isdigit() else None
        except ValueError:
            flash('Los valores de goles y penales deben ser numéricos.', 'danger')
            return redirect(url_for('admin.acta_partido', partido_id=partido.id))
            
        # 1. Actualizar resultado global del partido y marcar como Jugado
        partido.goles_local = goles_local
        partido.goles_visitante = goles_visitante
        partido.penales_local = penales_local
        partido.penales_visitante = penales_visitante
        partido.estado = 'Jugado'
        
        # 2. Limpiar estadísticas individuales anteriores para evitar duplicados si se edita
        EstadisticaPartido.query.filter_by(partido_id=partido.id).delete()
        
        # Obtener todos los jugadores de ambos equipos
        jugadores_ids = []
        if partido.equipo_local_id:
            jl = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
            jugadores_ids.extend(jl)
        if partido.equipo_visitante_id:
            jv = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
            jugadores_ids.extend(jv)
            
        # Registrar estadísticas de cada jugador enviado en el formulario
        for j in jugadores_ids:
            g = int(request.form.get(f'gol_{j.id}', 0))
            a = int(request.form.get(f'asis_{j.id}', 0))
            am = int(request.form.get(f'ama_{j.id}', 0))
            r = int(request.form.get(f'roj_{j.id}', 0))
            
            if g > 0 or a > 0 or am > 0 or r > 0:
                stat = EstadisticaPartido(
                    partido_id=partido.id,
                    jugador_id=j.id,
                    equipo_id=j.equipo_id,
                    goles=g,
                    asistencias=a,
                    amarillas=am,
                    rojas=r
                )
                db.session.add(stat)
                
        # 3. Determinar Ganador y Perdedor
        ganador_id = None
        perdedor_id = None
        
        if goles_local > goles_visitante:
            ganador_id = partido.equipo_local_id
            perdedor_id = partido.equipo_visitante_id
        elif goles_visitante > goles_local:
            ganador_id = partido.equipo_visitante_id
            perdedor_id = partido.equipo_local_id
        else:
            # En caso de empate, evaluar tanda de penales
            if penales_local is not None and penales_visitante is not None:
                if penales_local > penales_visitante:
                    ganador_id = partido.equipo_local_id
                    perdedor_id = partido.equipo_visitante_id
                elif penales_visitante > penales_local:
                    ganador_id = partido.equipo_visitante_id
                    perdedor_id = partido.equipo_local_id
                    
        # 4. Avance automático de ronda en el fixture
        if ganador_id and partido.partido_siguiente_ganador_id:
            sig_ganador = Partido.query.get(partido.partido_siguiente_ganador_id)
            if sig_ganador:
                if not sig_ganador.equipo_local_id:
                    sig_ganador.equipo_local_id = ganador_id
                elif sig_ganador.equipo_visitante_id != ganador_id and not sig_ganador.equipo_visitante_id:
                    sig_ganador.equipo_visitante_id = ganador_id
                    
        if perdedor_id and partido.partido_siguiente_perdedor_id:
            sig_perdedor = Partido.query.get(partido.partido_siguiente_perdedor_id)
            if sig_perdedor:
                if not sig_perdedor.equipo_local_id:
                    sig_perdedor.equipo_local_id = perdedor_id
                elif sig_perdedor.equipo_visitante_id != perdedor_id and not sig_perdedor.equipo_visitante_id:
                    sig_perdedor.equipo_visitante_id = perdedor_id
                    
        # Excepción específica para el Repechaje Masculino (conecta con Semifinal 2)
        if partido.fase == 'Repechaje' and ganador_id:
            semi2 = Partido.query.filter_by(categoria_id=partido.categoria_id, fase='Semifinal 2').first()
            if semi2 and not semi2.equipo_visitante_id:
                semi2.equipo_visitante_id = ganador_id
                
        db.session.commit()
        flash('¡Acta guardada con éxito! El fixture se ha actualizado de manera automática.', 'success')
        return redirect(url_for('admin.panel'))
        
    # Si es GET, preparamos las listas de jugadores y detectamos suspensiones por tarjeta roja previa
    jugadores_local = []
    jugadores_visitante = []
    
    # Identificar partidos previos jugados en esta categoría para buscar tarjetas rojas
    partidos_previos = Partido.query.filter_by(categoria_id=partido.categoria_id, estado='Jugado').all()
    partidos_previos_ids = [pt.id for pt in partidos_previos if pt.id != partido.id]
    
    jugadores_suspendidos_ids = []
    if partidos_previos_ids:
        stats_rojas = EstadisticaPartido.query.filter(
            EstadisticaPartido.partido_id.in_(partidos_previos_ids),
            EstadisticaPartido.rojas > 0
        ).all()
        jugadores_suspendidos_ids = [st.jugador_id for st in stats_rojas]

    if partido.equipo_local_id:
        jugadores_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id, rol_equipo='Deportista').all()
        
    if partido.equipo_visitante_id:
        jugadores_visitante = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id, rol_equipo='Deportista').all()
        
    estadisticas_guardadas = {stat.jugador_id: stat for stat in partido.estadisticas}
        
    return render_template('admin/actapartido.html', 
                           partido=partido, 
                           jugadores_local=jugadores_local, 
                           jugadores_visitante=jugadores_visitante,
                           estadisticas_guardadas=estadisticas_guardadas,
                           jugadores_suspendidos_ids=jugadores_suspendidos_ids)


@admin_bp.route('/subir-documento', methods=['POST'])
def subir_documento():
    if session.get('user_rol') not in ['admin', 'delegado']:
        return redirect(url_for('main.index'))

    if 'archivo' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(request.referrer)
        
    archivo = request.files['archivo']
    titulo = request.form.get('titulo')
    
    if archivo.filename == '':
        flash('El archivo no tiene nombre.', 'danger')
        return redirect(request.referrer)
        
    # 1. Obtener el torneo activo, o crear uno por defecto si es la primera vez
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    if not torneo_activo:
        torneo_activo = Torneo(nombre="Torneo Principal")
        db.session.add(torneo_activo)
        db.session.commit()
        
    if archivo and archivo.filename.endswith('.pdf'):
        filename = secure_filename(archivo.filename)
        
        # 2. Asegurar que la carpeta de destino exista antes de guardar
        directorio_destino = 'app/static/uploads'
        os.makedirs(directorio_destino, exist_ok=True)
        
        ruta_guardado = os.path.join(directorio_destino, filename)
        archivo.save(ruta_guardado)
        
        # 3. Guardar en base de datos vinculando el documento al torneo activo
        nuevo_doc = DocumentoTorneo(
            titulo=titulo,
            archivo=filename,
            subido_por_rol=session.get('user_rol'),
            torneo_id=torneo_activo.id, # Solución al error NOT NULL
            equipo_id=request.form.get('equipo_id') if request.form.get('equipo_id') else None
        )
        db.session.add(nuevo_doc)
        db.session.commit()
        flash('Documento subido correctamente.', 'success')
    else:
        flash('Solo se permiten archivos en formato PDF.', 'danger')
        
    return redirect(request.referrer)


@admin_bp.route('/eliminar-fixture/<int:categoria_id>', methods=['POST'])
def eliminar_fixture(categoria_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    # Eliminar todos los partidos (y sus estadísticas en cascada) de esta categoría
    partidos = Partido.query.filter_by(categoria_id=categoria_id).all()
    for p in partidos:
        db.session.delete(p)
        
    db.session.commit()
    flash('El fixture y todos los partidos de esta categoría han sido eliminados. Puedes volver a realizar el sorteo.', 'success')
    return redirect(url_for('admin.panel'))

from app.models import Torneo

@admin_bp.route('/eliminar-torneo/<int:torneo_id>', methods=['POST'])
def eliminar_torneo(torneo_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    torneo = Torneo.query.get_or_404(torneo_id)
    db.session.delete(torneo)
    db.session.commit()
    
    flash('El torneo y toda su información interna han sido eliminados por completo.', 'success')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/eliminar-documento/<int:doc_id>', methods=['POST'])
def eliminar_documento(doc_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    doc = DocumentoTorneo.query.get_or_404(doc_id)
    
    # 1. Eliminar el archivo PDF físico de la carpeta del servidor
    try:
        ruta_archivo = os.path.join('app/static/uploads', doc.archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
    except Exception as e:
        pass # Se ignora si el archivo ya no existe físicamente
        
    # 2. Eliminar el registro de la base de datos
    db.session.delete(doc)
    db.session.commit()
    
    flash('Documento eliminado correctamente del sistema.', 'success')
    return redirect(url_for('admin.panel'))



@admin_bp.route('/torneo/crear', methods=['POST'])
def crear_torneo():
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    nombre = request.form.get('nombre')
    if nombre:
        # Si es el primer torneo creado, lo activa por defecto
        hay_activos = Torneo.query.filter_by(estado='Activo').first()
        estado_inicial = 'Activo' if not hay_activos else 'Finalizado'
        
        nuevo_torneo = Torneo(nombre=nombre, estado=estado_inicial)
        db.session.add(nuevo_torneo)
        db.session.commit()
        flash('Torneo creado exitosamente.', 'success')
        
    return redirect(url_for('admin.panel'))

@admin_bp.route('/torneo/activar/<int:torneo_id>', methods=['POST'])
def activar_torneo(torneo_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    # Cambiar todos los torneos a estado Finalizado
    for t in Torneo.query.all():
        t.estado = 'Finalizado'
        
    # Activar únicamente el seleccionado
    torneo_seleccionado = Torneo.query.get_or_404(torneo_id)
    torneo_seleccionado.estado = 'Activo'
    db.session.commit()
    
    flash(f'El campeonato "{torneo_seleccionado.nombre}" es ahora el torneo activo.', 'success')
    return redirect(url_for('admin.panel'))

# ACTUALIZA TU RUTA DE CREAR CATEGORÍA
@admin_bp.route('/categoria/crear', methods=['POST'])
def crear_categoria():
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    nombre = request.form.get('nombre')
    
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    
    if not torneo_activo:
        flash('Debes crear y activar un torneo antes de agregar categorías.', 'danger')
        return redirect(url_for('admin.panel'))
        
    if nombre:
        nueva = Categoria(nombre=nombre, torneo_id=torneo_activo.id)
        db.session.add(nueva)
        db.session.commit()
        flash('Categoría creada con éxito.', 'success')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/torneo/vincular-antiguos', methods=['POST'])
def vincular_antiguos():
    if session.get('user_rol') != 'admin': 
        return redirect(url_for('main.index'))
    
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    if not torneo_activo:
        flash('Primero debes crear y activar un torneo.', 'danger')
        return redirect(url_for('admin.panel'))
        
    # Buscar categorías que no tengan torneo o que pertenezcan a ediciones pasadas que quieras trasladar
    categorias_huerfanas = Categoria.query.filter_by(torneo_id=None).all()
    
    if not categorias_huerfanas:
        flash('No hay categorías pendientes por vincular.', 'info')
        return redirect(url_for('admin.panel'))
        
    for cat in categorias_huerfanas:
        cat.torneo_id = torneo_activo.id
        
    db.session.commit()
    flash('¡Los equipos y categorías anteriores se han vinculado al torneo activo con éxito!', 'success')
    return redirect(url_for('admin.panel'))
