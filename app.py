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

def get_model_class_by_tablename(table_name, base):
    """
    Gibt die ORM-Klasse zurück, deren __tablename__ mit table_name übereinstimmt.
    """
    try:
        cls = next((c for c in base.__subclasses__() if c.__tablename__ == table_name), None)
        return cls
    except Exception as e:
        return None

def get_relevant_columns(cls):
    """
    Liefert alle Spalten, die keine Primärschlüssel sind und nicht 'created_at' oder 'updated_at' heißen.
    """
    try:
        inspector = inspect(cls)
        columns = [c for c in inspector.columns if not c.primary_key and c.name not in ("created_at", "updated_at")]
        return columns
    except Exception as e:
        return []

def get_foreign_key_columns(columns):
    """
    Extrahiert alle Spalten mit Foreign Keys als Dict: {Spaltenname: ForeignKey}
    """
    fk_columns = {}
    try:
        for c in columns:
            if c.foreign_keys:
                fk_columns[c.name] = list(c.foreign_keys)[0]
    except Exception as e:
        pass
    return fk_columns

def build_fk_options(fk_columns, base, session, fk_display_columns):
    """
    Baut ein Dict für Foreign-Key-Spalten, das für jede FK-Spalte die Optionen mit Anzeige-Labels liefert.
    Format: {fk_spaltenname: [(wert, "Anzeige (wert)"), ...]}
    """
    fk_options = {}
    try:
        for col_name, fk in fk_columns.items():
            ref_table = fk.column.table.name
            ref_cls = get_model_class_by_tablename(ref_table, base)
            if not ref_cls:
                continue
            display_col = fk_display_columns.get(ref_table, "name")
            options = []
            try:
                results = session.query(ref_cls).all()
                for r in results:
                    key = getattr(r, fk.column.name)
                    display_value = getattr(r, display_col, '???')
                    options.append((key, f"{display_value} ({key})"))
                fk_options[col_name] = options
            except Exception as e:
                continue
    except Exception as e:
        pass
    return fk_options

def generate_input_html(table_name, col, value, row_id, fk_options):
    """
    Generiert das HTML-Formularelement (input/autocomplete/select) für eine einzelne Zelle.
    Wenn FK: jQuery UI Autocomplete.
    """
    try:
        input_name = f"{table_name}_{row_id or 'new'}_{col.name}"
        col_type_str = str(col.type).upper()

        if col.name in fk_options:
            # Autocomplete für Foreign Key Spalten
            datalist = [
                {
                    "label": o[1],
                    "value": str(o[0])
                }
                for o in fk_options[col.name]
            ]

            # Aktuelles Label zum Wert finden (für visible input value)
            display_val = ""
            if value is not None:
                for opt_value, opt_label in fk_options[col.name]:
                    if str(opt_value) == str(value):
                        display_val = opt_label
                        break

            data_json = html.escape(str(datalist).replace("'", '"'))

            html_input = (
                f'<input type="text" '
                f'name="{html.escape(input_name)}" '
                f'value="{html.escape(display_val)}" '
                f'class="cell-input autocomplete-{html.escape(str(col.name))}" '
                f'data-id="{html.escape(str(value)) if value is not None else ""}" '
                f'data-autocomplete=\'{html.escape(data_json)}\'>\n'
            )


            return html_input

        # Standard-Typen
        val = "" if value is None else html.escape(str(value))
        if "INTEGER" in col_type_str:
            return f'<input type="number" name="{input_name}" value="{val}" class="cell-input">'
        if "FLOAT" in col_type_str or "NUMERIC" in col_type_str or "DECIMAL" in col_type_str:
            return f'<input type="number" step="any" name="{input_name}" value="{val}" class="cell-input">'
        if "TEXT" in col_type_str or "VARCHAR" in col_type_str or "CHAR" in col_type_str:
            return f'<input type="text" name="{input_name}" value="{val}" class="cell-input">'
        if "DATE" in col_type_str:
            return f'<input type="date" name="{input_name}" value="{val}" class="cell-input">'

        return f'<input type="text" name="{input_name}" value="{val}" class="cell-input">'

    except Exception as e:
        return f'<input type="text" name="{table_name}_{row_id or "new"}_{col.name}" value="" class="cell-input">'

def build_rows_html(rows, columns, table_name, fk_options):
    """
    Baut für jede Zeile und Spalte das passende Input-HTML zusammen.
    Gibt eine Liste von Listen zurück: [[(input_html, label), ...], ...]
    """
    row_html = []
    try:
        for row in rows:
            row_inputs = []
            for col in columns:
                try:
                    # Fall für Spalte 'return' auf 'return_' umleiten
                    attr_name = col.name if col.name != "return" else "return_"
                    value = getattr(row, attr_name, None)
                    label = column_label(table_name, col.name)
                    input_html = generate_input_html(table_name, col, value, row_id=row.id, fk_options=fk_options)
                    row_inputs.append((input_html, label))
                except Exception as e:
                    row_inputs.append(("", column_label(table_name, col.name)))
            row_html.append(row_inputs)
    except Exception as e:
        pass
    return row_html

def build_new_entry_inputs(columns, table_name, fk_options):
    """
    Baut die Inputs für eine neue Eintragszeile (leer).
    """
    new_entry_inputs = []
    try:
        for col in columns:
            input_html = generate_input_html(table_name, col, None, None, fk_options)
            label = column_label(table_name, col.name)
            new_entry_inputs.append((input_html, label))
    except Exception as e:
        pass
    return new_entry_inputs

def load_static_file(path):
    """
    Hilfsfunktion zum Einlesen einer statischen Datei, mit Fehlerbehandlung.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return ""

@app.route("/table/<table_name>")
def table_view(table_name):
    session = Session()

    cls = get_model_class_by_tablename(table_name, Base)
    if not cls:
        return "Tabelle nicht gefunden", 404

    columns = get_relevant_columns(cls)
    fk_columns = get_foreign_key_columns(columns)
    fk_options = build_fk_options(fk_columns, Base, session, FK_DISPLAY_COLUMNS)

    rows = session.query(cls).all()

    column_labels = [column_label(table_name, col.name) for col in columns]
    row_html = build_rows_html(rows, columns, table_name, fk_options)
    new_entry_inputs = build_new_entry_inputs(columns, table_name, fk_options)

    style_css = load_static_file("static/table_styles.css")
    javascript_code = load_static_file("static/table_scripts.js").replace("{{ table_name }}", table_name)

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

        for key, value in request.form.items():
            print(f"{key}: {value}")

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

@app.route("/delete/<table_name>", methods=["POST"])
def delete_entry(table_name):
    session = Session()
    cls = next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    if not cls:
        return jsonify(success=False, error="Tabelle nicht gefunden")
    try:
        name = request.form.get("name")
        prefix = f"{table_name}_"
        if not name.startswith(prefix):
            return jsonify(success=False, error="Ungültiger Feldname")

        parts = name[len(prefix):].split("_", 1)
        if len(parts) != 2:
            return jsonify(success=False, error="Ungültiger Feldname")

        row_id_str, _ = parts
        row_id = int(row_id_str)
        obj = session.query(cls).get(row_id)
        if not obj:
            return jsonify(success=False, error="Datensatz nicht gefunden")

        session.delete(obj)
        session.commit()
        return jsonify(success=True)
    except Exception as e:
        session.rollback()
        return jsonify(success=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
