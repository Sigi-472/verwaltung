import sys
import re
import platform
import shutil
import os
import subprocess
import random
from pprint import pprint

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
    subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "--upgrade", "flask", "sqlalchemy", "pypdf", "cryptography"])

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
    from flask import Flask, request, redirect, url_for, render_template_string, jsonify, send_from_directory, render_template, abort, send_file
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker, joinedload, Session
    from sqlalchemy.exc import SQLAlchemyError
    from db_defs import Base, Person, PersonContact, Building, Room, Transponder, TransponderToRoom, Inventory, Object
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    import io
    from markupsafe import escape
    import html
    from sqlalchemy import Date, DateTime
    import cryptography
    import datetime
except ModuleNotFoundError:
    if not VENV_PATH.exists():
        create_and_setup_venv()
    else:
        try:
            subprocess.check_call([PYTHON_BIN, "-m", "pip", "install", "-q", "--upgrade", "flask", "sqlalchemy", "pypdf", "cryptography"])
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

WIZARDS = {}

WIZARDS["transponder"] = {
    "title": "Transponder erstellen",
    "model": Transponder,
    "fields": [
        {"name": "issuer_id", "type": "number", "label": "Ausgeber-ID", "required": True},
        {"name": "owner_id", "type": "number", "label": "Besitzer-ID"},
        {"name": "serial_number", "type": "text", "label": "Seriennummer"},
        {"name": "got_date", "type": "date", "label": "Ausgabedatum"},
    ],
    "subforms": [
        {
            "name": "room_links",
            "label": "Zugeordnete Räume",
            "model": TransponderToRoom,
            "foreign_key": "transponder_id",
            "fields": [
                {"name": "room_id", "type": "number", "label": "Raum-ID"},
            ]
        }
    ]
}

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def is_valid_email(email):
    return bool(EMAIL_REGEX.match(email.strip()))

def column_label(table, col):
    return COLUMN_LABELS.get(f"{table}.{col}", col.replace("_id", "").replace("_", " ").capitalize())

@app.route("/")
def index():
    tables = [cls.__tablename__ for cls in Base.__subclasses__()]

    wizard_routes = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/wizard") and rule.rule != "/wizard":
            wizard_routes.append(rule.rule)
    wizard_routes = sorted(wizard_routes)

    return render_template("index.html", tables=tables, wizard_routes=wizard_routes)

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

    # Filter aus Query-Params
    show_only_unreturned = request.args.get("unreturned") == "1"
    owner_filter = request.args.get("owner", "").strip()
    issuer_filter = request.args.get("issuer", "").strip()

    try:
        query = session.query(Transponder) \
            .options(
                joinedload(Transponder.owner),
                joinedload(Transponder.issuer),
                joinedload(Transponder.room_links).joinedload(TransponderToRoom.room).joinedload(Room.building)
            )

        # Filter nur nicht zurückgegebene
        if show_only_unreturned:
            query = query.filter(Transponder.return_date.is_(None))

        # Filter für owner (besitzer)
        if owner_filter:
            # Hier gehen wir davon aus, dass owner_filter eine Teilstring-Suche auf Vor- oder Nachname erlaubt
            query = query.join(Transponder.owner).filter(
                (Transponder.owner.first_name.ilike(f"%{owner_filter}%")) |
                (Transponder.owner.last_name.ilike(f"%{owner_filter}%"))
            )

        # Filter für issuer (ausgeber)
        if issuer_filter:
            query = query.join(Transponder.issuer).filter(
                (Transponder.issuer.first_name.ilike(f"%{issuer_filter}%")) |
                (Transponder.issuer.last_name.ilike(f"%{issuer_filter}%"))
            )

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

        # Filter-Dict zum dynamischen Befüllen des Formulars und Anzeige des Status
        filters = {
            "Nur nicht zurückgegebene anzeigen": show_only_unreturned,
            "Besitzer (Ausgegeben an)": owner_filter,
            "Ausgeber (Ausgegeben durch)": issuer_filter
        }

        return render_template(
            "aggregate_view.html",
            title="Ausgegebene Transponder",
            column_labels=column_labels,
            row_data=row_data,
            filters=filters,
            # toggle_url nicht mehr hart codiert, hier auf Basis aktueller Filter mit geändertem "unreturned"
            toggle_url=url_for(
                "aggregate_transponder_view",
                unreturned="0" if show_only_unreturned else "1",
                owner=owner_filter,
                issuer=issuer_filter
            )
        )

    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Transponder-Aggregatsansicht: {e}")
        return render_template("error.html", message="Fehler beim Laden der Daten.")

