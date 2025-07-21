from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Person, Abteilung, PersonToAbteilung
from datetime import datetime

engine = create_engine("sqlite:///db.sqlite3")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Beispielpersonen
p1 = Person(first_name="Anna", last_name="Müller", created_at=datetime.now(), comment="Teamleiterin")
p2 = Person(first_name="Bernd", last_name="Schulz", created_at=datetime.now(), comment="Neu dabei")
p3 = Person(first_name="Carla", last_name="Meier", created_at=datetime.now(), comment="Erfahren")

session.add_all([p1, p2, p3])
session.flush()

# Abteilungen
a1 = Abteilung(name="Vertrieb", abteilungsleiter_id=p1.id)
a2 = Abteilung(name="Support", abteilungsleiter_id=p3.id)
session.add_all([a1, a2])
session.flush()

# Zuweisungen
z1 = PersonToAbteilung(person_id=p2.id, abteilung_id=a1.id)
session.add(z1)

session.commit()
