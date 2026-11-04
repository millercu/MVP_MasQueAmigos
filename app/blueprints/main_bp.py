from flask import Blueprint, render_template, request
from app.models import Traspaso, Configuracion, Categoria, Partido, Torneo, EstadisticaPartido, Jugador, Equipo, Carrusel, Patrocinador
from sqlalchemy import func
from app.extensions import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    torneos = Torneo.query.order_by(Torneo.fecha_creacion.desc()).all()
    torneo_id = request.args.get('torneo_id', type=int)
    
    if torneo_id:
        torneo_seleccionado = Torneo.query.get_or_404(torneo_id)
    else:
        torneo_seleccionado = Torneo.query.filter_by(estado='Activo').first()
        if not torneo_seleccionado:
            if torneos:
                torneo_seleccionado = torneos[0]
                torneo_seleccionado.estado = 'Activo'
                db.session.commit()
            else:
                torneo_seleccionado = Torneo(nombre="Torneo Principal", estado='Activo')
                db.session.add(torneo_seleccionado)
                db.session.commit()
                torneos = [torneo_seleccionado]
            
    # Rescatar categorías huérfanas públicas también por seguridad
    categorias_huerfanas = Categoria.query.filter_by(torneo_id=None).all()
    if categorias_huerfanas and torneo_seleccionado:
        for cat in categorias_huerfanas:
            cat.torneo_id = torneo_seleccionado.id
        db.session.commit()

    if torneo_seleccionado:
        categorias = Categoria.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        cat_ids = [c.id for c in categorias]
        partidos_jugados = Partido.query.filter(Partido.categoria_id.in_(cat_ids), Partido.estado == 'Jugado').all() if cat_ids else []
    else:
        categorias, partidos_jugados = [], []


    carrusel_imagenes = Carrusel.query.order_by(Carrusel.orden.asc()).all()
    patrocinadores = Patrocinador.query.all()

    return render_template('index.html', 
                           categorias=categorias, 
                           partidos_jugados=partidos_jugados,
                           torneos=torneos,
                           torneo_seleccionado=torneo_seleccionado,
                           carrusel_imagenes=carrusel_imagenes,
                           patrocinadores=patrocinadores)

@main_bp.route('/historial-fichajes')
def historial_fichajes():
    config = Configuracion.query.first()
    torneos = Torneo.query.order_by(Torneo.fecha_creacion.desc()).all()
    torneo_id = request.args.get('torneo_id', type=int)
    
    if torneo_id:
        torneo_seleccionado = Torneo.query.get_or_404(torneo_id)
    else:
        torneo_seleccionado = Torneo.query.filter_by(estado='Activo').first()
        if not torneo_seleccionado and torneos:
            torneo_seleccionado = torneos[0]

    if torneo_seleccionado:
        # Filtramos traspasos buscando los equipos que pertenecen al torneo seleccionado
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
    torneos = Torneo.query.order_by(Torneo.fecha_creacion.desc()).all()
    torneo_id = request.args.get('torneo_id', type=int)
    
    if torneo_id:
        torneo_seleccionado = Torneo.query.get_or_404(torneo_id)
    else:
        torneo_seleccionado = Torneo.query.filter_by(estado='Activo').first()
        if not torneo_seleccionado and torneos:
            torneo_seleccionado = torneos[0]

    # Obtenemos solo los partidos jugados en este torneo para no mezclar goles de meses pasados
    if torneo_seleccionado:
        categorias = Categoria.query.filter_by(torneo_id=torneo_seleccionado.id).all()
        cat_ids = [c.id for c in categorias]
        partidos_ids = [p.id for p in Partido.query.filter(Partido.categoria_id.in_(cat_ids)).all()]
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