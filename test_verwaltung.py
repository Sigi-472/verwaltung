# test_verwaltung.py

import traceback
import unittest
import os
import sys
import tempfile
import verwaltung
from pprint import pprint

def dier(row):
    print("\n===== DEBUG OUTPUT =====")
    if row is None:
        print("Ergebnis ist None")
    elif hasattr(row, "keys"):
        pprint(dict(row))
    else:
        pprint(row)

    print("\n===== STACKTRACE =====")
    traceback.print_stack(limit=5)
    print("========================")

class TestVerwaltungDatabase(unittest.TestCase):

    def setUp(self) -> None:
        self.db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.db_file.name
        self.conn = verwaltung.connect_to_db(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        os.unlink(self.db_path)

    def test_insert_update_delete_person(self):
        person_id = verwaltung.insert_person("Alice", "Anderson", "Test Person", conn=self.conn)
        self.assertIsInstance(person_id, int)

        verwaltung.update_person(person_id, first_names="Alicia", conn=self.conn)

        cur = self.conn.cursor()
        cur.execute("SELECT first_names FROM person WHERE id = ?", (person_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row, f"Kein Eintrag mit id={person_id} gefunden!")
        self.assertEqual(row["first_names"], "Alicia")

        verwaltung.delete_person(person_id, conn=self.conn)
        cur.execute("SELECT * FROM person WHERE id = ?", (person_id,))
        row = cur.fetchone()
        self.assertIsNone(row)

    def test_insert_update_delete_abteilung(self):
        leader_id = verwaltung.insert_person("Bob", "Boss", "Leiter", conn=self.conn)
        self.assertIsInstance(leader_id, int)

        abteilung_id = verwaltung.insert_abteilung("IT", leader_id, conn=self.conn)
        self.assertIsInstance(abteilung_id, int)

        verwaltung.update_abteilung(abteilung_id, name="Informatik", conn=self.conn)

        cur = self.conn.cursor()
        cur.execute("SELECT name FROM abteilung WHERE id = ?", (abteilung_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row, f"Abteilung mit id={abteilung_id} nicht gefunden!")
        self.assertEqual(row["name"], "Informatik")

        verwaltung.delete_abteilung(abteilung_id, conn=self.conn)
        cur.execute("SELECT * FROM abteilung WHERE id = ?", (abteilung_id,))
        res = cur.fetchone()
        self.assertIsNone(res)

    def test_assign_and_remove_person_to_abteilung(self):
        person_id = verwaltung.insert_person("Charlie", "Clerk", None, conn=self.conn)
        abteilung_id = verwaltung.insert_abteilung("HR", None, conn=self.conn)

        assignment_id = verwaltung.assign_person_to_abteilung(person_id, abteilung_id, conn=self.conn)
        self.assertIsInstance(assignment_id, int, "assignment_id sollte ein Integer sein")

        cur = self.conn.cursor()
        cur.execute("SELECT * FROM person_to_abteilung WHERE id = ?", (assignment_id,))
        row = cur.fetchone()

        self.assertIsNotNone(row, f"Kein Eintrag mit id={assignment_id} in person_to_abteilung gefunden")

        verwaltung.remove_person_from_abteilung(assignment_id, conn=self.conn)
        cur.execute("SELECT * FROM person_to_abteilung WHERE id = ?", (assignment_id,))
        self.assertIsNone(cur.fetchone(), "Eintrag wurde nicht entfernt")

    def test_abteilung_null_leiter(self):
        abteilung_id = verwaltung.insert_abteilung("Forschung", None, conn=self.conn)
        self.assertIsInstance(abteilung_id, int)

        cur = self.conn.cursor()
        cur.execute("SELECT abteilungsleiter_id FROM abteilung WHERE id = ?", (abteilung_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row, f"Abteilung mit id={abteilung_id} nicht gefunden!")
        self.assertIsNone(row["abteilungsleiter_id"])

    def test_update_person_no_fields(self):
        person_id = verwaltung.insert_person("Dummy", "Test", "Should remain", conn=self.conn)
        verwaltung.update_person(person_id, conn=self.conn)  # sollte nichts ändern, aber auch keinen Fehler werfen

        cur = self.conn.cursor()
        cur.execute("SELECT comment FROM person WHERE id = ?", (person_id,))
        row = cur.fetchone()

        self.assertIsNotNone(row, f"Kein Eintrag mit id={person_id} gefunden!")
        self.assertEqual(row["comment"], "Should remain")

    def test_update_abteilung_no_fields(self):
        abteilung_id = verwaltung.insert_abteilung("Vertrieb", None, self.conn)
        self.assertIsInstance(abteilung_id, int, "insert_abteilung sollte eine gültige ID zurückgeben")

        verwaltung.update_abteilung(abteilung_id, conn=self.conn)  # sollte nichts tun, aber auch nichts löschen

        cur = self.conn.cursor()
        cur.execute("SELECT name FROM abteilung WHERE id = ?", (abteilung_id,))
        row = cur.fetchone()

        self.assertIsNotNone(row, f"Abteilung mit id={abteilung_id} nicht gefunden!")
        self.assertEqual(row["name"], "Vertrieb")

if __name__ == '__main__':
    unittest.main()
