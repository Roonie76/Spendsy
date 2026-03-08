from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .integrated_parser import ParsedTransaction, ParserResponse
from .models import ApiAuditLog, TaxProfile, Transaction


class FinanceApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            password="strong-password",
            email="tester@example.com",
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_add_transaction_requires_auth(self):
        self.client.credentials()
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "Coffee",
            "amount": "199.50",
            "type": "expense",
            "category": "food",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_transaction_rejects_invalid_type(self):
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "Bad Type",
            "amount": "1200",
            "type": "transfer",
            "category": "other",
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data.get("ok"))
        self.assertEqual(res.data.get("code"), "INVALID_TRANSACTION_TYPE")

    def test_add_transaction_rejects_invalid_amount(self):
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "Bad Amount",
            "amount": "abc",
            "type": "expense",
            "category": "other",
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data.get("ok"))
        self.assertEqual(res.data.get("code"), "INVALID_AMOUNT")

    def test_add_transaction_requires_explicit_type(self):
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "No Type",
            "amount": "1200",
            "category": "other",
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data.get("ok"))
        self.assertEqual(res.data.get("code"), "INVALID_TRANSACTION_TYPE")

    def test_add_transaction_success(self):
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "Coffee",
            "amount": "199.50",
            "type": "expense",
            "category": "food",
            "is_recurring": False,
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data.get("ok"))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_add_transaction_creates_audit_log(self):
        url = reverse("add_transaction")
        payload = {
            "user_id": self.user.id,
            "title": "Audit Check",
            "amount": "100.00",
            "type": "expense",
            "category": "food",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ApiAuditLog.objects.filter(action="transaction_created", user=self.user).exists())

    def test_financial_summary_is_correct_for_income_and_expense(self):
        Transaction.objects.create(
            user=self.user,
            title="Salary",
            amount="1000.00",
            type="income",
            category="salary",
            is_recurring=False,
        )
        Transaction.objects.create(
            user=self.user,
            title="Groceries",
            amount="250.00",
            type="expense",
            category="food",
            is_recurring=False,
        )
        res = self.client.get(reverse("financial_summary"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        payload = res.data.get("data", {})
        self.assertEqual(payload.get("income"), 1000.0)
        self.assertEqual(payload.get("expense"), 250.0)
        self.assertEqual(payload.get("balance"), 750.0)

    def test_manage_tax_profile_post_returns_saved_profile(self):
        url = reverse("manage_tax_profile", kwargs={"user_id": self.user.id})
        payload = {
            "annualRent": 120000,
            "annualEPF": 30000,
            "isBusiness": True,
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("ok"))
        self.assertIn("annualRent", res.data["data"])
        self.assertEqual(res.data["data"]["annualRent"], 120000.0)
        self.assertEqual(res.data["data"]["annualEPF"], 30000.0)
        self.assertTrue(res.data["data"]["isBusiness"])

        profile = TaxProfile.objects.get(user=self.user)
        self.assertEqual(float(profile.annual_rent), 120000.0)
        self.assertEqual(float(profile.annual_epf), 30000.0)
        self.assertTrue(profile.is_business)

    def test_profile_access_ignores_path_user_id_and_scopes_to_request_user(self):
        other = User.objects.create_user(
            username="other",
            password="strong-password",
            email="other@example.com",
        )
        url = reverse("profile_settings", kwargs={"user_id": other.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("ok"))
        self.assertEqual(res.data.get("data", {}).get("username"), self.user.username)

    def test_add_transaction_ignores_payload_user_id_and_scopes_to_request_user(self):
        other = User.objects.create_user(
            username="other2",
            password="strong-password",
            email="other2@example.com",
        )
        url = reverse("add_transaction")
        payload = {
            "user_id": other.id,
            "title": "Scoped Insert",
            "amount": "100.00",
            "type": "income",
            "category": "salary",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        tx = Transaction.objects.get(title="Scoped Insert")
        self.assertEqual(tx.user_id, self.user.id)

    @patch("finance.views.AUTH_RATE_LIMIT_LOGIN", 2)
    def test_login_rate_limit_returns_429(self):
        self.client.credentials()
        url = reverse("login")
        bad_payload = {"username": self.user.username, "password": "wrong-password"}

        first = self.client.post(url, bad_payload, format="json")
        second = self.client.post(url, bad_payload, format="json")
        third = self.client.post(url, bad_payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(third.data.get("code"), "RATE_LIMITED")

    @patch("finance.views._integrated_parser.parse")
    def test_upload_statement_persists_transactions_and_returns_updated_summary(
        self, mocked_parse
    ):
        mocked_parse.return_value = ParserResponse(
            status="success",
            reconciliation_score=1.0,
            transactions=[
                ParsedTransaction(
                    date="2026-01-10",
                    description="Salary Credit",
                    amount=50000.0,
                    type="income",
                    balance=80000.0,
                    is_valid=True,
                ),
                ParsedTransaction(
                    date="2026-01-11",
                    description="Coffee",
                    amount=250.0,
                    type="expense",
                    balance=79750.0,
                    is_valid=True,
                ),
            ],
            meta={"method": "digital", "checksum_verified": True},
        )

        url = reverse("parse_statement_proxy")
        upload = SimpleUploadedFile("statement.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        res = self.client.post(url, {"file": upload}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("ok"))
        payload = res.data.get("data", {})
        self.assertEqual(payload.get("saved_count"), 2)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)
        self.assertEqual(payload.get("meta", {}).get("method"), "digital")
        self.assertEqual(payload.get("reconciliation_score"), 1.0)

        summary = payload.get("financial_summary", {})
        self.assertEqual(summary.get("income"), 50000.0)
        self.assertEqual(summary.get("expense"), 250.0)
        self.assertEqual(summary.get("balance"), 49750.0)

        summary_res = self.client.get(reverse("financial_summary"))
        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        summary_data = summary_res.data.get("data", {})
        self.assertEqual(summary_data.get("income"), 50000.0)
        self.assertEqual(summary_data.get("expense"), 250.0)
        self.assertEqual(summary_data.get("balance"), 49750.0)

        upload_again = SimpleUploadedFile("statement.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        second = self.client.post(url, {"file": upload_again}, format="multipart")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        second_payload = second.data.get("data", {})
        self.assertEqual(second_payload.get("saved_count"), 0)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)