@app.route("/aggregate/inventory")
def aggregate_inventory_view():
    session = None
    try:
        session = Session()

        # Query-Parameter auslesen
        show_only_unreturned = request.args.get("unreturned") == "1"
        owner_filter = request.args.get("owner", type=int)
        issuer_filter = request.args.get("issuer", type=int)

        # Grundquery mit Joins
        query = session.query(Inventory) \
            .options(
                joinedload(Inventory.owner),
                joinedload(Inventory.issuer),
                joinedload(Inventory.object).joinedload(Object.category),
                joinedload(Inventory.kostenstelle),
                joinedload(Inventory.abteilung),
                joinedload(Inventory.professorship),
                joinedload(Inventory.room)
            )

        # Filter anwenden
        if show_only_unreturned:
            query = query.filter(Inventory.return_date.is_(None))

        if owner_filter:
            query = query.filter(Inventory.owner_id == owner_filter)

        if issuer_filter:
            query = query.filter(Inventory.issuer_id == issuer_filter)

        inventory_list = query.all()

        # Hilfsfunktionen
        def person_name(p):
            if p:
                return f"{p.first_name} {p.last_name}"
            return "Unbekannt"

        def category_name(c):
            return c.name if c else "-"

        def kostenstelle_name(k):
            return k.name if k else "-"

        def abteilung_name(a):
            return a.name if a else "-"

        def professorship_name(pf):
            return pf.name if pf else "-"

        def room_name(r):
            if r:
                floor_str = f"{r.floor}.OG" if r.floor is not None else "?"
                return f"{r.name} ({floor_str})"
            return "-"

        rows = []
        for inv in inventory_list:
            row = {
                "ID": inv.id,
                "Seriennummer": inv.serial_number or "-",
                "Objekt": inv.object.name if inv.object else "-",
                "Kategorie": category_name(inv.object.category) if inv.object else "-",
                "Anlagennummer": inv.anlagennummer or "-",
                "Ausgegeben an": person_name(inv.owner),
                "Ausgegeben durch": person_name(inv.issuer),
                "Ausgabedatum": inv.got_date.isoformat() if inv.got_date else "-",
                "Rückgabedatum": inv.return_date.isoformat() if inv.return_date else "Nicht zurückgegeben",
                "Raum": room_name(inv.room),
                "Abteilung": abteilung_name(inv.abteilung),
                "Professur": professorship_name(inv.professorship),
                "Kostenstelle": kostenstelle_name(inv.kostenstelle),
                "Preis": f"{inv.price:.2f} €" if inv.price is not None else "-",
                "Kommentar": inv.comment or "-"
            }
            rows.append(row)

        # Für Filter: Alle User (Owner und Issuer) holen (vereinfachend hier alle Personen)
        # Du kannst ggf. nur Owner oder Issuer spezifisch holen, falls nötig
        people_query = session.query(Person).order_by(Person.last_name, Person.first_name).all()
        people = [{"id": p.id, "name": f"{p.first_name} {p.last_name}"} for p in people_query]

        column_labels = list(rows[0].keys()) if rows else []
        row_data = [[escape(str(row[col])) for col in column_labels] for row in rows]

        return render_template(
            "aggregate_view.html",
            title="Inventarübersicht",
            column_labels=column_labels,
            row_data=row_data,
            filters={
                "unreturned": show_only_unreturned,
                "owner": owner_filter,
                "issuer": issuer_filter,
            },
            people=people,
            url_for_view=url_for("aggregate_inventory_view")
        )
    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Inventar-Aggregatsansicht: {e}")
        return render_template("error.html", message="Fehler beim Laden der Daten.")
    finally:
        if session:
            session.close()


