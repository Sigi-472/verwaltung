import datetime
from typing import Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import select
from db_defs import (
    Person, PersonContact, Abteilung, PersonToAbteilung,
    Building, Room, PersonToRoom, Transponder, TransponderToRoom
)


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

