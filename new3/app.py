from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base

app = Flask(__name__)
app.secret_key = "supersecretkey"

engine = create_engine("sqlite:///db.sqlite3", echo=False)
Base.metadata.bind = engine
Session = scoped_session(sessionmaker(bind=engine))

def get_all_models():
    return [mapper.class_ for mapper in Base.registry.mappers]

def get_model_by_tablename(tablename):
    for model in get_all_models():
        if getattr(model, "__tablename__", None) == tablename:
            return model
    return None

@app.route("/")
def index():
    tables = [m.__tablename__ for m in get_all_models()]
    return render_template("index.html", tables=tables)

@app.route("/edit/<tablename>", methods=["GET", "POST"])
def edit_table(tablename):
    model = get_model_by_tablename(tablename)
    if not model:
        return f"Table {tablename} not found", 404

    session = Session()

    if request.method == "POST":
        form_data = request.form.to_dict()
        obj_id = form_data.get("id")

        if obj_id:
            obj = session.query(model).get(obj_id)
            if not obj:
                return f"Entry with id {obj_id} not found", 404
        else:
            obj = model()

        # Setze alle Spalten, außer PK (id) - Typumwandlung für Integer/Float/Date bei Bedarf noch möglich
        for col in model.__table__.columns:
            col_name = col.name
            if col.primary_key:
                continue
            if col_name in form_data:
                value = form_data[col_name]
                # Einfachheitshalber leere Strings zu None, wenn Spalte nullable
                if value == "" and col.nullable:
                    value = None
                setattr(obj, col_name, value)

        if not obj_id:
            session.add(obj)
        session.commit()
        return redirect(url_for("edit_table", tablename=tablename))

    # GET: Alle Einträge laden
    entries = session.query(model).all()
    columns = model.__table__.columns

    return render_template("edit_table.html", entries=entries, columns=columns, tablename=tablename)

if __name__ == "__main__":
    app.run(debug=True)

