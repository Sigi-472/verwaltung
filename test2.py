from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_interface import (
    PersonHandler, PersonContactHandler, AbteilungHandler, PersonToAbteilungHandler,
    BuildingHandler, RoomHandler, PersonToRoomHandler, TransponderHandler, TransponderToRoomHandler
)

DATABASE_URL = "sqlite:///database.db"  # Oder dein PostgreSQL/MySQL-String
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)


def main():
    session = Session()

    try:
        person_mgr = PersonHandler(session)
        contact_mgr = PersonContactHandler(session)
        abt_mgr = AbteilungHandler(session)

        # Person einfügen
        person_data = {
            "title": "Prof.",
            "first_name": "Alan",
            "last_name": "Turing",
            "comment": "Informatikpionier",
            "image_url": None
        }

        person_id = person_mgr.insert_person(person_data)
        print("Person-ID:", person_id)

        # Contact einfügen
        contact_id = contact_mgr.insert_into_db({
            "person_id": person_id,
            "email": "alan.turing@example.com",
            "phone": None,
            "fax": None,
            "comment": None
        })
        print("Contact-ID:", contact_id)

        # Spalte setzen
        success = person_mgr.set_column(person_id, "title", "Dr.")
        print("Titel aktualisiert:", success)

        # Ganze Zeile setzen
        updated = person_mgr.set_row(person_id, {
            "comment": "Mathematiker",
            "image_url": "https://example.com/turing.jpg"
        })
        print("Daten aktualisiert:", updated)

    finally:
        session.close()


if __name__ == "__main__":
    main()

