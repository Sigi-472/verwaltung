from db_defs import *
from db_helpers import describe_possible_joins, add_all_and_commit, add_and_commit, delete_and_commit, execute_and_commit, generate_editable_table

def insert_sample_data(session):
    anna = Person(first_name="Anna", last_name="Müller")
    max = Person(first_name="Max", last_name="Schmidt")
    add_all_and_commit(session, [anna, max])  # commit direkt nach add

    it = Abteilung(name="IT", abteilungsleiter_id=anna.id)
    add_and_commit(session, it)

    add_and_commit(session, PersonToAbteilung(person_id=anna.id, abteilung_id=it.id))
    add_and_commit(session, PersonToAbteilung(person_id=max.id, abteilung_id=it.id))

    prof = Professorship(name="AI Research")
    add_and_commit(session, prof)
    add_and_commit(session, ProfessorshipToPerson(person_id=anna.id, professorship_id=prof.id))
    add_and_commit(session, ProfessorshipToPerson(person_id=max.id, professorship_id=prof.id))

    building = Building(name="Hauptgebäude", building_number="H1", address="Campusstraße 1")
    add_and_commit(session, building)

    room1 = Room(name="2.01", floor=2, building_id=building.id)
    room2 = Room(name="2.02", floor=2, building_id=building.id)
    add_all_and_commit(session, [room1, room2])

    add_and_commit(session, PersonToRoom(person_id=anna.id, room_id=room1.id))

    transponder = Transponder(issuer_id=max.id, owner_id=anna.id, serial_number="T-123")
    add_and_commit(session, transponder)
    add_all_and_commit(session, [
        TransponderToRoom(transponder_id=transponder.id, room_id=room1.id),
        TransponderToRoom(transponder_id=transponder.id, room_id=room2.id),
    ])

    contact = PersonContact(person_id=anna.id, email="anna@example.com", phone="1234")
    add_and_commit(session, contact)


# ========== MAIN ==========
if __name__ == "__main__":
    engine = create_engine("sqlite:///mydatabase.db", echo=False)
    Base.metadata.drop_all(engine)  # Optional: Leert die DB vorher
    Base.metadata.create_all(engine)

    describe_possible_joins("person", Base)

    with Session(engine) as session:
        insert_sample_data(session)

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

        print("==============")

        query = session.query(Person).outerjoin(Person.contacts)  # Beispiel: `contacts` ist Beziehung zu PersonContact
        rows = query.all()

        columns = [
            ("Person", "first_name", "First Name"),
            ("Person", "last_name", "Last Name"),
            ("Person", "comment", "Comment"),
            ("contacts", "email", "Emails", True),   # True = mehrere (Liste)
            ("contacts", "fax", "Faxes", True),
        ]


        html_table = generate_editable_table(rows, columns, id_column='id')

        print(html_table)

