# app.py
from flask import Flask, render_template, render_template_string, request, jsonify
import verwaltung
import os

join_views = {
    "person_abteilung": {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_to_abteilung", "alias": "pta", "type": "LEFT", "on": "p.id = pta.person_id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "pta.abteilung_id = a.id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "p.created_at",
            "p.comment",
            "a.id AS abteilung_id",
            "a.name AS abteilungsname"
        ],
        "primary_key": "id"
    },
    # Weitere Views hier definieren:
    # "andere_view": { ... }
}


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
        columns = rows[0].keys() if rows else ["id", "first_name", "last_name", "created_at", "comment"]
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
                first_name=data.get("first_name", ""),
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
                first_name=data.get("first_name"),
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

@app.route("/<view_name>/", methods=["GET"])
def generic_join_edit_page(view_name):
    view_def = join_views.get(view_name)
    if not view_def:
        return f"<h1>View '{view_name}' nicht definiert</h1>", 404

    conn = verwaltung._get_connection()
    try:
        rows = verwaltung.fetch_join_view(conn, view_def)
        records = [dict(row) for row in rows]

        if not records:
            return "<h1>Keine Daten gefunden</h1>", 404

        fields = list(records[0].keys())

        # Beispiel: Automatische Dropdowns für *_id-Felder
        select_options = {}
        cursor = conn.cursor()
        for field in fields:
            if field.endswith("_id") and field in verwaltung.extract_column_field_mapping(view_def):
                alias, _ = verwaltung.extract_column_field_mapping(view_def)[field]
                table = verwaltung.extract_alias_table_mapping(view_def).get(alias)
                if table:
                    try:
                        cursor.execute(f"SELECT id, name FROM {table} ORDER BY name")
                        rows = cursor.fetchall()
                        select_options[field] = [{"id": r["id"], "name": r["name"]} for r in rows]
                    except Exception:
                        continue  # z.B. wenn "name" nicht existiert

        return render_template(
            "edit_table.html",
            records=records,
            fields=fields,
            primary_key=view_def["primary_key"],
            select_options=select_options
        )
    except Exception as e:
        return f"<h1>Fehler: {str(e)}</h1>", 500
    finally:
        conn.close()

@app.route("/api/join/<view_name>", methods=["PUT"])
def api_update_generic_view(view_name):
    view_def = join_views.get(view_name)
    if not view_def:
        return jsonify({"error": f"View '{view_name}' nicht definiert"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine JSON-Daten empfangen"}), 400

    pk_field = view_def["primary_key"]
    if pk_field not in data:
        return jsonify({"error": f"Primärschlüssel '{pk_field}' fehlt"}), 400

    pk_value = data[pk_field]
    alias_to_table = extract_alias_table_mapping(view_def)
    col_field_map = extract_column_field_mapping(view_def)

    update_fields = [
        k for k in data if k != pk_field and k in col_field_map
    ]

    if not update_fields:
        return jsonify({"error": "Keine gültigen Felder zum Aktualisieren"}), 400

    updates_by_table = {}
    for field in update_fields:
        alias, real_field = col_field_map[field]
        table = alias_to_table.get(alias)
        if not table:
            continue
        updates_by_table.setdefault(table, {})[real_field] = data[field]

    conn = verwaltung._get_connection()
    try:
        cursor = conn.cursor()

        # Update der Base-Tabelle
        base_table = view_def["base_table"]
        if base_table in updates_by_table:
            set_clauses = []
            params = []
            for k, v in updates_by_table[base_table].items():
                set_clauses.append(f"{k} = ?")
                params.append(v)
            params.append(pk_value)
            sql = f"UPDATE {base_table} SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)

        # Update verbundene Tabellen
        for join in view_def.get("joins", []):
            join_table = join["table"]
            if join_table not in updates_by_table:
                continue
            # Sonderfall: Fremdschlüssel über person_id
            cursor.execute(f"SELECT id FROM {join_table} WHERE person_id = ?", (pk_value,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": f"Eintrag in {join_table} nicht gefunden"}), 404
            join_id = row["id"]
            set_clauses = []
            params = []
            for k, v in updates_by_table[join_table].items():
                set_clauses.append(f"{k} = ?")
                params.append(v)
            params.append(join_id)
            sql = f"UPDATE {join_table} SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"DB-Fehler: {str(e)}"}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
