from sqlalchemy import (create_engine, Column, Integer, String, Text, ForeignKey, Date, Float, TIMESTAMP)
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import declarative_base, relationship, Session, class_mapper, RelationshipProperty, aliased, joinedload

Base = declarative_base()

# Person
class Person(Base):
    __tablename__ = "person"
    id = Column(Integer, primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    created_at = Column(TIMESTAMP)
    comment = Column(Text)

    contacts = relationship("PersonContact", back_populates="person", cascade="all, delete")
    rooms = relationship("PersonToRoom", back_populates="person", cascade="all, delete")
    transponders_issued = relationship("Transponder", foreign_keys="[Transponder.issuer_id]", back_populates="issuer")
    transponders_owned = relationship("Transponder", foreign_keys="[Transponder.owner_id]", back_populates="owner")
    departments = relationship("Abteilung", back_populates="leiter")
    person_abteilungen = relationship("PersonToAbteilung", back_populates="person", cascade="all, delete")
    professorships = relationship("ProfessorshipToPerson", back_populates="person", cascade="all, delete")

class PersonContact(Base):
    __tablename__ = "person_contact"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("person.id", ondelete="CASCADE"))
    phone = Column(Text)
    fax = Column(Text)
    email = Column(Text)
    comment = Column(Text)
    person = relationship("Person", back_populates="contacts")

class Abteilung(Base):
    __tablename__ = "abteilung"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    abteilungsleiter_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))
    leiter = relationship("Person", back_populates="departments")
    persons = relationship("PersonToAbteilung", back_populates="abteilung", cascade="all, delete")

class PersonToAbteilung(Base):
    __tablename__ = "person_to_abteilung"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("person.id", ondelete="CASCADE"))
    abteilung_id = Column(Integer, ForeignKey("abteilung.id", ondelete="CASCADE"))
    person = relationship("Person", back_populates="person_abteilungen")
    abteilung = relationship("Abteilung", back_populates="persons")

class Kostenstelle(Base):
    __tablename__ = "kostenstelle"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    professorships = relationship("Professorship", back_populates="kostenstelle")

class Professorship(Base):
    __tablename__ = "professorship"
    id = Column(Integer, primary_key=True)
    kostenstelle_id = Column(Integer, ForeignKey("kostenstelle.id", ondelete="SET NULL"))
    name = Column(Text)
    kostenstelle = relationship("Kostenstelle", back_populates="professorships")
    persons = relationship("ProfessorshipToPerson", back_populates="professorship", cascade="all, delete")

class ProfessorshipToPerson(Base):
    __tablename__ = "professorship_to_person"
    id = Column(Integer, primary_key=True)
    professorship_id = Column(Integer, ForeignKey("professorship.id", ondelete="CASCADE"))
    person_id = Column(Integer, ForeignKey("person.id", ondelete="CASCADE"))
    professorship = relationship("Professorship", back_populates="persons")
    person = relationship("Person", back_populates="professorships")

class Building(Base):
    __tablename__ = "building"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    building_number = Column(Text)
    address = Column(Text)
    rooms = relationship("Room", back_populates="building")

class Room(Base):
    __tablename__ = "room"
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("building.id", ondelete="SET NULL"))
    name = Column(Text)
    floor = Column(Integer)
    building = relationship("Building", back_populates="rooms")
    person_links = relationship("PersonToRoom", back_populates="room", cascade="all, delete")
    transponder_links = relationship("TransponderToRoom", back_populates="room", cascade="all, delete")

class PersonToRoom(Base):
    __tablename__ = "person_to_room"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("person.id", ondelete="CASCADE"))
    room_id = Column(Integer, ForeignKey("room.id", ondelete="CASCADE"))
    person = relationship("Person", back_populates="rooms")
    room = relationship("Room", back_populates="person_links")

class Transponder(Base):
    __tablename__ = "transponder"
    id = Column(Integer, primary_key=True)
    issuer_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))
    got = Column(Date)
    return_ = Column("return", Date)
    serial_number = Column(Text)
    comment = Column(Text)
    issuer = relationship("Person", foreign_keys=[issuer_id], back_populates="transponders_issued")
    owner = relationship("Person", foreign_keys=[owner_id], back_populates="transponders_owned")
    room_links = relationship("TransponderToRoom", back_populates="transponder", cascade="all, delete")

class TransponderToRoom(Base):
    __tablename__ = "transponder_to_room"
    id = Column(Integer, primary_key=True)
    transponder_id = Column(Integer, ForeignKey("transponder.id", ondelete="CASCADE"))
    room_id = Column(Integer, ForeignKey("room.id", ondelete="CASCADE"))
    transponder = relationship("Transponder", back_populates="room_links")
    room = relationship("Room", back_populates="transponder_links")

class ObjectCategory(Base):
    __tablename__ = "object_category"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    objects = relationship("Object", back_populates="category")

class Object(Base):
    __tablename__ = "object"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    price = Column(Float)
    category_id = Column(Integer, ForeignKey("object_category.id", ondelete="SET NULL"))
    category = relationship("ObjectCategory", back_populates="objects")

class Lager(Base):
    __tablename__ = "lager"
    id = Column(Integer, primary_key=True)
    raum_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"))

class ObjectToLager(Base):
    __tablename__ = "object_to_lager"
    id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey("object.id", ondelete="CASCADE"))
    lager_id = Column(Integer, ForeignKey("lager.id", ondelete="CASCADE"))

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))
    object_id = Column(Integer, ForeignKey("object.id", ondelete="SET NULL"))
    issuer_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))
    acquisition_date = Column(Date)
    got = Column(Date)
    return_ = Column("return", Date)
    serial_number = Column(Text)
    kostenstelle_id = Column(Integer, ForeignKey("kostenstelle.id", ondelete="SET NULL"))
    anlagennummer = Column(Text)
    comment = Column(Text)
    price = Column(Float)
    raum_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"))
    professorship_id = Column(Integer, ForeignKey("professorship.id", ondelete="SET NULL"))
    abteilung_id = Column(Integer, ForeignKey("abteilung.id", ondelete="SET NULL"))

