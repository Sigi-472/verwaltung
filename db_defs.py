from sqlalchemy import (create_engine, Column, Integer, String, Text, ForeignKey, Date, Float, TIMESTAMP)
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import declarative_base, relationship, Session, class_mapper, RelationshipProperty, aliased, joinedload

Base = declarative_base()

class Person(Base):
    __tablename__ = "person"
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    first_name = Column(Text)
    last_name = Column(Text)
    created_at = Column(TIMESTAMP)
    comment = Column(Text)
    image_url = Column(Text)

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
    got_date = Column(Date)
    return_date = Column("return_date", Date)
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
    got_date = Column(Date)
    return_date = Column("return_date", Date)
    serial_number = Column(Text)
    kostenstelle_id = Column(Integer, ForeignKey("kostenstelle.id", ondelete="SET NULL"))
    anlagennummer = Column(Text)
    comment = Column(Text)
    price = Column(Float)
    raum_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"))
    professorship_id = Column(Integer, ForeignKey("professorship.id", ondelete="SET NULL"))
    abteilung_id = Column(Integer, ForeignKey("abteilung.id", ondelete="SET NULL"))

    owner = relationship("Person", foreign_keys=[owner_id], lazy="joined")
    issuer = relationship("Person", foreign_keys=[issuer_id], lazy="joined")
    object = relationship("Object", lazy="joined")
    kostenstelle = relationship("Kostenstelle", lazy="joined")
    abteilung = relationship("Abteilung", lazy="joined")
    professorship = relationship("Professorship", lazy="joined")
    room = relationship("Room", foreign_keys=[raum_id], lazy="joined")

