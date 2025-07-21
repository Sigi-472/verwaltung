from flask import Flask, redirect, render_template_string, request, url_for
from sqlalchemy import create_engine, inspect
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

    id_column = 'id'

    with Session(engine) as session:
        if request.method == "POST":
            new_data = {}
            for key, val in request.form.items():
                parts = key.split(":")
                if len(parts) != 3:
                    continue
                tname, colname, rowid = parts
                if tname != tablename or "." in colname:
                    continue
                new_val = val if val != "" else None

                if rowid == "new":
                    new_data[colname] = new_val
                    continue

                if colname == id_column:
                    continue

                obj = session.get(model, rowid)
                if not obj:
                    continue
                setattr(obj, colname, new_val)

            if any(v is not None for v in new_data.values()):
                new_obj = model()
                for k, v in new_data.items():
                    if k == id_column:
                        continue
                    setattr(new_obj, k, v)
                session.add(new_obj)
                session.commit()
                session.refresh(new_obj)
            else:
                session.commit()

            return redirect(request.url)

        rows = session.query(model).all()

        # Dynamische Spaltendefinition
        columns = []
        fk_relations = {}  # z.B. {"issuer_id": Issuer}

        for prop in class_mapper(model).iterate_properties:
            if isinstance(prop, ColumnProperty):
                col = prop.columns[0]
                if col.primary_key:
                    continue
                # Dynamische Spaltendefinition
                columns = []
                fk_relations = {}  # z.B. {"issuer_id": Issuer}

                for prop in class_mapper(model).iterate_properties:
                    if isinstance(prop, ColumnProperty):
                        col = prop.columns[0]
                        if col.primary_key:
                            continue
                        if col.foreign_keys:
                            # FK-Spalte → versuche zugehörige Relationship zu finden
                            for rel in class_mapper(model).iterate_properties:
                                if isinstance(rel, RelationshipProperty):
                                    if col in rel.local_columns:
                                        fk_relations[col.name] = rel.mapper.class_
                                        break
                        columns.append((tablename, col.name, col.name.capitalize(), False))
                columns.append((tablename, col.name, col.name.capitalize(), False))

        # Jetzt alle lesbaren Felder aus den FK-Modellen hinzufügen
        for fk_col, fk_model in fk_relations.items():
            for prop in class_mapper(fk_model).iterate_properties:
                if isinstance(prop, ColumnProperty):
                    col = prop.columns[0]
                    if col.primary_key or col.foreign_keys:
                        continue
                    label = f"{fk_col}.{col.name}"
                    columns.append((tablename, f"{fk_col}.{col.name}", label, False))

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
