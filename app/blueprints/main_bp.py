import os
from flask import Blueprint, render_template, request, session
from app.models import Traspaso,Homenajeado,  Usuario, Configuracion, PodioEsports, PodioYeimi, Categoria, Partido, Torneo, EstadisticaPartido, Jugador, Equipo, Carrusel, Patrocinador
from sqlalchemy import func
from app.extensions import db
from werkzeug.utils import secure_filename
from flask import request, session, redirect, url_for, flash

main_bp = Blueprint('main', __name__)

def obtener_torneo_seleccionado():
    """Función auxiliar para mantener el torneo activo o seleccionado en la sesión activa del usuario."""
    torneos = Torneo.query.order_by(Torneo.fecha_creacion.desc()).all()
    torneo_id = request.args.get('torneo_id', type=int)
    torneo_seleccionado = None

    if torneo_id:
        torneo_seleccionado = Torneo.query.get(torneo_id)
        if torneo_seleccionado:
            session['torneo_id'] = torneo_seleccionado.id
    elif 'torneo_id' in session:
        torneo_seleccionado = Torneo.query.get(session['torneo_id'])

    if not torneo_seleccionado:
        torneo_seleccionado = Torneo.query.filter_by(estado='Activo').first()
        if not torneo_seleccionado and torneos:
            torneo_seleccionado = torneos[0]
        if torneo_seleccionado:
            session['torneo_id'] = torneo_seleccionado.id

    return torneos, torneo_seleccionado

@main_bp.route('/')
def index():
    torneos, torneo_seleccionado = obtener_torneo_seleccionado()
            
    # Rescatar categorías huérfanas públicas por seguridad
    categorias_huerfanas = Categoria.query.filter_by(torneo_id=None).all()
    if categorias_huerfanas and torneo_seleccionado:
        for cat in categorias_huerfanas:
            cat.torneo_id = torneo_seleccionado.id
        db.session.commit()

    # Inicializar listas vacías
    categorias = []
    partidos_jugados = []
    podios_esports = []
    podios_yeimi = []
    homenajeados = []

    if torneo_seleccionado:
        # Categorías del torneo activo/seleccionado
        categorias = Categoria.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        cat_ids = [c.id for c in categorias]
        
        if cat_ids:
            partidos_jugados = Partido.query.filter(Partido.categoria_id.in_(cat_ids), Partido.estado == 'Jugado').all()
            podios_esports = PodioEsports.query.filter(PodioEsports.categoria_id.in_(cat_ids)).all()
            podios_yeimi = PodioYeimi.query.filter(PodioYeimi.categoria_id.in_(cat_ids)).all()
        
        # Filtramos los homenajeados. Utilizamos try/except por si el modelo Homenajeado aún no tiene torneo_id
        try:
            homenajeados = Homenajeado.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        except Exception:
            homenajeados = Homenajeado.query.all()
            
    else:
        # Si no hay ningún torneo seleccionado, cargamos todo de forma global
        try:
            homenajeados = Homenajeado.query.filter_by(torneo_id=None).all()
        except Exception:
            homenajeados = Homenajeado.query.all()

    carrusel_imagenes = Carrusel.query.order_by(Carrusel.orden.asc()).all()
    patrocinadores = Patrocinador.query.all()

    return render_template('index.html', 
                           categorias=categorias, 
                           partidos_jugados=partidos_jugados,
                           torneos=torneos,
                           torneo_seleccionado=torneo_seleccionado,
                           carrusel_imagenes=carrusel_imagenes,
                           patrocinadores=patrocinadores,
                           homenajeados=homenajeados,
                           podios_esports=podios_esports,
                           podios_yeimi=podios_yeimi)

@main_bp.route('/historial-fichajes')
def historial_fichajes():
    config = Configuracion.query.first()
    torneos, torneo_seleccionado = obtener_torneo_seleccionado()

    if torneo_seleccionado:
        categorias = Categoria.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        cat_ids = [c.id for c in categorias]
        equipos_ids = [e.id for e in Equipo.query.filter(Equipo.categoria_id.in_(cat_ids)).all()]
        
        traspasos_completados = Traspaso.query.filter(
            Traspaso.estado == 'Completado',
            Traspaso.equipo_destino_id.in_(equipos_ids)
        ).all() if equipos_ids else []
    else:
        traspasos_completados = []
    
    return render_template('fichajes.html', 
                           traspasos=traspasos_completados,
                           config=config,
                           torneos=torneos,
                           torneo_seleccionado=torneo_seleccionado)

@main_bp.route('/estadisticas-generales')
def estadisticas_generales():
    torneos, torneo_seleccionado = obtener_torneo_seleccionado()

    if torneo_seleccionado:
        categorias = Categoria.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        cat_ids = [c.id for c in categorias]
        partidos_ids = [p.id for p in Partido.query.filter(Partido.categoria_id.in_(cat_ids)).all()] if cat_ids else []
    else:
        partidos_ids = []

    if partidos_ids:
        goleadores = db.session.query(Jugador, func.sum(EstadisticaPartido.goles).label('total_goles'))\
            .join(EstadisticaPartido).filter(EstadisticaPartido.partido_id.in_(partidos_ids))\
            .group_by(Jugador.id).order_by(func.sum(EstadisticaPartido.goles).desc()).all()

        asistentes = db.session.query(Jugador, func.sum(EstadisticaPartido.asistencias).label('total_asistencias'))\
            .join(EstadisticaPartido).filter(EstadisticaPartido.partido_id.in_(partidos_ids))\
            .group_by(Jugador.id).order_by(func.sum(EstadisticaPartido.asistencias).desc()).all()

        fair_play = db.session.query(Equipo, func.sum(EstadisticaPartido.amarillas).label('total_amarillas'), func.sum(EstadisticaPartido.rojas).label('total_rojas'))\
            .join(EstadisticaPartido, Equipo.id == EstadisticaPartido.equipo_id)\
            .filter(EstadisticaPartido.partido_id.in_(partidos_ids))\
            .group_by(Equipo.id).order_by(func.sum(EstadisticaPartido.rojas).asc(), func.sum(EstadisticaPartido.amarillas).asc()).all()
    else:
        goleadores, asistentes, fair_play = [], [], []

    return render_template('futbol/estadisticasgenerales.html', 
                           goleadores=goleadores, asistentes=asistentes, fair_play=fair_play,
                           torneos=torneos, torneo_seleccionado=torneo_seleccionado)

@main_bp.route('/equipo/<int:equipo_id>')
def ver_equipo(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    jugadores = Jugador.query.filter_by(equipo_id=equipo.id).all()
    return render_template('futbol/detalleequipo.html', equipo=equipo, jugadores=jugadores)


@main_bp.route('/editar-perfil', methods=['POST'])
def editar_perfil():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario = Usuario.query.get(session['user_id'])
    
    # Actualizar Datos Básicos
    usuario.nombres = request.form.get('nombres')
    usuario.telefono = request.form.get('telefono')
    session['user_nombre'] = usuario.nombres # Actualizar sesión principal
    
    # Subir/Actualizar Foto de Perfil
    foto = request.files.get('foto_perfil')
    if foto and foto.filename:
        filename = secure_filename(f"user_{usuario.id}_{foto.filename}")
        os.makedirs('app/static/uploads', exist_ok=True)
        foto.save(os.path.join('app/static/uploads', filename))
        usuario.foto_perfil = filename
        
    db.session.commit()
    flash('Tu perfil ha sido actualizado exitosamente.', 'success')
    return redirect(request.referrer)