@app.route("/wizard")
def wizard_index():
    wizard_routes = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/wizard") and rule.rule != "/wizard":
            wizard_routes.append(rule.rule)
    wizard_routes = sorted(wizard_routes)
    return render_template("wizard_index.html", wizard_routes=wizard_routes)

@app.route("/wizard/person", methods=["GET", "POST"])
def wizard_person():
    session = Session()
    error = None
    success = False

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip() or None
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            comment = request.form.get("comment", "").strip() or None
            image_url = request.form.get("image_url", "").strip() or None

            if not first_name or not last_name:
                raise ValueError("Vorname und Nachname sind Pflichtfelder.")

            emails = request.form.getlist("email[]")
            phones = request.form.getlist("phone[]")
            faxes = request.form.getlist("fax[]")
            comments = request.form.getlist("contact_comment[]")

            valid_emails = [e.strip() for e in emails if e.strip() != ""]
            if len(valid_emails) == 0:
                raise ValueError("Mindestens eine Email muss eingegeben werden.")

            for email in valid_emails:
                if not is_valid_email(email):
                    raise ValueError(f"Ungültige Email-Adresse: {email}")

            new_person = Person(
                title=title,
                first_name=first_name,
                last_name=last_name,
                comment=comment,
                image_url=image_url
            )
            session.add(new_person)
            session.flush()

            max_len = max(len(emails), len(phones), len(faxes), len(comments))
            for i in range(max_len):
                email_val = emails[i].strip() if i < len(emails) else None
                phone_val = phones[i].strip() if i < len(phones) else None
                fax_val = faxes[i].strip() if i < len(faxes) else None
                comment_val = comments[i].strip() if i < len(comments) else None

                if any([email_val, phone_val, fax_val, comment_val]):
                    if email_val and not is_valid_email(email_val):
                        raise ValueError(f"Ungültige Email-Adresse in Kontakt: {email_val}")

                    contact = PersonContact(
                        person_id=new_person.id,
                        email=email_val,
                        phone=phone_val,
                        fax=fax_val,
                        comment=comment_val
                    )
                    session.add(contact)

            session.commit()
            success = True

        except Exception as e:
            session.rollback()
            error = str(e) + "\n" + traceback.format_exc()

        finally:
            session.close()

    return render_template("person_wizard.html", success=success, error=error)

@app.route("/map-editor")
def map_editor():
    return render_template("map_editor.html")

from copy import deepcopy

@app.route("/wizard/transponder", methods=["GET", "POST"])
def run_wizard():
    return _wizard_internal("transponder")

def _wizard_internal(name):
    config = WIZARDS.get(name)
    if not config:
        abort(404)

    # JSON-sichere Version ohne nicht-serialisierbare Objekte
    def get_json_safe_config(config):
        safe = deepcopy(config)
        for sub in safe.get("subforms", []):
            sub.pop("model", None)
            sub.pop("foreign_key", None)
        safe.pop("model", None)
        return safe

    session = Session()
    success = False
    error = None

    if request.method == "POST":
        try:
            main_model = config["model"]
            main_data = {
                f["name"]: request.form.get(f["name"], "").strip() or None
                for f in config["fields"]
            }

            if any(f.get("required") and not main_data[f["name"]] for f in config["fields"]):
                raise ValueError("Pflichtfelder fehlen.")

            main_instance = main_model(**main_data)
            session.add(main_instance)
            session.flush()

            for sub in config.get("subforms", []):
                model = sub["model"]
                foreign_key = sub["foreign_key"]
                field_names = [f["name"] for f in sub["fields"]]
                data_lists = {f: request.form.getlist(f + "[]") for f in field_names}

                for i in range(max(len(l) for l in data_lists.values())):
                    entry = {
                        f: data_lists[f][i].strip() if i < len(data_lists[f]) else None
                        for f in field_names
                    }
                    if any(entry.values()):
                        entry[foreign_key] = main_instance.id
                        session.add(model(**entry))

            session.commit()
            success = True

        except Exception as e:
            session.rollback()
            error = str(e)
        finally:
            session.close()

    return render_template("wizard.html", config=config, config_json=get_json_safe_config(config), success=success, error=error)

