"""
Test cases for Payment Gateway Integration
Tests cover:
- Payment initiation for tournaments
- Payment verification/status check
- Payment history
- PhonePe callback handling
"""
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from payments.models import Payment, Refund
from tests.factories import HostProfileFactory, PlayerProfileFactory, TournamentFactory, TournamentRegistrationFactory


@pytest.mark.django_db
@patch("payments.views.phonepe_service.initiate_payment")
def test_initiate_tournament_payment(mock_initiate, api_client):
    """Test initiating payment for tournament registration (entry fee)"""
    mock_initiate.return_value = {
        "success": True,
        "merchant_order_id": "ORD_TEST123",
        "phonepe_order_id": "PH_ORDER_123",
        "redirect_url": "https://phonepe.com/pay/test",
        "state": "CREATED",
        "expire_at": 123456789,
    }

    player_profile = PlayerProfileFactory()
    tournament = TournamentFactory(entry_fee=299)
    # The view expects registration_id
    registration = TournamentRegistrationFactory(tournament=tournament, player=player_profile, payment_status=False)

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"payment_type": "entry_fee", "amount": 299.00, "registration_id": registration.id}

    response = client.post("/api/payments/initiate/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert "merchant_order_id" in response.data
    mock_initiate.assert_called_once()


@pytest.mark.django_db
@patch("payments.services.PhonePeService.get_order_status")
def test_verify_payment_success(mock_status, api_client):
    """Test successful payment status verification"""
    mock_status.return_value = {
        "success": True,
        "state": "COMPLETED",
        "amount": 29900,
        "payment_details": [{"transaction_id": "TXN_123", "payment_mode": "UPI", "instrument_type": "ACCOUNT"}],
    }

    player_profile = PlayerProfileFactory()
    tournament = TournamentFactory()
    registration = TournamentRegistrationFactory(tournament=tournament, player=player_profile)

    # Create a pending payment
    payment = Payment.objects.create(
        merchant_order_id="ORD_TEST123",
        user=player_profile.user,
        player_profile=player_profile,
        amount=299,
        payment_type="entry_fee",
        registration=registration,
        status="pending",
    )

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"merchant_order_id": "ORD_TEST123"}

    response = client.post("/api/payments/status/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    payment.refresh_from_db()
    assert payment.status == "completed"
    assert payment.phonepe_transaction_id == "TXN_123"


@pytest.mark.django_db
@patch("payments.services.PhonePeService.get_order_status")
def test_verify_payment_failure(mock_status, api_client):
    """Test payment status check with failure state"""
    mock_status.return_value = {
        "success": True,
        "state": "FAILED",
        "amount": 29900,
        "error_code": "PAYMENT_ERROR",
        "detailed_error_code": "INSUFFICIENT_FUNDS",
    }

    player_profile = PlayerProfileFactory()
    payment = Payment.objects.create(
        merchant_order_id="ORD_FAILED123",
        user=player_profile.user,
        amount=299,
        payment_type="entry_fee",
        status="pending",
    )

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    response = client.post("/api/payments/status/", {"merchant_order_id": "ORD_FAILED123"}, format="json")

    assert response.status_code == status.HTTP_200_OK
    payment.refresh_from_db()
    assert payment.status == "failed"
    assert payment.error_code == "PAYMENT_ERROR"


@pytest.mark.django_db
def test_payment_history(api_client):
    """Test retrieving payment history for a user"""
    player_profile = PlayerProfileFactory()

    # Create multiple payments
    Payment.objects.create(
        merchant_order_id="ORD_H1", user=player_profile.user, amount=299, payment_type="entry_fee", status="completed"
    )

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    response = client.get("/api/payments/list/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1


@pytest.mark.django_db
@patch("payments.services.PhonePeService.initiate_refund")
def test_refund_payment(mock_refund, api_client):
    """Test payment refund functionality"""
    mock_refund.return_value = {"success": True, "refund_id": "REF_123", "state": "COMPLETED", "amount": 29900}

    host_profile = HostProfileFactory()
    player_profile = PlayerProfileFactory()
    payment = Payment.objects.create(
        merchant_order_id="ORD_REFUND",
        user=player_profile.user,
        amount=299,
        payment_type="entry_fee",
        status="completed",
    )

    client = APIClient()
    # Host or Admin can initiate refunds
    client.force_authenticate(user=host_profile.user)

    data = {"payment_id": payment.id, "amount": 299.00, "reason": "Tournament cancelled"}

    # Correct endpoint is /api/payments/refund/initiate/
    response = client.post("/api/payments/refund/initiate/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert Refund.objects.filter(payment=payment).exists()
    mock_refund.assert_called_once()
