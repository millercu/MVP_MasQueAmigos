from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import Torneo, Categoria, PodioYeimi

yeimi_bp = Blueprint('yeimi', __name__, template_folder='templates/yeimi')

@yeimi_bp.route('/panel')
def panel():
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    torneo_activo = Torneo.query.filter_by(estado='Activo').first()
    # Filtramos categorías que contengan "yeimi" en su nombre
    if torneo_activo:
        categorias = Categoria.query.filter(
            Categoria.torneo_id == torneo_activo.id,
            Categoria.nombre.ilike('%yeimi%')
        ).all()
    else:
        categorias = []
        
    return render_template('yeimi/panelyeimi.html', categorias=categorias)

@yeimi_bp.route('/guardar-podio/<int:categoria_id>', methods=['POST'])
def guardar_podio(categoria_id):
    if session.get('user_rol') != 'admin': return redirect(url_for('main.index'))
    
    categoria = Categoria.query.get_or_404(categoria_id)
    podio = PodioYeimi.query.filter_by(categoria_id=categoria.id).first()
    
    if not podio:
        podio = PodioYeimi(categoria_id=categoria.id)
        db.session.add(podio)
        
    podio.campeon_id = request.form.get('campeon_id') or None
    podio.subcampeon_id = request.form.get('subcampeon_id') or None
    podio.tercer_puesto_id = request.form.get('tercer_puesto_id') or None
    
    db.session.commit()
    return redirect(url_for('yeimi.panel'))

@yeimi_bp.route('/eliminar-podio/<int:categoria_id>', methods=['POST'])
def eliminar_podio(categoria_id):
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.index'))
        
    podio = PodioYeimi.query.filter_by(categoria_id=categoria_id).first()
    if podio:
        db.session.delete(podio)
        db.session.commit()
        flash('El podio de esta categoría ha sido eliminado correctamente.', 'info')
    
    return redirect(url_for('yeimi.panel'))