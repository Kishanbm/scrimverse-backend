import pytest
from rest_framework import status
from rest_framework.test import APIClient

from payments.models import Payment
from tests.factories import UserFactory


@pytest.fixture
def auth_client():
    user = UserFactory(user_type="player")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
def test_list_payments(auth_client):
    """Test authenticated user can list their payments"""
    client, user = auth_client
    Payment.objects.create(
        user=user,
        amount=100.0,
        amount_paisa=10000,
        payment_type="entry_fee",
        status="SUCCESS",
        merchant_order_id="ORD1",
    )
    Payment.objects.create(
        user=user,
        amount=200.0,
        amount_paisa=20000,
        payment_type="tournament_plan",
        status="PENDING",
        merchant_order_id="ORD2",
    )

    response = client.get("/api/payments/list/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_initiate_payment_missing_params(auth_client):
    """Test initiate payment fails with missing parameters"""
    client, user = auth_client
    data = {"payment_type": "tournament_plan"}  # Missing tournament_id

    response = client.post("/api/payments/initiate/", data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_check_payment_status_missing_id(auth_client):
    """Test check status fails with missing order ID"""
    client, user = auth_client
    data = {}

    response = client.post("/api/payments/status/", data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_unauthenticated_cannot_list_payments():
    """Test unauthenticated user cannot list payments"""
    client = APIClient()
    response = client.get("/api/payments/list/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
