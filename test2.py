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


def test_handler(handler_class, test_data_insert, test_update_data, name: str):
    print(f"\nTeste {name}...")

    session = Session()
    try:
        handler = handler_class(session)

        # Insert
        inserted_id = None
        try:
            inserted_id = handler.insert_data(test_data_insert)
            print(f"-> Eintrag eingefügt mit ID: {inserted_id}")
        except Exception as e:
            print(f"Fehler beim Einfügen: {e}")

        # Update (falls Insert erfolgreich)
        if inserted_id is not None:
            try:
                success = handler.update_by_id(inserted_id, test_update_data)
                print(f"-> Update erfolgreich: {success}")
            except Exception as e:
                print(f"Fehler beim Update: {e}")

    finally:
        session.close()


def main():
    # Testdaten für alle Handler (bitte an dein Schema anpassen!)

    test_person_contact_insert = {
        "title": "Herr",
        "first_name": "Max",
        "last_name": "Mustermann",
        "comment": "Testperson",
        "image_url": None,
    }
    test_person_contact_update = {
        "comment": "Geänderte Testperson",
        "title": "Dr."
    }

    test_abteilung_insert = {
        "name": "IT-Abteilung",
        "beschreibung": "Verwaltet IT Systeme"
    }
    test_abteilung_update = {
        "beschreibung": "Geänderte Beschreibung"
    }

    test_p_to_a_insert = {
        "person_id": 1,  # Dummy ID, ggf. anpassen!
        "abteilung_id": 1
    }
    test_p_to_a_update = {
        # z.B. nur Kommentar, wenn Feld vorhanden
        # hier kein Beispiel, ggf. leer lassen
    }

    test_building_insert = {
        "name": "Hauptgebäude",
        "address": "Musterstraße 1"
    }
    test_building_update = {
        "address": "Geänderte Adresse 2"
    }

    test_room_insert = {
        "building_id": 1,
        "name": "Konferenzraum 101",
        "capacity": 20
    }
    test_room_update = {
        "capacity": 25
    }

    test_p_to_room_insert = {
        "person_id": 1,
        "room_id": 1
    }
    test_p_to_room_update = {
        # ggf. keine Felder zum updaten
    }

    test_transponder_insert = {
        "transponder_id": "TR-123456",
        "comment": "Testtransponder"
    }
    test_transponder_update = {
        "comment": "Geänderter Kommentar"
    }

    test_t_to_room_insert = {
        "transponder_id": 1,
        "room_id": 1
    }
    test_t_to_room_update = {
        # ggf. leer
    }

    # Tests ausführen

    test_handler(PersonWithContactHandler, test_person_contact_insert, test_person_contact_update, "PersonWithContactHandler")
    test_handler(AbteilungHandler, test_abteilung_insert, test_abteilung_update, "AbteilungHandler")
    test_handler(PersonToAbteilungHandler, test_p_to_a_insert, test_p_to_a_update, "PersonToAbteilungHandler")
    test_handler(BuildingHandler, test_building_insert, test_building_update, "BuildingHandler")
    test_handler(RoomHandler, test_room_insert, test_room_update, "RoomHandler")
    test_handler(PersonToRoomHandler, test_p_to_room_insert, test_p_to_room_update, "PersonToRoomHandler")
    test_handler(TransponderHandler, test_transponder_insert, test_transponder_update, "TransponderHandler")
    test_handler(TransponderToRoomHandler, test_t_to_room_insert, test_t_to_room_update, "TransponderToRoomHandler")


if __name__ == "__main__":
    main()
