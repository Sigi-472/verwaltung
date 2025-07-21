from db_defs import *
from db_helpers import describe_possible_joins

# ========== DEMO + JOIN-BEISPIELE ==========

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

# ========== MAIN ==========
if __name__ == "__main__":
    engine = create_engine("sqlite:///mydatabase.db", echo=False)
    Base.metadata.drop_all(engine)  # Optional: Leert die DB vorher
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        insert_sample_data(session)

    describe_possible_joins("person", Base)

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


        query = (
            session.query(Person)
            .options(
                joinedload(Person.person_abteilungen)
                .joinedload(PersonToAbteilung.abteilung)
                .joinedload(Abteilung.leiter)
                .joinedload(Person.contacts)
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

