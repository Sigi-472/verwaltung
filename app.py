# app.py
from flask import Flask, render_template, render_template_string, request, jsonify
import verwaltung
import os

from typing import Any

app = Flask(__name__)

@app.route("/")
def index():
    tables = ["person", "abteilung"]
    return render_template("index.html", tables=tables)

@app.route("/table/<string:table>")
def view_table(table: str):
    if table == "person":
        conn = verwaltung._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM person")
        rows = cursor.fetchall()
        columns = rows[0].keys() if rows else ["id", "first_names", "last_name", "created_at", "comment"]
        return render_template("table.html", table=table, columns=columns, rows=rows)

    elif table == "abteilung":
        conn = verwaltung._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM abteilung")
        rows = cursor.fetchall()
        columns = rows[0].keys() if rows else ["id", "name", "abteilungsleiter_id"]
        return render_template("table.html", table=table, columns=columns, rows=rows)

    else:
        return "Tabelle nicht unterstützt", 404

@app.route("/api/data/person", methods=["POST", "PUT", "DELETE"])
def api_person():
    if request.method == "POST":
        data = request.json
        try:
            person_id = verwaltung.insert_person(
                first_names=data.get("first_names", ""),
                last_name=data.get("last_name", ""),
                comment=data.get("comment")
            )
            return jsonify({"status": "inserted", "id": person_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "PUT":
        data = request.json
        try:
            verwaltung.update_person(
                person_id=data["id"],
                first_names=data.get("first_names"),
                last_name=data.get("last_name"),
                comment=data.get("comment")
            )
            return jsonify({"status": "updated"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "DELETE":
        data = request.json
        try:
            verwaltung.delete_person(data["id"])
            return jsonify({"status": "deleted"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/data/abteilung", methods=["POST", "PUT", "DELETE"])
def api_abteilung():
    if request.method == "POST":
        data = request.json
        try:
            abteilungsleiter_id = parse_optional_int(data.get("abteilungsleiter_id"))
            abteilung_id = verwaltung.insert_abteilung(
                name=data.get("name", ""),
                abteilungsleiter_id=abteilungsleiter_id
            )
            return jsonify({"status": "inserted", "id": abteilung_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "PUT":
        data = request.json
        try:
            abteilungsleiter_id = verwaltung.parse_optional_int(data.get("abteilungsleiter_id"))
            verwaltung.update_abteilung(
                abteilung_id=data["id"],
                name=data.get("name"),
                abteilungsleiter_id=abteilungsleiter_id
            )
            return jsonify({"status": "updated"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "DELETE":
        data = request.json
        try:
            verwaltung.delete_abteilung(data["id"])
            return jsonify({"status": "deleted"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/join/person_abteilung", methods=["PUT"])
def api_update_person_abteilung():
    # Definition der Join-View (kann man auch auslagern)
    join_view_person_abteilung = {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_to_abteilung", "alias": "pta", "type": "LEFT", "on": "p.id = pta.person_id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "pta.abteilung_id = a.id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_names",
            "p.last_name",
            "p.created_at",
            "p.comment",
            "a.id AS abteilung_id",
            "a.name AS abteilungsname"
        ],
        "primary_key": "id"
    }

    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine JSON-Daten empfangen"}), 400

    pk_field = join_view_person_abteilung["primary_key"]
    if pk_field not in data:
        return jsonify({"error": f"Primärschlüssel '{pk_field}' fehlt im Request"}), 400

    pk_value = data[pk_field]

    # Für UPDATE brauchen wir die tatsächlichen Tabellen + Spalten, nicht die Aliase
    # Annahme: columns sind als "alias.field AS field" oder "table.field AS field"
    # Wir bauen ein Mapping: alias.field -> (table, field)
    # Für Basis- und Join-Tabellen:

    # Extrahiere Mapping alias -> table
    alias_to_table = {join_view_person_abteilung["base_alias"]: join_view_person_abteilung["base_table"]}
    for join in join_view_person_abteilung["joins"]:
        alias_to_table[join["alias"]] = join["table"]

    # Extrahiere aus columns: Feldname (AS-Name) -> (alias, fieldname)
    import re
    col_field_map = {}
    for col in join_view_person_abteilung["columns"]:
        # z.B. "p.id AS id" oder "a.name AS abteilungsname"
        m = re.match(r"(\w+)\.(\w+)\s+AS\s+(\w+)", col.strip(), re.IGNORECASE)
        if m:
            alias, field, as_name = m.groups()
            col_field_map[as_name] = (alias, field)
        else:
            # Falls kein AS, versuchen direkt (z.B. "p.id")
            m2 = re.match(r"(\w+)\.(\w+)", col.strip())
            if m2:
                alias, field = m2.groups()
                col_field_map[field] = (alias, field)

    # Jetzt bestimmen wir, welche Felder tatsächlich updatefähig sind:
    # id ist primärschlüssel, darf nicht geupdated werden.
    update_fields = []
    for key in data.keys():
        if key == pk_field:
            continue
        if key not in col_field_map:
            # Feld nicht bekannt, ignorieren oder Fehler? Wir ignorieren
            continue
        update_fields.append(key)

    if len(update_fields) == 0:
        return jsonify({"error": "Keine Felder zum Aktualisieren übergeben"}), 400

    # SQLite Verbindungsobjekt
    conn = verwaltung._get_connection()
    try:
        cursor = conn.cursor()

        # Die Herausforderung: Wir müssen Updates auf zwei Tabellen machen:
        # person und person_to_abteilung (und evtl. abteilung - aber name nicht updaten hier)
        # Wir beschränken uns: Felder, die zur base_table gehören, update in base_table
        # Felder, die zur person_to_abteilung gehören, update in person_to_abteilung
        # Fremdschlüssel wie abteilung_id gehören zu person_to_abteilung
        # Wir ignorieren alle Felder aus abteilung (z.B. abteilungsname), da readonly

        # Gruppen update nach Tabelle
        updates_by_table = {}

        for field in update_fields:
            alias, real_field = col_field_map[field]
            table = alias_to_table.get(alias)
            if table not in updates_by_table:
                updates_by_table[table] = {}
            updates_by_table[table][real_field] = data[field]

        # Ausführen der Updates:
        # Basis: primary key ist id in person, also person.id = pk_value
        # Für person_to_abteilung brauchen wir die id der verknüpfung (person_to_abteilung.id)
        # Wir müssen also die person_to_abteilung.id anhand person_id finden (pk_value)

        # Update person-Tabelle
        if join_view_person_abteilung["base_table"] in updates_by_table:
            set_clauses = []
            params = []
            for k, v in updates_by_table[join_view_person_abteilung["base_table"]].items():
                set_clauses.append(f"{k} = ?")
                params.append(v)
            params.append(pk_value)

            sql_update_person = f"UPDATE {join_view_person_abteilung['base_table']} SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql_update_person, params)

        # Update person_to_abteilung-Tabelle
        if "person_to_abteilung" in updates_by_table:
            # Zunächst person_to_abteilung.id anhand person_id holen
            cursor.execute("SELECT id FROM person_to_abteilung WHERE person_id = ?", (pk_value,))
            row = cursor.fetchone()
            if row:
                pta_id = row[0]
                set_clauses = []
                params = []
                for k, v in updates_by_table["person_to_abteilung"].items():
                    set_clauses.append(f"{k} = ?")
                    params.append(v)
                params.append(pta_id)

                sql_update_pta = f"UPDATE person_to_abteilung SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(sql_update_pta, params)
            else:
                # Wenn kein Eintrag existiert, ggf. neuen Insert?
                # Hier für Einfachheit: Fehler zurückgeben
                return jsonify({"error": "Zugehöriger Eintrag in person_to_abteilung nicht gefunden"}), 404

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"DB-Fehler: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/person_abteilung/", methods=["GET"])
def person_abteilung_edit_page():
    join_view_person_abteilung = {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_to_abteilung", "alias": "pta", "type": "LEFT", "on": "p.id = pta.person_id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "pta.abteilung_id = a.id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_names",
            "p.last_name",
            "p.created_at",
            "p.comment",
            "a.id AS abteilung_id",
            "a.name AS abteilungsname"
        ],
        "primary_key": "id"
    }

    conn = verwaltung._get_connection()
    try:
        rows = verwaltung.fetch_join_view(conn, join_view_person_abteilung)
        records = [dict(row) for row in rows]

        # Alle Felder dynamisch aus den Keys des ersten Datensatzes ermitteln
        if len(records) == 0:
            return "<h1>Keine Daten gefunden</h1>", 404
        fields = list(records[0].keys())

        # Dropdown-Optionen für Fremdschlüsselfelder vorbereiten (hier exemplarisch nur abteilung_id)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM abteilung ORDER BY name")
        abteilungen_options = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]

        # Map Feldnamen zu Optionen - hier nur "abteilung_id"
        select_options = {
            "abteilung_id": abteilungen_options
        }

        return render_template(
            "edit_table.html",
            records=records,
            fields=fields,
            primary_key=join_view_person_abteilung["primary_key"],
            select_options=select_options
        )
    except Exception as e:
        return f"<h1>Fehler: {str(e)}</h1>", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
