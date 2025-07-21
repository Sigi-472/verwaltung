from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.views import ModelView
from db_defs import Base  # Deine Models hier

# ------------- Flask Setup ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ------------- SQLAlchemy & AppBuilder Init --------------
db = SQLA(app)
appbuilder = AppBuilder(app, db.session)

# ------------- DB Setup ----------------
# Erstelle Tabellen (wie bei Flask-Admin)
Base.metadata.create_all(db.engine)

# ------------- Automatisch alle Models registrieren --------------
from sqlalchemy.inspection import inspect

def register_all_models_appbuilder(appbuilder, base):
    for mapper in base.registry.mappers:
        model = mapper.class_
        cols = [c.key for c in inspect(model).columns]

        view_name = f"{model.__name__}ModelView"

        AutoModelView = type(
            view_name,
            (ModelView,),
            dict(
                datamodel=SQLAInterface(model),
                list_columns=cols,      # explizit alle Spalten zeigen
                can_create=True,        # Erlaubt neue Einträge
                can_edit=True,          # Erlaubt Einträge bearbeiten
                can_delete=True         # Erlaubt Einträge löschen
            )
        )

        appbuilder.add_view(
            AutoModelView,
            model.__name__,
            icon="fa-folder-open-o",
            category="Models"
        )



register_all_models_appbuilder(appbuilder, Base)

# ------------- Flask main -----------------
if __name__ == "__main__":
    app.run(debug=True)
