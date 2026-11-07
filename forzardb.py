from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 1. Asegura que todas las tablas y modelos nuevos se creen si faltan
    db.create_all()
    
    # 2. Agrega la columna torneo_id a la tabla homenajeado si no existe
    try:
        db.session.execute(text("ALTER TABLE homenajeado ADD COLUMN torneo_id INTEGER"))
        db.session.commit()
        print("Columna 'torneo_id' agregada con éxito a la tabla homenajeado.")
    except Exception as e:
        db.session.rollback()
        print("Nota: La columna 'torneo_id' ya existía en la tabla homenajeado o la tabla se creó recientemente.")
        
    print("¡Base de datos actualizada y lista!")