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
    from flask import Flask, request, redirect, url_for, render_template_string, jsonify, send_from_directory
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
    "person": "first_name"
}


def column_label(table, col):
    return COLUMN_LABELS.get(f"{table}.{col}", col.replace("_id", "").replace("_", " ").capitalize())


@app.route("/")
def index():
    tables = [cls.__tablename__ for cls in Base.__subclasses__()]
    links = [f'<li><a href="{url_for("table_view", table_name=t)}">{t.capitalize()}</a></li>' for t in tables]
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Datenbank Tabellen</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 2em;
            background: #f9f9f9;
            color: #333;
        }}
        h1 {{
            margin-bottom: 1em;
        }}
        ul {{
            list-style: none;
            padding-left: 0;
        }}
        li {{
            margin-bottom: 0.5em;
        }}
        a {{
            text-decoration: none;
            color: #007bff;
            font-weight: 600;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Datenbank Tabellen</h1>
    <ul>
        {''.join(links)}
    </ul>
</body>
</html>"""


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

    html_out = [f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>{table_name.capitalize()} - Datenbank Editor</title>

<!-- Toastr CSS -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css">

<style>
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 2em;
        background: #f4f7fa;
        color: #2c3e50;
    }}
    h2 {{
        margin-bottom: 0.5em;
        font-weight: 700;
        color: #34495e;
    }}
    a {{
        text-decoration: none;
        color: #2980b9;
        font-weight: 600;
    }}
    a:hover {{
        text-decoration: underline;
    }}

    table.edit-table {{
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 2em;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        background: white;
        border-radius: 6px;
        overflow: hidden;
    }}
    thead tr {{
        background-color: #2980b9;
        color: white;
        text-align: left;
        font-weight: 600;
        user-select: none;
    }}
    th, td {{
        padding: 10px 15px;
        border-bottom: 1px solid #ddd;
        vertical-align: middle;
    }}
    tbody tr:hover:not(.new-entry) {{
        background-color: #ecf0f1;
    }}
    input.cell-input, select.cell-input {{
        width: 100%;
        padding: 6px 8px;
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        font-size: 0.95rem;
        transition: border-color 0.2s ease-in-out;
    }}
    input.cell-input:focus, select.cell-input:focus {{
        border-color: #2980b9;
        outline: none;
        box-shadow: 0 0 6px #2980b9aa;
    }}

    .new-entry {{
        background-color: #dff0d8;
        font-weight: 600;
    }}
    .new-entry td {{
        padding-top: 14px;
        padding-bottom: 14px;
    }}

    button.save-new {{
        background-color: #27ae60;
        border: none;
        color: white;
        padding: 8px 14px;
        cursor: pointer;
        border-radius: 4px;
        font-weight: 700;
        font-size: 1rem;
        transition: background-color 0.3s ease;
        width: 100%;
    }}
    button.save-new:hover {{
        background-color: #219150;
    }}

    @media (max-width: 768px) {{
        body {{
            margin: 1em;
        }}
        table.edit-table, thead tr, tbody tr, th, td {{
            display: block;
            width: 100%;
        }}
        thead tr {{
            display: none;
        }}
        tbody tr {{
            margin-bottom: 1.5em;
            border-radius: 8px;
            box-shadow: 0 1px 5px rgba(0,0,0,0.1);
            background: white;
            padding: 1em;
        }}
        tbody tr td {{
            border: none;
            padding: 8px 4px;
            position: relative;
            padding-left: 50%;
        }}
        tbody tr td::before {{
            position: absolute;
            top: 8px;
            left: 10px;
            width: 45%;
            white-space: nowrap;
            font-weight: 600;
            color: #7f8c8d;
            content: attr(data-label);
        }}
        button.save-new {{
            width: 100%;
        }}
    }}
</style>
</head>
<body>
<h2>{table_name.capitalize()}</h2>
<a href="/">← zurück</a>
<table class="edit-table">
<thead><tr>"""]

    for col in columns:
        label = column_label(table_name, col.name)
        html_out.append(f'<th>{escape(label)}</th>')
    html_out.append('<th>Aktion</th></tr></thead><tbody>')

    for row in rows:
        html_out.append('<tr>')
        for col in columns:
            attr_name = col.name
            if attr_name == "return":
                attr_name = "return_"  # oder wie du es im Model umbenannt hast
            value = getattr(row, attr_name)
            # Für responsive mobile Labels
            label = column_label(table_name, col.name)
            html_out.append(f'<td data-label="{escape(label)}">{get_input(col, value, row_id=row.id)}</td>')
        html_out.append('<td></td></tr>')

    html_out.append('<tr class="new-entry">')
    for col in columns:
        label = column_label(table_name, col.name)
        html_out.append(f'<td data-label="{escape(label)}">{get_input(col)}</td>')
    html_out.append('<td><button class="save-new" title="Neuen Eintrag speichern">Speichern</button></td></tr>')

    html_out.append('</tbody></table>')

    # Javascript + Toastr + jQuery
    html_out.append("""
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.js"></script>
<script>
toastr.options = {
  "closeButton": true,
  "debug": false,
  "newestOnTop": true,
  "progressBar": true,
  "positionClass": "toast-top-right",
  "preventDuplicates": true,
  "showDuration": "300",
  "hideDuration": "1000",
  "timeOut": "3500",
  "extendedTimeOut": "1000",
  "showEasing": "swing",
  "hideEasing": "linear",
  "showMethod": "fadeIn",
  "hideMethod": "fadeOut"
};

$(".cell-input").filter(function() {
    return $(this).closest(".new-entry").length === 0;
}).on("change", function() {
    const name = $(this).attr("name");
    const value = $(this).val();
    $.post("/update/""" + table_name + """", { name, value }, function(resp) {
        if (!resp.success) {
            toastr.error("Fehler beim Updaten: " + resp.error);
        } else {
            toastr.success("Eintrag geupdatet");
        }
    }, "json").fail(function() {
        toastr.error("Netzwerkfehler beim Updaten");
    });
});
$(".save-new").on("click", function() {
    const data = {};
    $(".new-entry input, .new-entry select").each(function() {
        data[$(this).attr("name")] = $(this).val();
    });
    $.post("/add/""" + table_name + """", data, function(resp) {
        if (!resp.success) {
            toastr.error("Fehler beim Speichern: " + resp.error);
        } else {
            toastr.success("Eintrag gespeichert");
            location.reload();
        }
    }, "json").fail(function() {
        toastr.error("Netzwerkfehler beim Speichern");
    });
});
</script>
</body>
</html>
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
