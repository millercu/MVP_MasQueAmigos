from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    # db.create_all() crea exclusivamente las tablas que falten sin tocar los datos existentes
    db.create_all()
    print("-> ¡Tablas verificadas y creadas correctamente sin pérdida de datos!")