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

# ------------- Hilfsfunktion: Suche nach sinnvollen Suchfeldern ----------
def get_searchable_fields(model):
    """Versucht für das Model sinnvolle Felder für AJAX-Suche zu finden."""
    mapper = inspect(model)
    # Priorität: name, first_name, last_name, email, id als Fallback
    candidates = ['name', 'first_name', 'last_name', 'email']
    available = [c.key for c in mapper.columns]
    fields = [f for f in candidates if f in available]
    if not fields:
        fields = ['id']
    return fields

# ------------- Automatisch alle Models registrieren --------------
def register_all_models(admin_obj, db_session, base):

    def is_fk_column(column):
        return len(column.foreign_keys) > 0

    def create_modelview_for_model(model):
        mapper = inspect(model)
        columns = mapper.columns
        relationships = mapper.relationships

        normal_cols = [c for c in columns if not is_fk_column(c) and c.key != "id"]
        fk_cols = [c for c in columns if is_fk_column(c) and c.key != "id"]

        if len(normal_cols) == 0 and len(fk_cols) > 0:
            # Nur id + FKs => benutze relationships als Formularfelder
            form_cols = [rel.key for rel in relationships]

            form_ajax_refs = {}
            for rel in relationships:
                target_model = rel.mapper.class_
                fields = get_searchable_fields(target_model)
                if fields:
                    # Hier absichern, dass fields nicht leer sind
                    form_ajax_refs[rel.key] = {
                        'fields': fields,
                        'get_label': fields[0],  # Nehme erstes Suchfeld als Label
                    }

            CustomModelView = type(
                'CustomModelView',
                (ModelView,),
                {
                    'form_columns': form_cols,
                    'form_ajax_refs': form_ajax_refs
                }
            )
            return CustomModelView(model, db_session)
        else:
            return ModelView(model, db_session)

    for mapper in base.registry.mappers:
        cls = mapper.class_
        admin_view = create_modelview_for_model(cls)
        admin_obj.add_view(admin_view)

register_all_models(admin, db_session, Base)

# ------------- Flask main -----------------
if __name__ == "__main__":
    app.run(debug=True)
