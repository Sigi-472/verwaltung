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
    from flask import Flask, request, redirect, url_for, render_template_string, jsonify, send_from_directory, render_template, abort
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from db_defs import Base, Person, PersonContact, Building, Room, Transponder, TransponderToRoom
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

COLUMN_LABELS = {
    "abteilung.abteilungsleiter_id": "Abteilungsleiter",
    "person.first_name": "Vorname",
    "person.last_name": "Nachname"
}

FK_DISPLAY_COLUMNS = {
    "person": ["title", "first_name", "last_name"]
}

def column_label(table, col):
    return COLUMN_LABELS.get(f"{table}.{col}", col.replace("_id", "").replace("_", " ").capitalize())

@app.route("/")
def index():
    tables = [cls.__tablename__ for cls in Base.__subclasses__()]
    return render_template("index.html", tables=tables)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

def get_model_class_by_tablename(table_name):
    try:
        return next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    except Exception as e:
        app.logger.error(f"Fehler beim Abrufen der Modelklasse für Tabelle {table_name}: {e}")
        return None

def get_relevant_columns(cls):
    try:
        inspector = inspect(cls)
        return [c for c in inspector.columns if not c.primary_key and c.name not in ("created_at", "updated_at")]
    except Exception as e:
        app.logger.error(f"Fehler beim Inspektieren der Spalten für Klasse {cls}: {e}")
        return []

def get_foreign_key_columns(columns):
    try:
        return {c.name: list(c.foreign_keys)[0] for c in columns if c.foreign_keys}
    except Exception as e:
        app.logger.error(f"Fehler beim Extrahieren der Fremdschlüssel aus Spalten: {e}")
        return {}

def get_fk_options(session, fk_columns):
    fk_options = {}
    try:
        for col_name, fk in fk_columns.items():
            ref_table = fk.column.table.name
            ref_cls = get_model_class_by_tablename(ref_table)
            if ref_cls:
                display_cols = FK_DISPLAY_COLUMNS.get(ref_table, "name")
                records = session.query(ref_cls).all()
                options = []
                for r in records:
                    # key: Wert des FK (z.B. id)
                    key = getattr(r, fk.column.name, None)
                    # label: zusammengesetzter Name
                    if isinstance(display_cols, list):
                        # Alle Spaltenwerte auslesen und verbinden
                        parts = []
                        for col in display_cols:
                            val = getattr(r, col, None)
                            if val is not None:
                                parts.append(str(val))
                        label_text = " ".join(parts) if parts else "???"
                    else:
                        # Nur ein einzelner Spaltenname als String
                        label_text = getattr(r, display_cols, "???")
                    label = f"{label_text} ({key})"
                    options.append((key, label))
                fk_options[col_name] = options
    except Exception as e:
        app.logger.error(f"Fehler beim Abrufen der FK-Optionen: {e}")
    return fk_options

def generate_input_field(col, value=None, row_id=None, fk_options=None, table_name=""):
    try:
        input_name = f"{table_name}_{row_id or 'new'}_{col.name}"
        val = "" if value is None else html.escape(str(value))

        if fk_options and col.name in fk_options:
            options_list = fk_options[col.name]
            if not options_list:
                return "", False
            options_html = ""
            for opt_value, opt_label in options_list:
                selected = "selected" if str(opt_value) == val else ""
                options_html += f'<option value="{html.escape(str(opt_value))}" {selected}>{html.escape(opt_label)}</option>'
            return f'<select name="{html.escape(input_name)}" class="cell-input">{options_html}</select>', True

        col_type_str = str(col.type).upper()
        if "INTEGER" in col_type_str:
            return f'<input type="number" name="{html.escape(input_name)}" value="{val}" class="cell-input">', True
        if "FLOAT" in col_type_str or "DECIMAL" in col_type_str or "NUMERIC" in col_type_str:
            return f'<input type="number" step="any" name="{html.escape(input_name)}" value="{val}" class="cell-input">', True
        if "TEXT" in col_type_str or "VARCHAR" in col_type_str or "CHAR" in col_type_str:
            return f'<input type="text" name="{html.escape(input_name)}" value="{val}" class="cell-input">', True
        if "DATE" in col_type_str:
            return f'<input type="date" name="{html.escape(input_name)}" value="{val}" class="cell-input">', True

        return f'<input type="text" name="{html.escape(input_name)}" value="{val}" class="cell-input">', True
    except Exception as e:
        app.logger.error(f"Fehler beim Generieren des Input-Feldes für Spalte {col.name}: {e}")
        return f'<input type="text" name="{html.escape(input_name)}" value="" class="cell-input">', True

