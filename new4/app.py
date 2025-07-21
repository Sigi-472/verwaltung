from flask import Flask, render_template_string, request, url_for
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

@app.route("/table/<tablename>")
def show_table(tablename):
    # Model anhand Tabellennamen finden
    model = None
    for m in get_model_classes():
        if m.__tablename__ == tablename:
            model = m
            break
    if not model:
        return f"Table {tablename} not found", 404

    # Session öffnen und alle Zeilen abfragen
    with Session(engine) as session:
        rows = session.query(model).all()

    # Spalten definieren — hier müsste man das anpassen, evtl. dynamisch oder hardcoded
    # Beispiel: alle Spalten des Models (außer Beziehungsspalten) anzeigen
    columns = []
    for col in model.__table__.columns:
        columns.append((tablename, col.name, col.name.capitalize(), False))

    # HTML-Table generieren
    html_table = generate_editable_table(rows, columns, id_column='id')

    # Seite rendern mit Link zurück und der Tabelle
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
