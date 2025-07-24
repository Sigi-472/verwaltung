from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_interface import PersonWithContactHandler

DATABASE_URL = "sqlite:///database.db"  # Oder PostgreSQL/MySQL
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)


def main():
    session = Session()

    try:
        person_mgr = PersonWithContactHandler(session)

        # Person + Kontakte einfügen
        person_data = {
            "title": "Prof.",
            "first_name": "Alan",
            "last_name": "Turing",
            "comment": "Informatikpionier",
            "image_url": None
        }

        contacts = [
            {
                "email": "alan.turing@example.com",
                "phone": None,
                "fax": None,
                "comment": None
            },
            {
                "email": "a.turing@uni.cam.ac.uk",
                "phone": "+44-12345678",
                "fax": None,
                "comment": "Uni-Adresse"
            }
        ]

        person_id = person_mgr.insert_person_with_contacts(person_data, contacts)
        print("Person-ID:", person_id)

        # Einzelne Spalte setzen
        success = person_mgr.update_person_column(person_id, "title", "Dr.")
        print("Titel aktualisiert:", success)

        # Ganze Zeile setzen
        updated = person_mgr.update_person(person_id, {
            "comment": "Mathematiker",
            "image_url": "https://example.com/turing.jpg"
        })
        print("Daten aktualisiert:", updated)

    finally:
        session.close()


if __name__ == "__main__":
    main()