def get_column_label(table_name, column_name):
    # Hier deine Logik für die Label-Erzeugung
    # Einfacher Platzhalter:
    try:
        return column_label(table_name, column_name)
    except Exception as e:
        app.logger.error(f"Fehler beim Abrufen des Labels für {table_name}.{column_name}: {e}")
        return column_name

def prepare_table_data(session, cls, table_name):
    columns = get_relevant_columns(cls)
    fk_columns = get_foreign_key_columns(columns)
    fk_options = get_fk_options(session, fk_columns)

    try:
        rows = session.query(cls).all()
    except Exception as e:
        app.logger.error(f"Fehler bei der Abfrage der Tabelle {table_name}: {e}")
        rows = []

    row_html = []
    row_ids = []
    table_has_missing_inputs = False

    for row in rows:
        row_inputs = []
        try:
            row_id = getattr(row, "id", None)
            if row_id is None:
                first_col_name = columns[0].name if columns else None
                row_id = getattr(row, first_col_name, None) if first_col_name else None
        except Exception as e:
            app.logger.error(f"Fehler beim Zugriff auf ID der Zeile: {e}")
            row_id = None

        row_ids.append(row_id)

        for col in columns:
            col_name = col.name
            if col_name == "return":
                col_name = "return_"

            try:
                value = getattr(row, col_name)
            except AttributeError:
                value = None
            except Exception as e:
                app.logger.error(f"Fehler beim Zugriff auf Spalte {col_name} der Tabelle {table_name}: {e}")
                value = None

            label = get_column_label(table_name, col.name)
            try:
                input_html, valid = generate_input_field(
                    col,
                    value,
                    row_id=row_id,
                    fk_options=fk_options,
                    table_name=table_name
                )
                if not valid:
                    table_has_missing_inputs = True
            except Exception as e:
                app.logger.error(f"Fehler bei der Generierung des Input-Felds für {col.name}: {e}")
                input_html = '<input value="Error">'
                valid = True

            row_inputs.append((input_html, label))
        row_html.append(row_inputs)

    new_entry_inputs = []
    for col in columns:
        try:
            input_html, valid = generate_input_field(
                col,
                fk_options=fk_options,
                table_name=table_name
            )
            if not valid:
                print(col)
                table_has_missing_inputs = True
        except Exception as e:
            app.logger.error(f"Fehler bei der Generierung des neuen Input-Felds für {col.name}: {e}")
            input_html = '<input value="Error">'
        label = get_column_label(table_name, col.name)
        new_entry_inputs.append((input_html, label))

    column_labels = [get_column_label(table_name, col.name) for col in columns]

    return column_labels, row_html, new_entry_inputs, row_ids, table_has_missing_inputs

def load_static_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Datei {path}: {e}")
        return ""

