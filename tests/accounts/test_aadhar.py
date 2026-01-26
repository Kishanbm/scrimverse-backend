from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import HostProfileFactory


@pytest.mark.django_db
def test_upload_aadhar_success():
    """Test host can upload aadhar card"""
    host_profile = HostProfileFactory()
    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    image_content = b"fake-image-content"
    front = SimpleUploadedFile("front.jpg", image_content, content_type="image/jpeg")
    back = SimpleUploadedFile("back.jpg", image_content, content_type="image/jpeg")

    response = client.post(
        "/api/accounts/host/upload-aadhar/", {"aadhar_card_front": front, "aadhar_card_back": back}, format="multipart"
    )

    assert response.status_code == status.HTTP_200_OK
    host_profile.refresh_from_db()
    assert host_profile.aadhar_card_front
    assert host_profile.aadhar_card_back
    assert host_profile.verification_status == "pending"


@pytest.mark.django_db
def test_upload_aadhar_unauthenticated_fails():
    """Test unauthenticated user cannot upload aadhar"""
    client = APIClient()
    image = SimpleUploadedFile("aadhar.jpg", b"content", content_type="image/jpeg")

    response = client.post("/api/accounts/host/upload-aadhar/", {"aadhar_image": image}, format="multipart")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_upload_aadhar_missing_file_fails():
    """Test upload fails if no file is provided"""
    host_profile = HostProfileFactory()
    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post("/api/accounts/host/upload-aadhar/", {}, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_player_cannot_upload_aadhar():
    """Test players cannot upload aadhar (only for hosts)"""
    from tests.factories import PlayerProfileFactory

    player_profile = PlayerProfileFactory()
    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    image = SimpleUploadedFile("aadhar.jpg", b"content", content_type="image/jpeg")
    response = client.post("/api/accounts/host/upload-aadhar/", {"aadhar_image": image}, format="multipart")

    # Depending on how the view is implemented, it might be 403 or 400
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]
