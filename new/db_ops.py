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
    tables = view_config.get('writable_tables')
    if not tables:
        raise ValueError("No writable_tables defined")
    
    pk = view_config['primary_key']
    pk_val = data[pk]
    
    for table, alias in tables.items():
        update_fields = {k: v for k, v in data.items() if k.startswith(alias + ".") or k in [f"{alias}.{c.split(' AS ')[-1]}" for c in view_config["columns"]]}
        update_fields_clean = {k.split('.')[-1]: v for k, v in update_fields.items()}
        if not update_fields_clean:
            continue
        
        sets = ", ".join(f"{k} = ?" for k in update_fields_clean)
        values = list(update_fields_clean.values())
        conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", values + [pk_val])
    conn.commit()

def delete_row(conn, view_config, pk_val):
    base_table = view_config['base_table']
    pk = view_config['primary_key']
    conn.execute(f"DELETE FROM {base_table} WHERE {pk} = ?", (pk_val,))
    conn.commit()

def insert_row(conn, view_config, data):
    table = view_config['base_table']
    columns = [col.split(' AS ')[-1] for col in view_config['columns'] if not col.endswith(' AS id')]
    insert_data = {k: data.get(k, None) for k in columns}
    keys = ", ".join(insert_data.keys())
    placeholders = ", ".join("?" for _ in insert_data)
    values = list(insert_data.values())
    cur = conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
    conn.commit()
    return cur.lastrowid

