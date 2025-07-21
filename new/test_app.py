# test_app.py
import os
import sqlite3
import pytest
from db_ops import get_joined_data, update_row, insert_row, delete_row

join_views = {
    "person": {
        "base_table": "person",
        "base_alias": "p",
        "primary_key": "id",
        "columns": ["p.id AS id", "p.first_name", "p.last_name"],
        "writable_tables": {"person": "p"}
    }
}

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE person (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT)")
    conn.execute("INSERT INTO person (first_name, last_name) VALUES ('Max', 'Mustermann')")
    conn.commit()
    yield conn
    conn.close()

def test_get(db):
    data = get_joined_data(db, join_views["person"])
    assert data[0]["first_name"] == "Max"

def test_update(db):
    data = {"id": 1, "first_name": "Martha", "last_name": "Meier"}
    update_row(db, join_views["person"], data)
    cur = db.execute("SELECT first_name FROM person WHERE id=1")
    assert cur.fetchone()[0] == "Martha"

def test_insert_and_delete(db):
    insert_row(db, join_views["person"], {"first_name": "Alice", "last_name": "Test"})
    cur = db.execute("SELECT COUNT(*) FROM person")
    assert cur.fetchone()[0] == 2
    delete_row(db, join_views["person"], 2)
    cur = db.execute("SELECT COUNT(*) FROM person")
    assert cur.fetchone()[0] == 1
