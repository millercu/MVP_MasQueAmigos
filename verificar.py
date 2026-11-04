from app import create_app
from app.extensions import db
from app.models import Usuario
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin_existente = Usuario.query.filter_by(rol='admin').first()
    if not admin_existente:
        nuevo_admin = Usuario(
            nombres="Administrador Copa Mas Que Amigos",
            tipo_documento="CC",
            documento="1000000000",
            telefono="3000000000",
            fecha_nacimiento="1990-01-01",
            email="admin@copamasqueamigos.com",
            password_hash=generate_password_hash("Admin123*"),
            rol="admin"
        )
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Usuario administrador creado con éxito!")
        print("Correo: admin@copamasqueamigos.com")
        print("Contraseña: Admin123*")
    else:
        print("Ya existe un administrador registrado en la base de datos.")