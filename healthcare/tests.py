from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PatientDoctorMapping


class HealthcareAPITests(APITestCase):
    PASSWORD = "Test@12345"

    def register_and_login(self, email="a@test.com", name="Alice"):
        r = self.client.post(
            "/api/auth/register/",
            {"name": name, "email": email, "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        r = self.client.post(
            "/api/auth/login/", {"email": email, "password": self.PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertIn("access", r.data)
        return r.data["access"]

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ---- auth ----
    def test_register_duplicate_and_weak_password(self):
        self.register_and_login()
        r = self.client.post(
            "/api/auth/register/",
            {"name": "X", "email": "a@test.com", "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.post(
            "/api/auth/register/",
            {"name": "X", "email": "b@test.com", "password": "12345678"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_login_wrong_password(self):
        self.register_and_login()
        r = self.client.post(
            "/api/auth/login/", {"email": "a@test.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_endpoints_require_token(self):
        for url in ["/api/patients/", "/api/doctors/", "/api/mappings/"]:
            self.assertEqual(self.client.get(url).status_code, 401)

    # ---- patients ----
    def test_patient_crud_and_isolation(self):
        t1 = self.register_and_login("a@test.com")
        t2 = self.register_and_login("b@test.com", "Bob")

        self.auth(t1)
        r = self.client.post(
            "/api/patients/", {"name": "Ravi", "age": 35, "gender": "M"}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data["id"]

        self.assertEqual(len(self.client.get("/api/patients/").data), 1)
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").status_code, 200)

        r = self.client.put(
            f"/api/patients/{pid}/",
            {"name": "Ravi K", "age": 36, "gender": "M"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["name"], "Ravi K")

        # validation
        r = self.client.post(
            "/api/patients/", {"name": "Bad", "age": 500, "gender": "M"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

        # doosre user ko nahi dikhna chahiye
        self.auth(t2)
        self.assertEqual(len(self.client.get("/api/patients/").data), 0)
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/patients/{pid}/").status_code, 404)

        self.auth(t1)
        self.assertEqual(self.client.delete(f"/api/patients/{pid}/").status_code, 204)

    # ---- doctors ----
    def test_doctor_crud_and_ownership(self):
        t1 = self.register_and_login("a@test.com")
        t2 = self.register_and_login("b@test.com", "Bob")

        self.auth(t1)
        r = self.client.post(
            "/api/doctors/",
            {"name": "Sharma", "specialization": "Cardiology", "email": "dr@test.com",
             "experience_years": 10},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        did = r.data["id"]

        # duplicate doctor email
        r = self.client.post(
            "/api/doctors/",
            {"name": "Other", "specialization": "ENT", "email": "dr@test.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

        # doosra user dekh sakta hai par edit/delete nahi
        self.auth(t2)
        self.assertEqual(len(self.client.get("/api/doctors/").data), 1)
        self.assertEqual(self.client.get(f"/api/doctors/{did}/").status_code, 200)
        r = self.client.put(
            f"/api/doctors/{did}/",
            {"name": "Hacked", "specialization": "X", "email": "dr@test.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.delete(f"/api/doctors/{did}/").status_code, 403)

        self.auth(t1)
        r = self.client.put(
            f"/api/doctors/{did}/",
            {"name": "Sharma J", "specialization": "Cardiology", "email": "dr@test.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/doctors/{did}/").status_code, 204)

    # ---- mappings ----
    def test_mapping_flow(self):
        t1 = self.register_and_login("a@test.com")
        t2 = self.register_and_login("b@test.com", "Bob")

        self.auth(t1)
        pid = self.client.post(
            "/api/patients/", {"name": "Ravi", "age": 35, "gender": "M"}, format="json"
        ).data["id"]
        d1 = self.client.post(
            "/api/doctors/",
            {"name": "Sharma", "specialization": "Cardiology", "email": "d1@test.com"},
            format="json",
        ).data["id"]
        d2 = self.client.post(
            "/api/doctors/",
            {"name": "Gupta", "specialization": "Neuro", "email": "d2@test.com"},
            format="json",
        ).data["id"]

        r = self.client.post("/api/mappings/", {"patient": pid, "doctor": d1}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        mid = r.data["id"]
        self.assertEqual(
            self.client.post(
                "/api/mappings/", {"patient": pid, "doctor": d2}, format="json"
            ).status_code,
            201,
        )

        # duplicate mapping
        r = self.client.post("/api/mappings/", {"patient": pid, "doctor": d1}, format="json")
        self.assertEqual(r.status_code, 400)

        self.assertEqual(len(self.client.get("/api/mappings/").data), 2)

        r = self.client.get(f"/api/mappings/{pid}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["doctors"]), 2)

        # doosra user kisi aur ke patient pe assign nahi kar sakta
        self.auth(t2)
        r = self.client.post("/api/mappings/", {"patient": pid, "doctor": d1}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.get(f"/api/mappings/{pid}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mappings/{mid}/").status_code, 404)

        self.auth(t1)
        self.assertEqual(self.client.delete(f"/api/mappings/{mid}/").status_code, 204)
        self.assertEqual(PatientDoctorMapping.objects.count(), 1)
        self.assertEqual(self.client.delete(f"/api/mappings/{mid}/").status_code, 404)
