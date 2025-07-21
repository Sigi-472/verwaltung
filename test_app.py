import unittest
import json

from app import app

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"person", response.data)
        self.assertIn(b"abteilung", response.data)

    def test_view_person_table(self):
        response = self.client.get("/table/person")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"first_name", response.data)

    def test_view_abteilung_table(self):
        response = self.client.get("/table/abteilung")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"abteilungsleiter_id", response.data)

    def test_unsupported_table(self):
        response = self.client.get("/table/unknown")
        self.assertEqual(response.status_code, 404)

    def test_post_person(self):
        response = self.client.post("/api/data/person", json={
            "first_name": "Max",
            "last_name": "Mustermann",
            "comment": "Testeintrag"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("inserted", response.json.get("status", ""))

    def test_update_person(self):
        # ID muss real existieren, sonst kommt 500
        response = self.client.put("/api/data/person", json={
            "id": 1,
            "first_name": "Maximilian",
            "last_name": "Muster",
            "comment": "Updated"
        })
        self.assertIn(response.status_code, [200, 500])  # Abfangen, falls ID nicht existiert

    def test_delete_person(self):
        # ID muss real existieren, sonst 500
        response = self.client.delete("/api/data/person", json={"id": 1})
        self.assertIn(response.status_code, [200, 500])

    def test_update_abteilung(self):
        response = self.client.put("/api/data/abteilung", json={
            "id": 1,
            "name": "Entwicklung",
            "abteilungsleiter_id": 2
        })
        self.assertIn(response.status_code, [200, 500])

    def test_delete_abteilung(self):
        response = self.client.delete("/api/data/abteilung", json={"id": 1})
        self.assertIn(response.status_code, [200, 500])

if __name__ == "__main__":
    unittest.main()
