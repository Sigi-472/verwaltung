from sqlalchemy.orm import class_mapper
from pprint import pprint
from sqlalchemy.inspection import inspect

def dier(msg):
    """
    Expects msg to be a list (oder auch einzelnes) von SQLAlchemy ORM-Objekten.
    Gibt die Attribute als Dict aus und beendet mit Exit-Code 10.
    """
    if not msg:
        print("Empty or None msg received.")

    # Falls msg kein Iterable ist (z.B. einzelnes Objekt), in Liste packen
    if not hasattr(msg, '__iter__') or isinstance(msg, str):
        msg = [msg]

    for obj in msg:
        if hasattr(obj, '__table__') or hasattr(obj, '__mapper__'):
            # ORM-Objekt, alle Spaltenattribute auslesen
            attrs = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
            pprint(attrs)
        else:
            # Kein ORM-Objekt, einfach pprint
            pprint(obj)

def describe_possible_joins(table_name: str, base_class):
    # Mapping aller ORM-Klassen aus der Base
    models = {cls.__tablename__: cls for cls in base_class.__subclasses__()}

    if table_name not in models:
        print(f"Tabelle '{table_name}' existiert nicht.")
        return

    cls = models[table_name]
    print(f"Joins für Tabelle '{table_name}':\n")

    mapper = class_mapper(cls)
    found = False
    for rel in mapper.relationships:
        target = rel.mapper.class_.__name__
        print(f"  {rel.key} → {target} ({'ManyToOne' if rel.direction.name == 'MANYTOONE' else rel.direction.name})")
        found = True

    if not found:
        print("  Keine Joins vorhanden.")

def add_and_commit(session, obj):
    session.add(obj)
    session.commit()

def add_all_and_commit(session, objs):
    session.add_all(objs)
    session.commit()

def delete_and_commit(session, obj):
    session.delete(obj)
    session.commit()

def execute_and_commit(session, stmt):
    session.execute(stmt)
    session.commit()

def generate_editable_table(rows, columns, id_column='id', allow_add_row=False):
    html = ['<form method="post"><table border="1"><thead><tr>']
    for _, _, label, *_ in columns:
        html.append(f'<th>{label or _ + "." + _}</th>')
    html.append('</tr></thead><tbody>')

    for row in rows:
        row_id = getattr(row, id_column)
        html.append('<tr>')
        for (table, col, label, *rest) in columns:
            is_list = rest[0] if rest else False
            if is_list:
                related_objs = getattr(row, table, [])
                if related_objs:
                    vals = [str(getattr(obj, col)) for obj in related_objs]
                    val = ", ".join(vals)
                else:
                    val = ""
            else:
                val = getattr(row, col, "")
            input_name = f"{table}:{col}:{row_id}"
            html.append(f'<td><input type="text" name="{input_name}" value="{val}"></td>')
        html.append('</tr>')

    if allow_add_row:
        html.append('<tr>')
        for (table, col, label, *rest) in columns:
            input_name = f"{table}:{col}:new"
            html.append(f'<td><input type="text" name="{input_name}" value=""></td>')
        html.append('</tr>')

    html.append('</tbody></table><input type="submit" value="Save"></form>')
    return "\n".join(html)