@app.route("/table/<table_name>")
def table_view(table_name):
    session = Session()
    cls = get_model_class_by_tablename(table_name)
    if cls is None:
        abort(404, description="Tabelle nicht gefunden")

    column_labels, row_html, new_entry_inputs, row_ids, table_has_missing_inputs = prepare_table_data(session, cls, table_name)

    style_css = load_static_file("static/table_styles.css")
    javascript_code = load_static_file("static/table_scripts.js").replace("{{ table_name }}", table_name)

    row_data = list(zip(row_html, row_ids))

    missing_data_messages = []
    if table_has_missing_inputs:
        link = url_for("table_view", table_name=table_name)
        missing_data_messages.append(
            f'<div class="warning">⚠️ Fehlende Eingabeoptionen für Tabelle</div>'
        )

    return render_template(
        "table_view.html",
        table_name=table_name,
        column_labels=column_labels,
        row_data=row_data,
        new_entry_inputs=new_entry_inputs,
        style_css=style_css,
        javascript_code=javascript_code,
        missing_data_messages=missing_data_messages
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

@app.route("/delete/<table_name>", methods=["POST"])
def delete_entry(table_name):
    session = Session()
    cls = next((c for c in Base.__subclasses__() if c.__tablename__ == table_name), None)
    if not cls:
        return jsonify(success=False, error="Tabelle nicht gefunden")

    try:
        json_data = request.get_json()
        print("Empfangene JSON-Daten:", json_data)

        if not json_data or "id" not in json_data:
            return jsonify(success=False, error="Keine ID angegeben")

        row_id = json_data["id"]
        if not isinstance(row_id, int):
            try:
                row_id = int(row_id)
            except ValueError:
                return jsonify(success=False, error="Ungültige ID")

        obj = session.query(cls).get(row_id)
        if not obj:
            return jsonify(success=False, error="Datensatz nicht gefunden")

        session.delete(obj)
        session.commit()
        return jsonify(success=True)

    except Exception as e:
        session.rollback()
        return jsonify(success=False, error=str(e))


@app.route("/aggregate/")
def aggregate_index():
    return render_template("aggregate_index.html")  # Optional – nur als Startseite für Aggregates

@app.route("/aggregate/transponder")
def aggregate_transponder_view():
    session = Session()
    show_only_unreturned = request.args.get("unreturned") == "1"

    try:
        query = session.query(Transponder).join(Transponder.owner).outerjoin(Transponder.room_links).outerjoin(TransponderToRoom.room).outerjoin(Room.building)
        if show_only_unreturned:
            query = query.filter(Transponder.return_date.is_(None))

        transponder_list = query.all()

        rows = []
        for t in transponder_list:
            owner = t.owner
            issuer = t.issuer
            rooms = [link.room for link in t.room_links if link.room]
            buildings = list({r.building.name if r.building else "?" for r in rooms})

            row = {
                "ID": t.id,
                "Seriennummer": t.serial_number or "-",
                "Ausgegeben an": f"{owner.first_name} {owner.last_name}" if owner else "Unbekannt",
                "Ausgegeben durch": f"{issuer.first_name} {issuer.last_name}" if issuer else "Unbekannt",
                "Ausgabedatum": t.got_date.isoformat() if t.got_date else "-",
                "Rückgabedatum": t.return_date.isoformat() if t.return_date else "Nicht zurückgegeben",
                "Gebäude": ", ".join(sorted(buildings)) if buildings else "-",
                "Räume": ", ".join(sorted(set(f"{r.name} ({r.floor}.OG)" for r in rooms))) if rooms else "-",
                "Kommentar": t.comment or "-"
            }
            rows.append(row)

        column_labels = list(rows[0].keys()) if rows else []
        row_data = [[html.escape(str(row[col])) for col in column_labels] for row in rows]

        return render_template(
            "aggregate_view.html",
            title="Ausgegebene Transponder",
            column_labels=column_labels,
            row_data=row_data,
            filters={"Nur nicht zurückgegebene anzeigen": show_only_unreturned},
            toggle_url=url_for("aggregate_transponder_view", unreturned="0" if show_only_unreturned else "1")
        )

    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Transponder-Aggregatsansicht: {e}")
        return render_template("error.html", message="Fehler beim Laden der Daten.")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
