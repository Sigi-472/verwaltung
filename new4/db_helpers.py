from sqlalchemy.orm import class_mapper

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

def generate_editable_table(rows, columns, id_column='id'):
    """
    rows: list von SQLAlchemy-Objekten (oder dicts mit Join-Ergebnissen)
    columns: list von tuples (table_name, column_name, label=None, is_list=False)
    id_column: der Primärschlüsselname in der Haupttabelle, wird für Input-Name gebraucht

    Gibt einen HTML-String mit editierbarer Tabelle zurück.
    """

    html = ['<form method="post"><table border="1"><thead><tr>']
    # Header
    for _, _, label, *_ in columns:
        html.append(f'<th>{label or _ + "." + _}</th>')
    html.append('</tr></thead><tbody>')

    for row in rows:
        # id der Haupttabelle pro Zeile, für eindeutigen input name
        row_id = getattr(row, id_column)

        html.append('<tr>')
        for (table, col, label, *rest) in columns:
            is_list = rest[0] if rest else False

            # Wir greifen je nach Join-Result unterschiedlich zu:
            # - row.Person.first_name oder
            # - row.PersonContact.email, etc.
            # Falls List, nehmen wir eine Liste von Objekten

            # Beispiel: row.Person.first_name oder row.PersonContact (Liste)
            val = None
            if is_list:
                # z.B. row.PersonContacts = Liste von Objekten
                related_objs = getattr(row, table, [])
                if related_objs:
                    # Alle Werte der Spalte aus der Liste holen
                    vals = [str(getattr(obj, col)) for obj in related_objs]
                    val = ", ".join(vals)
                else:
                    val = ""
            else:
                # Einfacher Zugriff
                related_obj = getattr(row, table, None)
                val = getattr(related_obj, col) if related_obj else ""

            # Input name mit Tabelle, Spalte und Zeilen-id
            input_name = f"{table}:{col}:{row_id}"
            # Editable input Feld
            html.append(f'<td><input type="text" name="{input_name}" value="{val}"></td>')

        html.append('</tr>')
    html.append('</tbody></table><input type="submit" value="Save"></form>')
    return "\n".join(html)
