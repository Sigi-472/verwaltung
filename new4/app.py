from flask import Flask, redirect, render_template_string, request, url_for
from sqlalchemy import create_engine
from flask import request, redirect, render_template_string
from sqlalchemy.orm import class_mapper, ColumnProperty, RelationshipProperty, Session
from sqlalchemy.orm import Session, class_mapper, ColumnProperty, RelationshipProperty
from db_defs import *  # deine Models
from db_helpers import generate_editable_table

app = Flask(__name__)
engine = create_engine("sqlite:///mydatabase.db", echo=False)

def get_model_classes():
    return [mapper.class_ for mapper in Base.registry.mappers]

@app.route("/")
def index():
    models = get_model_classes()
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
    model = next((m for m in get_model_classes() if m.__tablename__ == tablename), None)
    if not model:
        return f"Table {tablename} not found", 404

    id_column = "id"

    with Session(engine) as session:
        # === Dynamische Spaltendefinition ===
        columns = []
        fk_relations = {}  # Relationship-Name -> Klasse

        # Spalten Hauptmodell
        for prop in class_mapper(model).iterate_properties:
            if isinstance(prop, ColumnProperty):
                col = prop.columns[0]
                if col.primary_key:
                    continue
                columns.append((tablename, col.name, col.name.capitalize(), False))

        # FK-Relationen ermitteln
        for prop in class_mapper(model).iterate_properties:
            if isinstance(prop, RelationshipProperty):
                fk_relations[prop.key] = prop.mapper.class_

                # FK-Modellspalten anhängen (ohne PK/FK-Spalten)
                fk_model = prop.mapper.class_
                for fk_prop in class_mapper(fk_model).iterate_properties:
                    if isinstance(fk_prop, ColumnProperty):
                        col = fk_prop.columns[0]
                        if col.primary_key or col.foreign_keys:
                            continue
                        label = f"{prop.key}.{col.name}"
                        columns.append((tablename, f"{prop.key}.{col.name}", label, False))

        if request.method == "POST":
            new_main_data = {}
            new_fk_data = {}

            for key, val in request.form.items():
                parts = key.split(":")
                if len(parts) != 3:
                    continue
                tname, colname, rowid = parts
                if tname != tablename:
                    continue
                val = val if val != "" else None

                if rowid == "new":
                    if "." in colname:
                        fk_col, sub_col = colname.split(".", 1)
                        new_fk_data.setdefault(fk_col, {})[sub_col] = val
                    else:
                        new_main_data[colname] = val
                    continue

                # Update bestehendes Objekt
                obj = session.get(model, rowid)
                if not obj:
                    continue

                if "." in colname:
                    fk_col, sub_col = colname.split(".", 1)
                    fk_obj = getattr(obj, fk_col)
                    if not fk_obj:
                        fk_cls = fk_relations.get(fk_col)
                        if not fk_cls:
                            continue
                        fk_obj = fk_cls()
                        setattr(obj, fk_col, fk_obj)
                        session.add(fk_obj)
                    setattr(fk_obj, sub_col, val)
                else:
                    if colname == id_column:
                        continue
                    setattr(obj, colname, val)

            # Neue Objekte anlegen
            if new_main_data or new_fk_data:
                new_fk_objs = {}
                for fk_col, sub_data in new_fk_data.items():
                    fk_cls = fk_relations.get(fk_col)
                    if not fk_cls:
                        continue
                    fk_obj = fk_cls()
                    for k, v in sub_data.items():
                        setattr(fk_obj, k, v)
                    session.add(fk_obj)
                    new_fk_objs[fk_col] = fk_obj

                new_obj = model()
                for k, v in new_main_data.items():
                    if k == id_column:
                        continue
                    setattr(new_obj, k, v)
                for fk_col, fk_obj in new_fk_objs.items():
                    setattr(new_obj, fk_col, fk_obj)
                session.add(new_obj)

            session.commit()
            return redirect(request.url)

        rows = session.query(model).all()
        html_table = generate_editable_table(rows, columns, id_column=id_column, allow_add_row=True)

    html_tpl = """
    <a href="{{ url_for('index') }}">&lt;&lt; Back to tables</a>
    <h1>Table: {{ tablename }}</h1>
    {{ html_table|safe }}
    """
    return render_template_string(html_tpl, tablename=tablename, html_table=html_table)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    app.run(debug=True)
