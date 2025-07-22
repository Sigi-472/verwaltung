import sys
import re
import platform
import shutil
import os
import subprocess

try:
    import venv
except ModuleNotFoundError:
    print("venv not found. Is python3-venv installed?")
    sys.exit(1)

from pathlib import Path

VENV_PATH = Path.home() / ".verwaltung_venv"
PYTHON_BIN = VENV_PATH / ("Scripts" if platform.system() == "Windows" else "bin") / ("python.exe" if platform.system() == "Windows" else "python")

def create_and_setup_venv():
    print(f"Creating virtualenv at {VENV_PATH}")
    venv.create(VENV_PATH, with_pip=True)
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "flask", "sqlalchemy"])

def restart_with_venv():
    try:
        result = subprocess.run(
            [str(PYTHON_BIN)] + sys.argv,
            text=True,
            check=True,
            env=dict(**os.environ)
        )
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print("Subprocess Error:")
        print(f"Exit-Code: {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Unexpected error while restarting python: {e}")
        sys.exit(1)

try:
    from flask import Flask, request, redirect, url_for, render_template_string, jsonify, send_from_directory, render_template
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from db_defs import Base
    from markupsafe import escape
    import html
    from sqlalchemy import Date, DateTime
    import datetime
except ModuleNotFoundError:
    if not VENV_PATH.exists():
        create_and_setup_venv()
    else:
        try:
            subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "-q", "--upgrade", "flask", "sqlalchemy"])
        except subprocess.CalledProcessError:
            shutil.rmtree(VENV_PATH)
            create_and_setup_venv()
            restart_with_venv()
    try:
        restart_with_venv()
    except KeyboardInterrupt:
        print("You cancelled installation")
        sys.exit(0)

app = Flask(__name__)
engine = create_engine("sqlite:///database.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Deine Konfiguration:
COLUMN_LABELS = {
    "abteilung.abteilungsleiter_id": "Abteilungsleiter",
    "person.first_name": "Vorname",
    "person.last_name": "Nachname"
}

FK_DISPLAY_COLUMNS = {
    "person": "first_name",
    "person": "last_name",
}

def column_label(table, col):
    return COLUMN_LABELS.get(f"{table}.{col}", col.replace("_id", "").replace("_", " ").capitalize())

from flask import render_template

@app.route("/")
def index():
    tables = [cls.__tablename__ for cls in Base.__subclasses__()]
    return render_template("index.html", tables=tables)

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
                f'<option value="{o[0]}" {"selected" if str(o[0])==val else ""}>{html.escape(o[1])}</option>'
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

    # Daten vorbereiten für Template
    column_labels = [column_label(table_name, col.name) for col in columns]
    row_html = []
    for row in rows:
        row_inputs = []
        for col in columns:
            value = getattr(row, col.name if col.name != "return" else "return_")
            label = column_label(table_name, col.name)
            row_inputs.append((get_input(col, value, row_id=row.id), label))
        row_html.append(row_inputs)

    new_entry_inputs = [
        (get_input(col), column_label(table_name, col.name)) for col in columns
    ]

    # CSS und JS separat halten für bessere Übersichtlichkeit
    with open("static/table_styles.css") as f:
        style_css = f.read()
    with open("static/table_scripts.js") as f:
        javascript_code = f.read().replace("{{ table_name }}", table_name)

    return render_template(
        "table_view.html",
        table_name=table_name,
        column_labels=column_labels,
        row_html=row_html,
        new_entry_inputs=new_entry_inputs,
        style_css=style_css,
        javascript_code=javascript_code
    )

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
        name = request.form.get("name")
        value = request.form.get("value")
        prefix = f"{table_name}_"
        if not name.startswith(prefix):
            return jsonify(success=False, error="Ungültiger Feldname")
        parts = name[len(prefix):].split("_", 1)
        if len(parts) != 2:
            return jsonify(success=False, error="Ungültiger Feldname")
        row_id_str, field = parts
        row_id = int(row_id_str)
        obj = session.query(cls).get(row_id)
        if not obj:
            return jsonify(success=False, error="Datensatz nicht gefunden")

        col_type = getattr(cls, field).property.columns[0].type
        if value == "":
            setattr(obj, field, None)
        elif isinstance(col_type, Date):
            setattr(obj, field, datetime.datetime.strptime(value, "%Y-%m-%d").date())
        elif isinstance(col_type, DateTime):
            setattr(obj, field, datetime.datetime.fromisoformat(value))
        else:
            setattr(obj, field, value)
        session.commit()
        return jsonify(success=True)
    except Exception as e:
        session.rollback()
        return jsonify(success=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