# Platzhalterdaten erzeugen
def generate_field_data():
    data = {}

    FIELD_NAMES = [
        'Text1', 'Text3', 'Text4', 'Text5', 'Text7', 'Text8',
        'GebäudeRow1', 'RaumRow1', 'SerienNrSchlüsselNrRow1', 'AnzahlRow1',
        'GebäudeRow2', 'RaumRow2', 'SerienNrSchlüsselNrRow2', 'AnzahlRow2',
        'GebäudeRow3', 'RaumRow3', 'SerienNrSchlüsselNrRow3', 'AnzahlRow3',
        'GebäudeRow4', 'RaumRow4', 'SerienNrSchlüsselNrRow4', 'AnzahlRow4',
        'GebäudeRow5', 'RaumRow5', 'SerienNrSchlüsselNrRow5', 'AnzahlRow5',
        'Datum Übergebende:r', 'Datum Übernehmende:r', 'Weitere Anmerkungen'
    ]

    for name in FIELD_NAMES:
        if "Datum" in name:
            data[name] = datetime.date.today().strftime("%d.%m.%Y")
        elif "Anzahl" in name:
            data[name] = str(random.randint(1, 5))
        elif "SerienNr" in name or "SchlüsselNr" in name:
            data[name] = f"SN-{random.randint(1000,9999)}"
        elif "Raum" in name:
            data[name] = f"R{random.randint(100,499)}"
        elif "Gebäude" in name:
            data[name] = f"G{random.randint(1,9)}"
        elif "Text" in name:
            data[name] = f"Text-{random.randint(100,999)}"
        elif "Weitere Anmerkungen" in name:
            data[name] = "Dies ist ein automatisierter Testeintrag."
        else:
            data[name] = f"Wert-{random.randint(100,999)}"
    return data

def get_transponder_metadata(transponder_id: int) -> dict:
    session = Session()

    try:
        transponder = session.query(Transponder).filter(Transponder.id == transponder_id).one_or_none()

        if transponder is None:
            return None

        metadata = {
            "id": transponder.id,
            "serial_number": transponder.serial_number,
            "got_date": transponder.got_date,
            "return_date": transponder.return_date,
            "comment": transponder.comment,

            "issuer": None,
            "owner": None,
            "rooms": []
        }

        if transponder.issuer is not None:
            metadata["issuer"] = {
                "id": transponder.issuer.id,
                "first_name": transponder.issuer.first_name,
                "last_name": transponder.issuer.last_name,
                "title": transponder.issuer.title
            }

        if transponder.owner is not None:
            metadata["owner"] = {
                "id": transponder.owner.id,
                "first_name": transponder.owner.first_name,
                "last_name": transponder.owner.last_name,
                "title": transponder.owner.title
            }

        for link in transponder.room_links:
            room = link.room

            room_data = {
                "id": room.id,
                "name": room.name,
                "floor": room.floor,
                "building": None
            }

            if room.building is not None:
                room_data["building"] = {
                    "id": room.building.id,
                    "name": room.building.name,
                    "building_number": room.building.building_number,
                    "address": room.building.address
                }

            metadata["rooms"].append(room_data)

        return metadata

    except SQLAlchemyError as e:
        return {"error": str(e)}

