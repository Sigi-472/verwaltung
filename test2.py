from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_interface import (
    PersonWithContactHandler,
    AbteilungHandler,
    PersonToAbteilungHandler,
    BuildingHandler,
    RoomHandler,
    PersonToRoomHandler,
    TransponderHandler,
    TransponderToRoomHandler,
)

DATABASE_URL = "sqlite:///database.db"  # Oder PostgreSQL/MySQL
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)


def safe_insert(handler, data):
    if hasattr(handler, "insert_data"):
        try:
            inserted_id = handler.insert_data(data)
            print(f"-> Eintrag eingefügt mit ID: {inserted_id}")
            return inserted_id
        except Exception as e:
            print(f"Fehler beim Einfügen: {e}")
            return None
    else:
        print(f"Handler {handler.__class__.__name__} hat keine Methode insert_data.")
        return None


def safe_update(handler, id_, update_data):
    if hasattr(handler, "update_by_id"):
        try:
            success = handler.update_by_id(id_, update_data)
            print(f"-> Update erfolgreich: {success}")
        except Exception as e:
            print(f"Fehler beim Update: {e}")
    else:
        print(f"Handler {handler.__class__.__name__} hat keine Methode update_by_id.")


def test_handler(handler_class, insert_data, update_data, name: str):
    print(f"\nTeste {name}...")

    session = Session()
    try:
        handler = handler_class(session)

        if name == "PersonWithContactHandler":
            # Spezielle Methode benutzen, falls vorhanden
            try:
                inserted_id = handler.insert_person_with_contacts(insert_data, insert_data.get("contacts", []))
                print(f"-> Eintrag eingefügt mit ID: {inserted_id}")
                if inserted_id is not None:
                    safe_update(handler, inserted_id, update_data)
            except Exception as e:
                print(f"Fehler bei insert_person_with_contacts: {e}")
        else:
            inserted_id = safe_insert(handler, insert_data)
            if inserted_id is not None:
                safe_update(handler, inserted_id, update_data)
    finally:
        session.close()


def main():
    # Dummy-Daten für Test, hier nur valide Felder verwenden!

    person_with_contacts_insert = {
        "title": "Herr",
        "first_name": "Max",
        "last_name": "Mustermann",
        "comment": "Testperson",
        "image_url": None,
        "contacts": [
            {
                "email": "max.mustermann@example.com",
                "phone": None,
                "fax": None,
                "comment": None
            }
        ]
    }
    person_with_contacts_update = {
        "comment": "Geänderte Testperson",
        "title": "Dr."
    }

    abteilung_insert = {
        "name": "IT"
        # hier nur Felder, die sicher existieren
    }
    abteilung_update = {
        "name": "IT-Abteilung"
    }

    person_to_abteilung_insert = {
        "person_id": 1,
        "abteilung_id": 1
    }
    person_to_abteilung_update = {}

    building_insert = {
        "name": "Hauptgebäude",
        "address": "Musterstraße 1"
    }
    building_update = {
        "address": "Neue Musterstraße 2"
    }

    room_insert = {
        "building_id": 1,
        "name": "Konferenzraum 1"
        # keine 'capacity', falls nicht definiert
    }
    room_update = {}

    person_to_room_insert = {
        "person_id": 1,
        "room_id": 1
    }
    person_to_room_update = {}

    transponder_insert = {
        "serial_number": "SN-123456",   # richtiges Feld
        "comment": "Erster Transponder",
        "issuer_id": None,
        "owner_id": None,
        "got_date": None,
        "return_date": None
    }
    transponder_update = {
        "comment": "Geänderter Kommentar"
    }

    transponder_update = {
        "comment": "Geändert"
    }

    transponder_to_room_insert = {
        "transponder_id": 1,
        "room_id": 1
    }
    transponder_to_room_update = {}

    test_handler(PersonWithContactHandler, person_with_contacts_insert, person_with_contacts_update, "PersonWithContactHandler")
    test_handler(AbteilungHandler, abteilung_insert, abteilung_update, "AbteilungHandler")
    test_handler(PersonToAbteilungHandler, person_to_abteilung_insert, person_to_abteilung_update, "PersonToAbteilungHandler")
    test_handler(BuildingHandler, building_insert, building_update, "BuildingHandler")
    test_handler(RoomHandler, room_insert, room_update, "RoomHandler")
    test_handler(PersonToRoomHandler, person_to_room_insert, person_to_room_update, "PersonToRoomHandler")
    test_handler(TransponderHandler, transponder_insert, transponder_update, "TransponderHandler")
    test_handler(TransponderToRoomHandler, transponder_to_room_insert, transponder_to_room_update, "TransponderToRoomHandler")


if __name__ == "__main__":
    main()
