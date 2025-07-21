# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any, Union
from beartype import beartype
from flask import jsonify
import re

DB_CONN: Optional[sqlite3.Connection] = None


def add_column(cursor, conn, base_table, new_col):
    col_name = new_col.get("name")
    col_type = new_col.get("type", "TEXT")
    if not col_name:
        return jsonify({"error": "Spaltenname fehlt"}), 400
    try:
        cursor.execute(f"ALTER TABLE {base_table} ADD COLUMN {col_name} {col_type}")
        conn.commit()
        return jsonify({"success": True, "message": f"Spalte '{col_name}' hinzugefügt"})
    except Exception as e:
        return jsonify({"error": f"Spalte konnte nicht hinzugefügt werden: {str(e)}"}), 500


def drop_column(cursor, conn, base_table, drop_col):
    if not drop_col:
        return jsonify({"error": "Keine Spalte zum Löschen angegeben"}), 400
    try:
        cursor.execute(f"ALTER TABLE {base_table} DROP COLUMN {drop_col}")
        conn.commit()
        return jsonify({"success": True, "message": f"Spalte '{drop_col}' gelöscht"})
    except Exception as e:
        return jsonify({"error": f"Konnte Spalte nicht löschen: {str(e)}"}), 500


def validate_primary_key(data, pk_field):
    if pk_field not in data:
        return jsonify({"error": f"Primärschlüssel '{pk_field}' fehlt"}), 400
    return None


def extract_updates(data, pk_field, col_field_map):
    update_fields = [k for k in data if k != pk_field and k in col_field_map]
    if not update_fields:
        return None, jsonify({"error": "Keine gültigen Felder zum Aktualisieren"}), 400
    return update_fields, None


def group_updates_by_table(update_fields, data, col_field_map, alias_to_table):
    updates_by_table = {}
    for field in update_fields:
        alias, real_field = col_field_map[field]
        table = alias_to_table.get(alias)
        if not table:
            continue
        updates_by_table.setdefault(table, {})[real_field] = data[field]
    return updates_by_table

def app_update_table(cursor, table, fields_values, pk_field, pk_value):
    try:
        set_clauses = []
        params = []
        for k, v in fields_values.items():
            set_clauses.append(f"{k} = ?")
            params.append(v)
        params.append(pk_value)
        sql_update = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {pk_field} = ?"
        cursor.execute(sql_update, params)
        if cursor.rowcount == 0:
            # Kein Datensatz zum Updaten - INSERT machen
            all_fields = list(fields_values.keys()) + [pk_field]
            all_values = list(fields_values.values()) + [pk_value]
            placeholders = ", ".join(["?"] * len(all_fields))
            sql_insert = f"INSERT INTO {table} ({', '.join(all_fields)}) VALUES ({placeholders})"
            cursor.execute(sql_insert, all_values)
    except Exception as e:
        raise RuntimeError(f"Fehler in app_update_table_or_insert: {str(e)}")


def parse_join_on_condition(join_on, join_alias, base_table, cursor, pk_value, alias_to_table):
    try:
        left, right = join_on.split("=")
        left = left.strip()
        right = right.strip()

        if left.startswith(join_alias + "."):
            join_side = left
            other_side = right
        elif right.startswith(join_alias + "."):
            join_side = right
            other_side = left
        else:
            return None, None, "Unbekannte Join-Bedingung (kein Alias passt)", 400

        join_col = join_side.split(".")[1]
        other_alias, other_col = other_side.split(".")
        other_table = alias_to_table.get(other_alias)

        if not other_table:
            return None, None, f"Alias '{other_alias}' ist keiner Tabelle zugeordnet", 400

        # Sonderfall: Zugriff auf base_table mit id
        if other_alias == alias_to_table.get("base_alias", ""):
            cursor.execute(f"SELECT {other_col} FROM {other_table} WHERE id = ?", (pk_value,))
        else:
            # Versuch, Fremd-ID aus Join-Tabelle zu lesen
            # Annahme: Join-Tabelle hat 1:n-Beziehung mit base_table → wir lesen mit base_id
            base_id_col = f"{base_table}_id"
            cursor.execute(f"SELECT {other_col} FROM {other_table} WHERE {base_id_col} = ?", (pk_value,))

        row = cursor.fetchone()
        if not row:
            return None, None, f"Kein Wert in {other_table} für {other_col} gefunden", 404

        return join_col, row[0], None, None

    except Exception as e:
        return None, None, f"Fehler bei Join-Bedingung: {str(e)}", 500