def get_person_metadata(person_id: int) -> dict:
    session = Session()

    try:
        person = session.query(Person).filter(Person.id == person_id).one_or_none()

        if person is None:
            return {"error": f"No person found with id {person_id}"}

        metadata = {
            "id": person.id,
            "title": person.title,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "created_at": person.created_at,
            "comment": person.comment,
            "image_url": person.image_url,

            "contacts": [],
            "rooms": [],
            "transponders_issued": [],
            "transponders_owned": [],
            "departments": [],
            "person_abteilungen": [],
            "professorships": []
        }

        for contact in person.contacts:
            metadata["contacts"].append({
                "id": contact.id,
                "phone": contact.phone,
                "fax": contact.fax,
                "email": contact.email,
                "comment": contact.comment
            })

        for room in person.rooms:
            metadata["rooms"].append({
                "id": room.id,
                "room_id": getattr(room, "room_id", None),  # adapt if necessary
                "comment": getattr(room, "comment", None)
            })

        for transponder in person.transponders_issued:
            metadata["transponders_issued"].append({
                "id": transponder.id,
                "number": getattr(transponder, "number", None),
                "owner_id": transponder.owner_id
            })

        for transponder in person.transponders_owned:
            metadata["transponders_owned"].append({
                "id": transponder.id,
                "number": getattr(transponder, "number", None),
                "issuer_id": transponder.issuer_id
            })

        for dept in person.departments:
            metadata["departments"].append({
                "id": dept.id,
                "name": getattr(dept, "name", None)
            })

        for pa in person.person_abteilungen:
            metadata["person_abteilungen"].append({
                "id": pa.id,
                "abteilung_id": getattr(pa, "abteilung_id", None),
                "funktion": getattr(pa, "funktion", None)
            })

        for prof in person.professorships:
            metadata["professorships"].append({
                "id": prof.id,
                "professorship_id": getattr(prof, "professorship_id", None),
                "title": getattr(prof, "title", None)
            })

        return metadata

    except SQLAlchemyError as e:
        return {"error": str(e)}

def fill_pdf_form(template_path, data_dict):
    reader = PdfReader(template_path)
    writer = PdfWriter()

    # Alle Seiten übernehmen
    writer.append_pages_from_reader(reader)

    # 🛠️ AcroForm vom Original-PDF übernehmen
    if "/AcroForm" in reader.trailer["/Root"]:
        writer._root_object.update({
            NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
        })

    # Feldwerte vorbereiten
    fields = reader.get_fields()
    filled_fields = {}

    for field_name in data_dict:
        if field_name in fields:
            filled_fields[field_name] = data_dict[field_name]

    # 📝 Formularfelder auf erster Seite aktualisieren
    writer.update_page_form_field_values(writer.pages[0], filled_fields)

    # Ergebnis zurückgeben
    output_io = io.BytesIO()
    writer.write(output_io)
    output_io.seek(0)
    return output_io

@app.route('/generate_pdf/schliessmedien/')
def generate_pdf():
    TEMPLATE_PATH = 'pdfs/ausgabe_schliessmedien.pdf'

    issuer_id = request.args.get('issuer_id')
    owner_id = request.args.get('owner_id')
    transponder_id = request.args.get('transponder_id')

    missing = []
    if not issuer_id:
        missing.append("issuer_id (Ausgeber-ID)")
    if not owner_id:
        missing.append("owner_id (Besitzer-ID)")
    if not transponder_id:
        missing.append("transponder_id")

    if missing:
        return render_template_string(
            "<h1>Fehlende Parameter</h1><ul>{% for m in missing %}<li>{{ m }}</li>{% endfor %}</ul>",
            missing=missing
        ), 400

    issuer = get_person_metadata(issuer_id)
    owner = get_person_metadata(owner_id)
    transponder = get_transponder_metadata(transponder_id)

    not_found = []
    if issuer is None:
        not_found.append(f"Keine Person mit issuer_id: {issuer_id}")
    if owner is None:
        not_found.append(f"Keine Person mit owner_id: {owner_id}")
    if transponder is None:
        not_found.append(f"Kein Transponder mit transponder_id: {transponder_id}")

    if not_found:
        return render_template_string(
            "<h1>Nicht Gefunden</h1><ul>{% for msg in not_found %}<li>{{ msg }}</li>{% endfor %}</ul>",
            not_found=not_found
        ), 404

    print(transponder)
    field_data = generate_field_data()  # ggf. Argumente übergeben, je nach Bedarf

    filled_pdf = fill_pdf_form(TEMPLATE_PATH, field_data)
    if filled_pdf is None:
        return render_template_string("<h1>Fehler</h1><p>Das PDF-Formular konnte nicht generiert werden.</p>"), 500

    return send_file(
        filled_pdf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='ausgabe_schliessmedien_filled.pdf'
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
