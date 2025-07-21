# db_ops.py
import sqlite3
from copy import deepcopy

def get_joined_data(conn, view_config):
    base = view_config['base_table']
    base_alias = view_config['base_alias']
    cols = ", ".join(view_config['columns'])
    sql = f"SELECT {cols} FROM {base} AS {base_alias}"
    
    joins = view_config.get("joins", [])
    for join in joins:
        sql += f" {join['type']} JOIN {join['table']} AS {join['alias']} ON {join['on']}"
    
    cur = conn.execute(sql)
    rows = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    return rows

def update_row(conn, view_config, data):
    if "writable_tables" not in view_config:
        raise ValueError("Missing 'writable_tables' in view_config")

    pk = view_config["primary_key"]
    pk_val = data.get(pk)
    if pk_val is None:
        raise ValueError("Primary key value missing in update data")

    # Mappe AS-Namen zu Tabellenaliasen
    alias_to_table = {alias: table for table, alias in view_config["writable_tables"].items()}
    table_columns = {alias: [] for alias in alias_to_table}

    for col in view_config["columns"]:
        # Bestimme die Spalte, z.B. "p.first_name AS vorname"
        if ' AS ' in col:
            real, alias = col.split(" AS ")
        else:
            real = col
            alias = col.split(".")[-1]

        parts = real.strip().split(".")
        if len(parts) == 2:
            alias_prefix, col_name = parts
            if alias_prefix in alias_to_table:
                table_columns[alias_prefix].append((alias, col_name))  # (form_name, db_column)

    # UPDATE für jede Tabelle
    for alias_prefix, col_mappings in table_columns.items():
        update_data = {}
        for form_name, db_column in col_mappings:
            if form_name in data:
                update_data[db_column] = data[form_name]

        if not update_data:
            continue

        table = alias_to_table[alias_prefix]
        set_clause = ", ".join(f"{col} = ?" for col in update_data)
        values = list(update_data.values())
        conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values + [pk_val])

    conn.commit()

def delete_row(conn, view_config, pk_val):
    base_table = view_config['base_table']
    pk = view_config['primary_key']
    conn.execute(f"DELETE FROM {base_table} WHERE {pk} = ?", (pk_val,))
    conn.commit()

def insert_row(conn, view_config, data):
    table = view_config['base_table']

    # Extrahiere die Spaltennamen korrekt
    columns = []
    for col in view_config['columns']:
        if ' AS ' in col:
            name = col.split(' AS ')[-1]
        else:
            name = col.split('.')[-1]
        if name != 'id':  # Kein autoincrement-Feld
            columns.append(name)

    insert_data = {k: data.get(k, None) for k in columns}
    keys = ", ".join(insert_data.keys())
    placeholders = ", ".join("?" for _ in insert_data)
    values = list(insert_data.values())
    cur = conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
    conn.commit()
    return cur.lastrowid

