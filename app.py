# app.py
from flask import Flask, render_template, render_template_string, request, jsonify
from typing import Any
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
    "person_contact": {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_contact", "alias": "pc", "type": "LEFT", "on": "p.id = pc.person_id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "pc.phone",
            "pc.fax",
            "pc.email",
            "pc.comment AS contact_comment"
        ],
        "primary_key": "id"
    },
    "person_room": {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_to_room", "alias": "ptr", "type": "LEFT", "on": "p.id = ptr.person_id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "ptr.room_id = r.id"},
            {"table": "building", "alias": "b", "type": "LEFT", "on": "r.building_id = b.id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "r.name AS room_name",
            "r.floor AS room_floor",
            "b.name AS building_name",
            "b.building_number",
            "b.address"
        ],
        "primary_key": "id"
    },
    "person_professorship": {
        "base_table": "person",
        "base_alias": "p",
        "joins": [
            {"table": "person_to_professorship", "alias": "ptp", "type": "LEFT", "on": "p.id = ptp.person_id"},
            {"table": "professorship", "alias": "pr", "type": "LEFT", "on": "ptp.professorship_id = pr.id"},
            {"table": "kostenstelle", "alias": "k", "type": "LEFT", "on": "pr.kostenstelle_id = k.id"}
        ],
        "columns": [
            "p.id AS id",
            "p.first_name",
            "p.last_name",
            "pr.id AS professorship_id",
            "pr.name AS professorship_name",
            "k.id AS kostenstelle_id",
            "k.name AS kostenstelle_name"
        ],
        "primary_key": "id"
    },
    "transponder_with_owner_and_rooms": {
        "base_table": "transponder",
        "base_alias": "t",
        "joins": [
            {"table": "person", "alias": "issuer", "type": "LEFT", "on": "t.issuer_id = issuer.id"},
            {"table": "person", "alias": "owner", "type": "LEFT", "on": "t.owner_id = owner.id"},
            {"table": "transponder_to_room", "alias": "ttr", "type": "LEFT", "on": "t.id = ttr.transponder_id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "ttr.room_id = r.id"}
        ],
        "columns": [
            "t.id AS transponder_id",
            "t.serial_number",
            "t.got",
            "t.return",
            "t.comment",
            "issuer.first_name AS issuer_first_name",
            "issuer.last_name AS issuer_last_name",
            "owner.first_name AS owner_first_name",
            "owner.last_name AS owner_last_name",
            "r.name AS room_name",
            "r.floor AS room_floor"
        ],
        "primary_key": "transponder_id"
    },
    "inventory_detailed": {
        "base_table": "inventory",
        "base_alias": "i",
        "joins": [
            {"table": "person", "alias": "owner", "type": "LEFT", "on": "i.owner_id = owner.id"},
            {"table": "person", "alias": "issuer", "type": "LEFT", "on": "i.issuer_id = issuer.id"},
            {"table": "object", "alias": "o", "type": "LEFT", "on": "i.object_id = o.id"},
            {"table": "object_category", "alias": "oc", "type": "LEFT", "on": "o.category_id = oc.id"},
            {"table": "kostenstelle", "alias": "k", "type": "LEFT", "on": "i.kostenstelle_id = k.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "i.raum_id = r.id"},
            {"table": "building", "alias": "b", "type": "LEFT", "on": "r.building_id = b.id"},
            {"table": "professorship", "alias": "pr", "type": "LEFT", "on": "i.professorship_id = pr.id"},
            {"table": "abteilung", "alias": "a", "type": "LEFT", "on": "i.abteilung_id = a.id"}
        ],
        "columns": [
            "i.id AS inventory_id",
            "i.acquisition_date",
            "i.got",
            "i.return",
            "i.serial_number",
            "i.anlagennummer",
            "i.comment",
            "i.price",
            "owner.first_name AS owner_first_name",
            "owner.last_name AS owner_last_name",
            "issuer.first_name AS issuer_first_name",
            "issuer.last_name AS issuer_last_name",
            "o.name AS object_name",
            "oc.name AS object_category",
            "k.name AS kostenstelle_name",
            "r.name AS room_name",
            "b.name AS building_name",
            "pr.name AS professorship_name",
            "a.name AS abteilungsname"
        ],
        "primary_key": "inventory_id"
    },
    "object_lager": {
        "base_table": "object",
        "base_alias": "o",
        "joins": [
            {"table": "object_to_lager", "alias": "otl", "type": "LEFT", "on": "o.id = otl.object_id"},
            {"table": "lager", "alias": "l", "type": "LEFT", "on": "otl.lager_id = l.id"},
            {"table": "room", "alias": "r", "type": "LEFT", "on": "l.raum_id = r.id"},
            {"table": "building", "alias": "b", "type": "LEFT", "on": "r.building_id = b.id"},
            {"table": "object_category", "alias": "oc", "type": "LEFT", "on": "o.category_id = oc.id"}
        ],
        "columns": [
            "o.id AS object_id",
            "o.name AS object_name",
            "o.price",
            "oc.name AS category_name",
            "r.name AS room_name",
            "b.name AS building_name"
        ],
        "primary_key": "object_id"
    }
}

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
    alias_to_table = verwaltung.extract_alias_table_mapping(view_def)
    col_field_map = verwaltung.extract_column_field_mapping(view_def)

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
