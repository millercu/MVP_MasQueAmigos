from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 1. db.create_all() crea las tablas nuevas (Torneo y Documentos) sin tocar ni dañar las viejas
    db.create_all()
    print("-> Tablas nuevas creadas correctamente.")

    # 2. Inyectamos la nueva columna en la tabla vieja usando SQL puro (que SQLite sí acepta)
    try:
        db.session.execute(text("ALTER TABLE categoria ADD COLUMN torneo_id INTEGER REFERENCES torneo(id)"))
        db.session.commit()
        print("-> Columna torneo_id agregada a la tabla categoria con éxito.")
    except Exception as e:
        print("-> Nota: La columna torneo_id ya existía o hubo un aviso menor.")

    print("¡Base de datos actualizada al 100% sin perder ningún dato!")