# ========== DEMO + JOIN-BEISPIELE ==========

def build_joined_query(table_names: list[str], session: Session):
    # Alle bekannten Models aus Base holen
    known_models = {cls.__tablename__: cls for cls in Base.__subclasses__()}

    # Models aus Eingabeliste sammeln
    try:
        models = [known_models[name] for name in table_names]
    except KeyError as e:
        raise ValueError(f"Unbekannter Tabellenname: {e.args[0]}")

    if not models:
        raise ValueError("Keine gültigen Tabellen angegeben.")

    # Starte mit erster Tabelle
    base_model = models[0]
    query = session.query(base_model)
    joined = {base_model}

    for model in models[1:]:
        found = False
        # Versuche: base_model → model
        for rel in inspect(base_model).relationships:
            if rel.mapper.class_ == model:
                query = query.join(getattr(base_model, rel.key))
                joined.add(model)
                found = True
                break
        if not found:
            # Versuche: model → base_model
            for rel in inspect(model).relationships:
                if rel.mapper.class_ == base_model:
                    query = query.join(model)
                    joined.add(model)
                    found = True
                    break
        if not found:
            raise ValueError(f"Keine direkte Beziehung zwischen {base_model.__name__} und {model.__name__} gefunden.")

    return query

def describe_joins(table_name: str, base_class):
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

def insert_sample_data(session):
    # Personen
    anna = Person(first_name="Anna", last_name="Müller")
    max = Person(first_name="Max", last_name="Schmidt")
    session.add_all([anna, max])
    session.flush()

    # Abteilung
    it = Abteilung(name="IT", abteilungsleiter_id=anna.id)
    session.add(it)
    session.flush()

    # Zuordnung Person ↔ Abteilung
    session.add(PersonToAbteilung(person_id=anna.id, abteilung_id=it.id))
    session.add(PersonToAbteilung(person_id=max.id, abteilung_id=it.id))

    # Professur und Zuordnung
    prof = Professorship(name="AI Research")
    session.add(prof)
    session.flush()
    session.add(ProfessorshipToPerson(person_id=anna.id, professorship_id=prof.id))
    session.add(ProfessorshipToPerson(person_id=max.id, professorship_id=prof.id))

    # Gebäude und Raum
    building = Building(name="Hauptgebäude", building_number="H1", address="Campusstraße 1")
    session.add(building)
    session.flush()
    room1 = Room(name="2.01", floor=2, building_id=building.id)
    room2 = Room(name="2.02", floor=2, building_id=building.id)
    session.add_all([room1, room2])
    session.flush()

    # Person zu Raum
    session.add(PersonToRoom(person_id=anna.id, room_id=room1.id))

    # Transponder + Zuordnung zu Raum
    transponder = Transponder(issuer_id=max.id, owner_id=anna.id, serial_number="T-123")
    session.add(transponder)
    session.flush()
    session.add(TransponderToRoom(transponder_id=transponder.id, room_id=room1.id))
    session.add(TransponderToRoom(transponder_id=transponder.id, room_id=room2.id))

    # Kontakt
    contact = PersonContact(person_id=anna.id, email="anna@example.com", phone="1234")
    session.add(contact)

    session.commit()

def demo_queries(engine):
    with Session(engine) as session:
        print("\nBeispiel: Alle Personen mit ihren Abteilungen:")
        for entry in session.query(Person).join(PersonToAbteilung).join(Abteilung).all():
            for abt in entry.person_abteilungen:
                print(f"{entry.first_name} {entry.last_name} → {abt.abteilung.name}")

        print("\nBeispiel: Transponder mit Besitzer und Räumen:")
        for trans in session.query(Transponder).join(TransponderToRoom).join(Room).all():
            print(f"Transponder {trans.serial_number} gehört {trans.owner.first_name} {trans.owner.last_name} "
                  f"und gilt für Räume {[r.room.name for r in trans.room_links]}")

        print("\nBeispiel: Professuren mit zugeordneten Personen:")
        for prof in session.query(Professorship).join(ProfessorshipToPerson).join(Person).all():
            print(f"{prof.name} → {[p.person.first_name + ' ' + p.person.last_name for p in prof.persons]}")

# ========== MAIN ==========
if __name__ == "__main__":
    engine = create_engine("sqlite:///mydatabase.db", echo=False)
    Base.metadata.drop_all(engine)  # Optional: Leert die DB vorher
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        insert_sample_data(session)

    demo_queries(engine)

    describe_joins("person", Base)

    with Session(engine) as session:
        query = (
            session.query(Person)
            .options(
                joinedload(Person.person_abteilungen)
                .joinedload(PersonToAbteilung.abteilung)
                .joinedload(Abteilung.leiter)
                .joinedload(Person.contacts)  # Kontakte des Leiters
            )
            .filter(Person.first_name == "Anna")
        )

        results = query.filter(Person.first_name == "Anna").all()
        for p in results:
            for p in results:
                for pa in p.person_abteilungen:
                    abteilung = pa.abteilung
                    leiter = abteilung.leiter
                    if leiter:
                        emails = [c.email for c in leiter.contacts if c.email]
                        print(p.first_name, "-> Abt:", abteilung.name, "Leiter:", leiter.first_name, leiter.last_name, "Emails:", emails)

