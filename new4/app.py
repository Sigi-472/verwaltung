from flask import Flask, redirect, render_template_string, request, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db_defs import *  # deine Models
from db_helpers import generate_editable_table

app = Flask(__name__)

# Engine einmal global erzeugen
engine = create_engine("sqlite:///mydatabase.db", echo=False)

# Helfer, um alle Models zu bekommen
def get_models():
    # Hier holen wir alle Klassen, die Base.metadata enthalten
    # Base.metadata.tables ist ein dict mit Tabellennamen
    # Aber wir wollen die Klassen/Models
    return Base._decl_class_registry.values()

# Wir nehmen nur SQLAlchemy Models (Klassen mit __table__)
def get_model_classes():
    return [mapper.class_ for mapper in Base.registry.mappers]

@app.route("/")
def index():
    models = get_model_classes()
    # Wir bauen eine Liste von (Name der Tabelle, Model-Klasse)
    table_list = [(m.__tablename__, m) for m in models]

    html = """
    <h1>Available Tables</h1>
    <ul>
    {% for tablename, model in tables %}
      <li><a href="{{ url_for('show_table', tablename=tablename) }}">{{ tablename }}</a></li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, tables=table_list)

@app.route("/table/<tablename>", methods=["GET", "POST"])
def show_table(tablename):
    # Model anhand Tabellennamen finden
    model = None
    for m in get_model_classes():
        if m.__tablename__ == tablename:
            model = m
            break
    if not model:
        return f"Table {tablename} not found", 404

    id_column = 'id'  # falls bei dir ein anderer Name, anpassen!

    with Session(engine) as session:
        if request.method == "POST":
            # Formular-Daten bearbeiten
            # Erwartet Eingaben mit Name = tablename:column:rowid

            for key, val in request.form.items():
                # key = "tablename:column:rowid"
                parts = key.split(":")
                if len(parts) != 3:
                    continue  # unerwartetes Format ignorieren
                tname, colname, rowid = parts
                if tname != tablename:
                    continue  # andere Tabelle ignorieren

                # Datensatz holen
                obj = session.get(model, rowid)
                if not obj:
                    continue  # ungültige ID ignorieren

                # Leere Strings zu None konvertieren
                new_val = val if val != "" else None

                # Spalte darf nicht Primärschlüssel sein, nicht updaten
                if colname == id_column:
                    continue

                # Attribut aktualisieren
                setattr(obj, colname, new_val)

            session.commit()
            return redirect(request.url)  # Nach Post-Redirect-Get

        # GET: Daten abfragen und Tabelle anzeigen
        rows = session.query(model).all()

        # Spalten definieren, ohne Primary Key
        columns = []
        for col in model.__table__.columns:
            if col.name == id_column:
                continue
            columns.append((tablename, col.name, col.name.capitalize(), False))

        html_table = generate_editable_table(rows, columns, id_column=id_column)

    html = """
    <a href="{{ url_for('index') }}">&lt;&lt; Back to tables</a>
    <h1>Table: {{ tablename }}</h1>
    {{ html_table|safe }}
    """

    return render_template_string(html, tablename=tablename, html_table=html_table)

if __name__ == "__main__":
    # DB Tabellen erzeugen
    Base.metadata.create_all(engine)
    app.run(debug=True)
