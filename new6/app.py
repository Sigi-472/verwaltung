from flask import Flask, request, redirect, url_for, render_template_string, jsonify, send_from_directory
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from db_defs import Base
from markupsafe import escape
import html
from sqlalchemy import Date, DateTime
from sqlalchemy import Date, DateTime
import datetime

app = Flask(__name__)
engine = create_engine("sqlite:///test.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Deine Konfiguration:
COLUMN_LABELS = {
    "abteilung.abteilungsleiter_id": "Abteilungsleiter",
    "person.first_name": "Vorname",
    "person.last_name": "Nachname"
}

FK_DISPLAY_COLUMNS = {
    "person": "first_name"
}


def column_label(table, col):
    return COLUMN_LABELS.get(f"{table}.{col}", col.replace("_id", "").replace("_", " ").capitalize())


@app.route("/")
def index():
    tables = [cls.__tablename__ for cls in Base.__subclasses__()]
    links = [f'<li><a href="{url_for("table_view", table_name=t)}">{t.capitalize()}</a></li>' for t in tables]
    return f"<h1>Datenbank Tabellen</h1><ul>{''.join(links)}</ul>"


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route("/table/<table_name>")
def table_view(table_name):
    session = Session()
    cls = next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    if not cls:
        return "Tabelle nicht gefunden", 404

    inspector = inspect(cls)
    columns = [c for c in inspector.columns if not c.primary_key and c.name not in ("created_at", "updated_at")]
    fk_columns = {c.name: list(c.foreign_keys)[0] for c in columns if c.foreign_keys}

    fk_options = {}
    for col_name, fk in fk_columns.items():
        ref_table = fk.column.table.name
        ref_cls = next((c for c in Base.__subclasses__() if c.__tablename__ == ref_table), None)
        if ref_cls:
            display_col = FK_DISPLAY_COLUMNS.get(ref_table, "name")
            fk_options[col_name] = [
                (getattr(r, fk.column.name), f"{getattr(r, display_col, '???')} ({getattr(r, fk.column.name)})")
                for r in session.query(ref_cls).all()
            ]

    rows = session.query(cls).all()

    def get_input(col, value=None, row_id=None):
        input_name = f"{table_name}_{row_id or 'new'}_{col.name}"
        val = "" if value is None else html.escape(str(value))
        if col.name in fk_options:
            opts = "".join(
                f'<option value="{o[0]}" {"selected" if str(o[0])==val else ""}>{escape(o[1])}</option>'
                for o in fk_options[col.name]
            )
            return f'<select name="{input_name}" class="cell-input">{opts}</select>'
        if str(col.type).startswith("INTEGER"):
            return f'<input type="number" name="{input_name}" value="{val}" class="cell-input">'
        if str(col.type).startswith("FLOAT"):
            return f'<input type="number" step="any" name="{input_name}" value="{val}" class="cell-input">'
        if str(col.type).startswith("TEXT") or str(col.type).startswith("VARCHAR"):
            return f'<input type="text" name="{input_name}" value="{val}" class="cell-input">'
        if "DATE" in str(col.type).upper():
            return f'<input type="date" name="{input_name}" value="{val}" class="cell-input">'
        return f'<input type="text" name="{input_name}" value="{val}" class="cell-input">'

    html_out = [f'<h2>{table_name.capitalize()}</h2><a href="/">← zurück</a>']
    html_out.append('<table class="edit-table"><thead><tr>')
    for col in columns:
        label = column_label(table_name, col.name)
        html_out.append(f'<th>{escape(label)}</th>')
    html_out.append('</tr></thead><tbody>')

    for row in rows:
        html_out.append('<tr>')
        for col in columns:
            attr_name = col.name
            if attr_name == "return":
                attr_name = "return_"  # oder wie du es im Model umbenannt hast
            value = getattr(row, attr_name)
            html_out.append(f'<td>{get_input(col, value, row_id=row.id)}</td>')
        html_out.append('</tr>')

    html_out.append('<tr class="new-entry">')
    for col in columns:
        html_out.append(f'<td>{get_input(col)}</td>')
    html_out.append('<td><button class="save-new">Speichern</button></td></tr>')

    html_out.append('</tbody></table>')

    html_out.append("""
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script>
    $(".cell-input").filter(function() {
        return $(this).closest(".new-entry").length === 0;
    }).on("change", function() {
        const name = $(this).attr("name");
        const value = $(this).val();
        $.post("/update/""" + table_name + """", { name, value }, function(resp) {
            if (!resp.success) alert("Fehler: " + resp.error);
        }, "json");
    });
    $(".save-new").on("click", function() {
        const data = {};
        $(".new-entry input, .new-entry select").each(function() {
            data[$(this).attr("name")] = $(this).val();
        });
        $.post("/add/""" + table_name + """", data, function(resp) {
            if (!resp.success) alert("Fehler: " + resp.error);
            else location.reload();
        }, "json");
    });
    </script>
    <style>
    table { border-collapse: collapse; width: 100%; margin-bottom: 2em; }
    th, td { border: 1px solid #ccc; padding: 4px; }
    input, select { width: 100%; }
    .new-entry { background: #eef; }
    </style>
    """)
    return render_template_string("\n".join(html_out))


@app.route("/add/<table_name>", methods=["POST"])
def add_entry(table_name):
    session = Session()
    cls = next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    if not cls:
        return jsonify(success=False, error="Tabelle nicht gefunden")
    try:
        obj = cls()
        for key, val in request.form.items():
            _, _, field = key.partition(f"{table_name}_new_")
            if not hasattr(obj, field):
                continue
            col_type = getattr(cls, field).property.columns[0].type

            if val == "":
                setattr(obj, field, None)
            elif isinstance(col_type, Date):
                setattr(obj, field, datetime.datetime.strptime(val, "%Y-%m-%d").date())
            elif isinstance(col_type, DateTime):
                setattr(obj, field, datetime.datetime.fromisoformat(val))
            elif isinstance(col_type.python_type, type):
                typ = col_type.python_type
                if typ == int:
                    setattr(obj, field, int(val))
                elif typ == float:
                    setattr(obj, field, float(val))
                else:
                    setattr(obj, field, val)
            else:
                setattr(obj, field, val)
        session.add(obj)
        session.commit()
        return jsonify(success=True)
    except Exception as e:
        session.rollback()
        return jsonify(success=False, error=str(e))

@app.route("/update/<table_name>", methods=["POST"])
def update_entry(table_name):
    session = Session()
    cls = next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    if not cls:
        return jsonify(success=False, error="Tabelle nicht gefunden")
    try:
        name = request.form["name"]
        value = request.form["value"]
        _, rowid, field = name.split("_", 2)

        if rowid == "new":
            return jsonify(success=False, error="Kann neue Zeile nicht per Update speichern")

        row = session.query(cls).get(int(rowid))
        if not hasattr(cls, field):
            return jsonify(success=False, error=f"Unbekanntes Feld: {field}")

        col_type = getattr(cls, field).property.columns[0].type

        if value == "":
            setattr(row, field, None)
        elif isinstance(col_type, Date):
            setattr(row, field, datetime.datetime.strptime(value, "%Y-%m-%d").date())
        elif isinstance(col_type, DateTime):
            setattr(row, field, datetime.datetime.fromisoformat(value))
        elif isinstance(col_type.python_type, type):
            typ = col_type.python_type
            if typ == int:
                setattr(row, field, int(value))
            elif typ == float:
                setattr(row, field, float(value))
            else:
                setattr(row, field, value)
        else:
            setattr(row, field, value)

        session.commit()
        return jsonify(success=True)
    except Exception as e:
        session.rollback()
        return jsonify(success=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
