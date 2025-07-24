import datetime
from typing import Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import select
from db_defs import (
    Person, PersonContact, Abteilung, PersonToAbteilung,
    Building, Room, PersonToRoom, Transponder, TransponderToRoom
)
from sqlalchemy.exc import IntegrityError

class AbstractDBHandler:
    def __init__(self, session: Session, model: Type):
        self.session = session
        self.model = model

    def get_row(self, id: int) -> Optional[Any]:
        return self.session.get(self.model, id)

    def get_id(self, data: Dict[str, Any]) -> Optional[int]:
        query = select(self.model)
        for k, v in data.items():
            if v is not None:
                query = query.where(getattr(self.model, k) == v)
        result = self.session.execute(query).scalars().first()
        if result:
            return result.id
        return None

    def insert_into_db(self, data: Dict[str, Any]) -> int:
        id_ = self.get_id(data)
        if id_ is not None:
            return id_

        row = self.model(**data)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row.id

    def set_column(self, id_: int, column: str, value: Any) -> bool:
        row = self.get_row(id_)
        if row is None or not hasattr(row, column):
            return False
        setattr(row, column, value)
        self.session.commit()
        return True

    def set_row(self, id_: int, new_values: Dict[str, Any]) -> bool:
        row = self.get_row(id_)
        if row is None:
            return False
        for k, v in new_values.items():
            if hasattr(row, k):
                setattr(row, k, v)
        self.session.commit()
        return True


# Spezifische Klassen

class PersonHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, Person)

    def insert_person(self, data: Dict[str, Any]) -> int:
        if "created_at" not in data:
            data["created_at"] = datetime.datetime.utcnow()
        return self.insert_into_db(data)


class PersonContactHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, PersonContact)


class AbteilungHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, Abteilung)


class PersonToAbteilungHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, PersonToAbteilung)


class BuildingHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, Building)


class RoomHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, Room)


class PersonToRoomHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, PersonToRoom)


class TransponderHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, Transponder)


class TransponderToRoomHandler(AbstractDBHandler):
    def __init__(self, session: Session):
        super().__init__(session, TransponderToRoom)


class PersonWithContactHandler:
    def __init__(self, session: Session):
        self.session = session

    def _get_row_by_values(self, model, data: Dict[str, Any]) -> Optional[Any]:
        query = select(model)
        for k, v in data.items():
            if v is not None:
                query = query.where(getattr(model, k) == v)
        result = self.session.execute(query).scalars().first()
        return result

    def _safe_insert(self, model, data: Dict[str, Any]) -> int:
        existing_row = self._get_row_by_values(model, data)
        if existing_row is not None:
            return existing_row.id

        row = model(**data)
        self.session.add(row)
        try:
            self.session.commit()
            self.session.refresh(row)
            return row.id
        except IntegrityError as e:
            self.session.rollback()
            existing_row = self._get_row_by_values(model, data)
            if existing_row is not None:
                return existing_row.id
            raise e

    def insert_person_with_contacts(self, person_data: dict, contacts: list) -> int | None:
        # 1. Prüfe, ob Person schon existiert (title, first_name, last_name)
        stmt = select(Person).where(
            Person.title == person_data.get("title"),
            Person.first_name == person_data.get("first_name"),
            Person.last_name == person_data.get("last_name")
        )
        existing_person = self.session.execute(stmt).scalars().first()
        if existing_person:
            # Wenn Person schon existiert, gib ihre ID zurück
            print(f"ℹ️ Person existiert bereits mit ID {existing_person.id}")
            return existing_person.id

        # 2. Person anlegen
        new_person = Person(
            title=person_data.get("title"),
            first_name=person_data.get("first_name"),
            last_name=person_data.get("last_name"),
            created_at=person_data.get("created_at") or datetime.utcnow(),
            comment=person_data.get("comment"),
            image_url=person_data.get("image_url")
        )

        # 3. Kontakte anlegen (optional)
        if contacts:
            for c in contacts:
                contact = PersonContact(
                    phone=c.get("phone"),
                    fax=c.get("fax"),
                    email=c.get("email"),
                    comment=c.get("comment"),
                    person=new_person
                )
                self.session.add(contact)

        # 4. Insert versuchen, Fehler abfangen
        self.session.add(new_person)
        try:
            self.session.commit()
            return new_person.id
        except IntegrityError as e:
            self.session.rollback()
            print(f"❌ IntegrityError beim Insert: {e}")
            return None
        
    def update_person(self, person_id: int, new_values: Dict[str, Any]) -> bool:
        person = self.session.get(Person, person_id)
        if person is None:
            return False
        for k, v in new_values.items():
            if hasattr(person, k):
                setattr(person, k, v)
        self.session.commit()
        return True

    def update_person_column(self, person_id: int, column: str, value: Any) -> bool:
        person = self.session.get(Person, person_id)
        if person is None or not hasattr(person, column):
            return False

        # Vorherige Werte extrahieren
        new_title = person.title
        new_first_name = person.first_name
        new_last_name = person.last_name

        if column == "title":
            new_title = value
        elif column == "first_name":
            new_first_name = value
        elif column == "last_name":
            new_last_name = value

        # Prüfe, ob diese Kombination (title, first_name, last_name) schon existiert (aber andere ID!)
        stmt = select(Person).where(
            Person.id != person_id,
            Person.title == new_title,
            Person.first_name == new_first_name,
            Person.last_name == new_last_name
        )
        existing = self.session.execute(stmt).scalars().first()
        if existing:
            print(f"❌ Abgelehnt: Person mit (title={new_title}, first_name={new_first_name}, last_name={new_last_name}) existiert bereits (ID={existing.id})")
            return False

        # Keine Kollision → setzen & committen
        setattr(person, column, value)
        try:
            self.session.commit()
            return True
        except IntegrityError as e:
            self.session.rollback()
            print(f"❌ IntegrityError beim Commit: {e}")
            return False