def invert_dict(d):
    return {v: k for k, v in d.items()}

def update_join_tables(cursor, view_def, updates_by_table, base_table, pk_value, alias_to_table):
    for join in view_def.get("joins", []):
        join_table = join["table"]
        join_alias = join.get("alias")
        join_on = join.get("on")

        if join_table not in updates_by_table:
            continue

        if not join_on:
            raise RuntimeError("Join-Bedingung fehlt")

        filter_col, filter_val, error_response, status_code = parse_join_on_condition(join_on, join_alias, base_table, cursor, pk_value, alias_to_table)
        if error_response:
            raise RuntimeError(f"Fehler bei parse_join_on_condition: {error_response}")

        cursor.execute(f"SELECT id FROM {join_table} WHERE {filter_col} = ?", (filter_val,))
        join_rows = cursor.fetchall()

        if not join_rows:
            # Kein Datensatz vorhanden -> INSERT machen mit filter_col=filter_val plus update fields
            fields = updates_by_table[join_table].copy()
            # filter_col ist das Join-Kriterium, muss mit rein
            fields[filter_col] = filter_val
            all_fields = list(fields.keys())
            all_values = list(fields.values())
            placeholders = ", ".join(["?"] * len(all_fields))
            sql_insert = f"INSERT INTO {join_table} ({', '.join(all_fields)}) VALUES ({placeholders})"
            cursor.execute(sql_insert, all_values)
            continue

        for join_row in join_rows:
            join_id = join_row["id"]
            set_clauses = []
            params = []
            for k, v in updates_by_table[join_table].items():
                set_clauses.append(f"{k} = ?")
                params.append(v)
            params.append(join_id)
            sql_update = f"UPDATE {join_table} SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql_update, params)
            if cursor.rowcount == 0:
                # Update fehlgeschlagen, mach stattdessen Insert
                fields = updates_by_table[join_table].copy()
                # Wenn id existiert, besser nicht neu einfügen, sondern Fehler werfen oder anders handeln
                # Hier überspringen wir Insert, da id schon existiert
                raise RuntimeError(f"Update in {join_table} mit id={join_id} fehlgeschlagen und Insert abgebrochen")

def extract_alias_table_mapping(view_def):
    mapping = {view_def["base_alias"]: view_def["base_table"]}
    for join in view_def.get("joins", []):
        mapping[join["alias"]] = join["table"]
    return mapping

def extract_column_field_mapping(view_def):
    col_map = {}
    for col in view_def["columns"]:
        m = re.match(r"(\w+)\.(\w+)\s+AS\s+(\w+)", col.strip(), re.IGNORECASE)
        if m:
            alias, field, as_name = m.groups()
            col_map[as_name] = (alias, field)
        else:
            m2 = re.match(r"(\w+)\.(\w+)", col.strip())
            if m2:
                alias, field = m2.groups()
                col_map[field] = (alias, field)
    return col_map

@beartype
def insert_into_table(conn: sqlite3.Connection, table: str, data: Dict[str, Any]) -> int:
    """
    Insert in Tabelle mit dict data.

    Args:
        conn: Datenbank-Verbindung
        table: Tabellenname
        data: Dict Spalte -> Wert

    Returns:
        ID des neuen Eintrags (angenommen autoincrement id)
    """
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["?"] * len(keys))
    columns = ", ".join(keys)

    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

    cursor = conn.cursor()
    try:
        cursor.execute(sql, values)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Fehler beim Insert in {table}: {e}")

