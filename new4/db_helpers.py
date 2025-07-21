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


