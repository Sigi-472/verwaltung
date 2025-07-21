from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Person(Base):
    __tablename__ = "person"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(TIMESTAMP)
    comment = Column(Text)

    geleitete_abteilungen = relationship("Abteilung", back_populates="leiter")
    abteilungen = relationship("PersonToAbteilung", back_populates="person")

class Abteilung(Base):
    __tablename__ = "abteilung"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abteilungsleiter_id = Column(Integer, ForeignKey("person.id", ondelete="SET NULL"))

    leiter = relationship("Person", back_populates="geleitete_abteilungen")
    personen = relationship("PersonToAbteilung", back_populates="abteilung")

class PersonToAbteilung(Base):
    __tablename__ = "person_to_abteilung"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("person.id", ondelete="CASCADE"))
    abteilung_id = Column(Integer, ForeignKey("abteilung.id", ondelete="CASCADE"))

    person = relationship("Person", back_populates="abteilungen")
    abteilung = relationship("Abteilung", back_populates="personen")
