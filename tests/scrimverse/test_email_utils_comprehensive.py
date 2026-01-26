from unittest.mock import patch

import pytest

from scrimverse.email_utils import (
    send_password_reset_email,
    send_player_tournament_reminder_email,
    send_tournament_created_email,
    send_tournament_registration_email,
    send_verification_email,
    send_welcome_email,
)


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_welcome_email(mock_send):
    mock_send.return_value = True
    result = send_welcome_email("test@example.com", "testuser", "http://dashboard.com", "player")
    assert result is True
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert kwargs["subject"] == "Welcome to the Arena, testuser! You’re officially in."
    assert kwargs["template_name"] == "welcome"


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_verification_email(mock_send):
    mock_send.return_value = True
    result = send_verification_email("test@example.com", "testuser", "http://verify.com")
    assert result is True
    mock_send.assert_called_once()


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_password_reset_email(mock_send):
    mock_send.return_value = True
    result = send_password_reset_email("test@example.com", "testuser", "http://reset.com")
    assert result is True
    mock_send.assert_called_once()


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_tournament_registration_email(mock_send):
    mock_send.return_value = True
    result = send_tournament_registration_email(
        "test@example.com", "testuser", "My Tournament", "BGMI", "2024-01-01", "REG123", "http://tournament.com"
    )
    assert result is True
    mock_send.assert_called_once()


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_player_tournament_reminder_email(mock_send):
    mock_send.return_value = True
    result = send_player_tournament_reminder_email(
        "test@example.com", "testuser", "My Tournament", "BGMI", "10:00 AM", "1 hour", "http://tournament.com"
    )
    assert result is True
    mock_send.assert_called_once()


@pytest.mark.django_db
@patch("scrimverse.email_utils.EmailService.send_email")
def test_send_tournament_created_email(mock_send):
    mock_send.return_value = True
    result = send_tournament_created_email(
        "host@example.com",
        "hostname",
        "My Tournament",
        "BGMI",
        "2024-01-01",
        100,
        "basic",
        "http://tourn.com",
        "http://manage.com",
    )
    assert result is True
    mock_send.assert_called_once()
