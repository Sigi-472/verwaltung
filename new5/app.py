from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect
from db_defs import Base

# ------------- DB Setup -------------------
engine = create_engine("sqlite:///test.db", echo=True)  # Beispiel SQLite DB
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

# ------------- Flask Setup ----------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"
app.config["FLASK_ADMIN_SWATCH"] = "cerulean"  # Optisch nett

admin = Admin(app, name="My Admin", template_mode="bootstrap4")


# ------------- Automatisch alle Models registrieren --------------
def register_all_models(admin_obj, db_session, base):
    for mapper in base.registry.mappers:
        cls = mapper.class_
        admin_obj.add_view(ModelView(cls, db_session))

register_all_models(admin, db_session, Base)

# ------------- Flask main -----------------
if __name__ == "__main__":
    app.run(debug=True)