@beartype
def update_table(conn: sqlite3.Connection, cursor: sqlite3.Cursor, table: str, primary_key: str, data: Dict[str, Any]) -> None:
    """
    Update Eintrag in Tabelle. data muss primary_key enthalten.

    Args:
        conn: DB Verbindung
        table: Tabellenname
        primary_key: Name des Primärschlüssels
        data: dict mit Spalten inkl. primary_key

    Raises:
        RuntimeError bei Fehler
    """
    if primary_key not in data:
        raise ValueError(f"primary_key {primary_key} fehlt in data")

    pk_value = data[primary_key]
    update_keys = [k for k in data.keys() if k != primary_key]

    if not update_keys:
        return  # nichts zu tun

    set_clause = ", ".join([f"{k} = ?" for k in update_keys])
    values = [data[k] for k in update_keys]
    values.append(pk_value)

    sql = f"UPDATE {table} SET {set_clause} WHERE {primary_key} = ?"

    try:
        cursor.execute(sql, values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Fehler beim Update in {table}: {e}")

@beartype
def delete_from_table(conn: sqlite3.Connection, table: str, primary_key: str, pk_value: Any) -> None:
    """
    Löscht Eintrag anhand Primärschlüssel.

    Args:
        conn: DB Verbindung
        table: Tabellenname
        primary_key: Name PK Spalte
        pk_value: Wert des PK

    Raises:
        RuntimeError bei Fehler
    """
    sql = f"DELETE FROM {table} WHERE {primary_key} = ?"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (pk_value,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Fehler beim Delete in {table}: {e}")

@beartype
def fetch_join_view(conn: sqlite3.Connection, view_def: Dict[str, Any]) -> List[sqlite3.Row]:
    """
    Lädt Daten aus der Join-View.

    Args:
        conn: Datenbank-Verbindung
        view_def: Join-View-Definition

    Returns:
        Liste von sqlite3.Row
    """
    try:
        sql, params = build_join_query(view_def)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise RuntimeError(f"Fehler beim Laden der Join-View: {e}")

@beartype
def build_join_query(view_def: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Erzeugt eine SQL-Select-Abfrage mit Joins basierend auf view_def.

    Args:
        view_def: Dict mit Keys base_table, base_alias, joins, columns

    Returns:
        sql_query, params (aktuell keine Parameter, aber vorbereitet)
    """
    base_table = view_def.get("base_table")
    base_alias = view_def.get("base_alias", base_table)
    joins = view_def.get("joins", [])
    columns = view_def.get("columns", ["*"])

    if not base_table:
        raise ValueError("base_table ist erforderlich in view_def")

    select_clause = ", ".join(columns)

    sql = f"SELECT {select_clause} FROM {base_table} AS {base_alias} "

    for join in joins:
        join_type = join.get("type", "INNER").upper()
        join_table = join.get("table")
        join_alias = join.get("alias", join_table)
        join_on = join.get("on")
        if not join_table or not join_on:
            raise ValueError("Join muss table und on enthalten")

        sql += f" {join_type} JOIN {join_table} AS {join_alias} ON {join_on} "

    return sql, []

def parse_optional_int(value):
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "" or value.strip().lower() == "none":
            return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

@beartype
def connect_to_db(db_path: str) -> sqlite3.Connection:
    global DB_CONN
    try:
        DB_CONN = sqlite3.connect(db_path)
        DB_CONN.execute('PRAGMA foreign_keys = ON')
        DB_CONN.row_factory = sqlite3.Row

        init_db(DB_CONN)

        return DB_CONN
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to connect to database: {e}")

@beartype
def init_db(connection: sqlite3.Connection) -> None:
    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        schema_statements = [

            # person
            """
            CREATE TABLE IF NOT EXISTS person (
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP,
                comment TEXT
            );
            """,

            # abteilung
            """
            CREATE TABLE IF NOT EXISTS abteilung (
                id INTEGER PRIMARY KEY,
                name TEXT,
                abteilungsleiter_id INTEGER,
                FOREIGN KEY (abteilungsleiter_id) REFERENCES person(id) ON DELETE SET NULL
            );
            """,

            # person_to_abteilung
            """
            CREATE TABLE IF NOT EXISTS person_to_abteilung (
                id INTEGER PRIMARY KEY,
                person_id INTEGER,
                abteilung_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
                FOREIGN KEY (abteilung_id) REFERENCES abteilung(id) ON DELETE CASCADE
            );
            """,

            # kostenstelle
            """
            CREATE TABLE IF NOT EXISTS kostenstelle (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
            """,

            # professorship
            """
            CREATE TABLE IF NOT EXISTS professorship (
                id INTEGER PRIMARY KEY,
                kostenstelle_id INTEGER,
                name TEXT,
                FOREIGN KEY (kostenstelle_id) REFERENCES kostenstelle(id) ON DELETE SET NULL
            );
            """,

            # professorship_to_person
            """
            CREATE TABLE IF NOT EXISTS professorship_to_person (
                id INTEGER PRIMARY KEY,
                professorship_id INTEGER,
                person_id INTEGER,
                FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE CASCADE,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
            );
            """,

            # person_contact
            """
            CREATE TABLE IF NOT EXISTS person_contact (
                id INTEGER PRIMARY KEY,
                person_id INTEGER,
                phone TEXT,
                fax TEXT,
                email TEXT,
                comment TEXT,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
            );
            """,

            # building
            """
            CREATE TABLE IF NOT EXISTS building (
                id INTEGER PRIMARY KEY,
                name TEXT,
                building_number TEXT,
                address TEXT
            );
            """,

            # room
            """
            CREATE TABLE IF NOT EXISTS room (
                id INTEGER PRIMARY KEY,
                building_id INTEGER,
                name TEXT,
                floor INTEGER,
                FOREIGN KEY (building_id) REFERENCES building(id) ON DELETE SET NULL
            );
            """,

            # person_to_room
            """
            CREATE TABLE IF NOT EXISTS person_to_room (
                id INTEGER PRIMARY KEY,
                person_id INTEGER,
                room_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
                FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
            );
            """,

            # transponder
            """
            CREATE TABLE IF NOT EXISTS transponder (
                id INTEGER PRIMARY KEY,
                issuer_id INTEGER,
                owner_id INTEGER,
                got DATE,
                return DATE,
                serial_number TEXT,
                comment TEXT,
                FOREIGN KEY (issuer_id) REFERENCES person(id) ON DELETE SET NULL,
                FOREIGN KEY (owner_id) REFERENCES person(id) ON DELETE SET NULL
            );
            """,

            # transponder_to_room
            """
            CREATE TABLE IF NOT EXISTS transponder_to_room (
                id INTEGER PRIMARY KEY,
                transponder_id INTEGER,
                room_id INTEGER,
                FOREIGN KEY (transponder_id) REFERENCES transponder(id) ON DELETE CASCADE,
                FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
            );
            """,

            # object_category
            """
            CREATE TABLE IF NOT EXISTS object_category (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
            """,

            # object
            """
            CREATE TABLE IF NOT EXISTS object (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price REAL,
                category_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES object_category(id) ON DELETE SET NULL
            );
            """,

            # lager
            """
            CREATE TABLE IF NOT EXISTS lager (
                id INTEGER PRIMARY KEY,
                raum_id INTEGER,
                FOREIGN KEY (raum_id) REFERENCES room(id) ON DELETE SET NULL
            );
            """,

            # object_to_lager
            """
            CREATE TABLE IF NOT EXISTS object_to_lager (
                id INTEGER PRIMARY KEY,
                object_id INTEGER,
                lager_id INTEGER,
                FOREIGN KEY (object_id) REFERENCES object(id) ON DELETE CASCADE,
                FOREIGN KEY (lager_id) REFERENCES lager(id) ON DELETE CASCADE
            );
            """,

            # inventory
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER,
                object_id INTEGER,
                issuer_id INTEGER,
                acquisition_date DATE,
                got DATE,
                return DATE,
                serial_number TEXT,
                kostenstelle_id INTEGER,
                anlagennummer TEXT,
                comment TEXT,
                price REAL,
                raum_id INTEGER,
                professorship_id INTEGER,
                abteilung_id INTEGER,
                FOREIGN KEY (owner_id) REFERENCES person(id) ON DELETE SET NULL,
                FOREIGN KEY (issuer_id) REFERENCES person(id) ON DELETE SET NULL,
                FOREIGN KEY (object_id) REFERENCES object(id) ON DELETE SET NULL,
                FOREIGN KEY (kostenstelle_id) REFERENCES kostenstelle(id) ON DELETE SET NULL,
                FOREIGN KEY (raum_id) REFERENCES room(id) ON DELETE SET NULL,
                FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE SET NULL,
                FOREIGN KEY (abteilung_id) REFERENCES abteilung(id) ON DELETE SET NULL
            );
            """,

            # person_to_professorship
            """
            CREATE TABLE IF NOT EXISTS person_to_professorship (
                id INTEGER PRIMARY KEY,
                person_id INTEGER,
                professorship_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
                FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE CASCADE
            );
            """
        ]

        for statement in schema_statements:
            cursor.execute(statement)

        connection.commit()
    except Exception as e:
        connection.rollback()
        raise RuntimeError(f"Database initialization failed: {e}")
    finally:
        cursor.close()

@beartype
def _get_connection() -> sqlite3.Connection:
    connect_to_db("databases.db")

    if DB_CONN is None:
        raise RuntimeError("Database connection not established. Call connect_to_db() first.")
    return DB_CONN

@beartype
def insert_person(first_name: str, last_name: str, comment: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> int:
    if not conn:
        conn = _get_connection()

    created_at = datetime.utcnow().isoformat()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO person (first_name, last_name, created_at, comment)
            VALUES (?, ?, ?, ?)
        """, (first_name, last_name, created_at, comment))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert person: {e}")

@beartype
def update_person(person_id: int, *, first_name: Optional[str] = None, last_name: Optional[str] = None, comment: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> None:
    if not conn:
        conn = _get_connection()

    fields = []
    values = []
    if first_name is not None:
        fields.append("first_name = ?")
        values.append(first_name)
    if last_name is not None:
        fields.append("last_name = ?")
        values.append(last_name)
    if comment is not None:
        fields.append("comment = ?")
        values.append(comment)
    if not fields:
        return
    values.append(person_id)
    try:
        conn.execute(f"""
            UPDATE person SET {', '.join(fields)} WHERE id = ?
        """, values)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to update person: {e}")

@beartype
def delete_person(person_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
    if not conn:
        conn = _get_connection()

    try:
        conn.execute("DELETE FROM person WHERE id = ?", (person_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to delete person: {e}")

@beartype
def insert_abteilung(name: str, abteilungsleiter_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> int:
    if not conn:
        conn = _get_connection()

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO abteilung (name, abteilungsleiter_id)
            VALUES (?, ?)
        """, (name, abteilungsleiter_id))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert abteilung: {e}")

@beartype
def update_abteilung(abteilung_id: int, *, name: Optional[str] = None, abteilungsleiter_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> None:
    if not conn:
        conn = _get_connection()

    fields = []
    values = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if abteilungsleiter_id is not None:
        fields.append("abteilungsleiter_id = ?")
        values.append(abteilungsleiter_id)
    if not fields:
        return
    values.append(abteilung_id)
    try:
        conn.execute(f"""
            UPDATE abteilung SET {', '.join(fields)} WHERE id = ?
        """, values)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to update abteilung: {e}")

@beartype
def delete_abteilung(abteilung_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
    if not conn:
        conn = _get_connection()
    try:
        conn.execute("DELETE FROM abteilung WHERE id = ?", (abteilung_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to delete abteilung: {e}")

@beartype
def assign_person_to_abteilung(person_id: int, abteilung_id: int, conn: Optional[sqlite3.Connection] = None) -> int:
    if not conn:
        conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO person_to_abteilung (person_id, abteilung_id)
            VALUES (?, ?)
        """, (person_id, abteilung_id))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to assign person to abteilung: {e}")

@beartype
def remove_person_from_abteilung(person_to_abteilung_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
    if not conn:
        conn = _get_connection()
    try:
        conn.execute("DELETE FROM person_to_abteilung WHERE id = ?", (person_to_abteilung_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to remove person from abteilung: {e}")
