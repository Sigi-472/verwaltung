PRAGMA foreign_keys = ON;

CREATE TABLE person (
  id INTEGER PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  created_at TIMESTAMP,
  comment TEXT
);

CREATE TABLE abteilung (
  id INTEGER PRIMARY KEY,
  name TEXT,
  abteilungsleiter_id INTEGER,
  FOREIGN KEY (abteilungsleiter_id) REFERENCES person(id) ON DELETE SET NULL
);

CREATE TABLE person_to_abteilung (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,
  abteilung_id INTEGER,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
  FOREIGN KEY (abteilung_id) REFERENCES abteilung(id) ON DELETE CASCADE
);

CREATE TABLE kostenstelle (
  id INTEGER PRIMARY KEY,
  name TEXT
);

CREATE TABLE professorship (
  id INTEGER PRIMARY KEY,
  kostenstelle_id INTEGER,
  name TEXT,
  FOREIGN KEY (kostenstelle_id) REFERENCES kostenstelle(id) ON DELETE SET NULL
);

CREATE TABLE professorship_to_person (
  id INTEGER PRIMARY KEY,
  professorship_id INTEGER,
  person_id INTEGER,
  FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE CASCADE,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
);

CREATE TABLE person_contact (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,
  phone TEXT,
  fax TEXT,
  email TEXT,
  comment TEXT,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
);

CREATE TABLE building (
  id INTEGER PRIMARY KEY,
  name TEXT,
  building_number TEXT,
  address TEXT
);

CREATE TABLE room (
  id INTEGER PRIMARY KEY,
  building_id INTEGER,
  name TEXT,
  floor INTEGER,
  FOREIGN KEY (building_id) REFERENCES building(id) ON DELETE SET NULL
);

CREATE TABLE person_to_room (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,
  room_id INTEGER,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

CREATE TABLE transponder (
  id INTEGER PRIMARY KEY,
  issuer_id INTEGER,
  owner_id INTEGER,
  got DATE,
  return DATE,
  serial_number TEXT,
  comment TEXT,
  FOREIGN KEY (issuer_id) REFERENCES person(id) ON DELETE SET NULL,
  FOREIGN KEY (owner_id) REFERENCES person(id) ON DELETE SET NULL
);

CREATE TABLE transponder_to_room (
  id INTEGER PRIMARY KEY,
  transponder_id INTEGER,
  room_id INTEGER,
  FOREIGN KEY (transponder_id) REFERENCES transponder(id) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

CREATE TABLE object_category (
  id INTEGER PRIMARY KEY,
  name TEXT
);

CREATE TABLE object (
  id INTEGER PRIMARY KEY,
  name TEXT,
  price REAL,
  category_id INTEGER,
  FOREIGN KEY (category_id) REFERENCES object_category(id) ON DELETE SET NULL
);

CREATE TABLE lager (
  id INTEGER PRIMARY KEY,
  raum_id INTEGER,
  FOREIGN KEY (raum_id) REFERENCES room(id) ON DELETE SET NULL
);

CREATE TABLE object_to_lager (
  id INTEGER PRIMARY KEY,
  object_id INTEGER,
  lager_id INTEGER,
  FOREIGN KEY (object_id) REFERENCES object(id) ON DELETE CASCADE,
  FOREIGN KEY (lager_id) REFERENCES lager(id) ON DELETE CASCADE
);

CREATE TABLE inventory (
  id INTEGER PRIMARY KEY,
  owner_id INTEGER,
  object_id INTEGER,
  issuer_id INTEGER,
  acquisition_date DATE,
  got DATE,
  return DATE,
  serial_number TEXT,
  kostenstelle_id INTEGER,
  anlagennummer TEXT,
  comment TEXT,
  price REAL,
  raum_id INTEGER,
  professorship_id INTEGER,
  abteilung_id INTEGER,
  FOREIGN KEY (owner_id) REFERENCES person(id) ON DELETE SET NULL,
  FOREIGN KEY (issuer_id) REFERENCES person(id) ON DELETE SET NULL,
  FOREIGN KEY (object_id) REFERENCES object(id) ON DELETE SET NULL,
  FOREIGN KEY (kostenstelle_id) REFERENCES kostenstelle(id) ON DELETE SET NULL,
  FOREIGN KEY (raum_id) REFERENCES room(id) ON DELETE SET NULL,
  FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE SET NULL,
  FOREIGN KEY (abteilung_id) REFERENCES abteilung(id) ON DELETE SET NULL
);

CREATE TABLE person_to_professorship (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,
  professorship_id INTEGER,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE,
  FOREIGN KEY (professorship_id) REFERENCES professorship(id) ON DELETE CASCADE
);
