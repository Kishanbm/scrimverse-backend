from django.core.exceptions import ValidationError


def validate_aadhar_image(image):
    """
    Validate Aadhar card image:
    - File size must be less than 5MB
    - Only image files are allowed (jpg, jpeg, png, webp)
    """
    # Check file size (5MB = 5 * 1024 * 1024 bytes)
    max_size = 5 * 1024 * 1024
    if image.size > max_size:
        raise ValidationError("Aadhar card image size must be less than 5MB.")

    # Check file extension
    allowed_extensions = ["jpg", "jpeg", "png", "webp"]
    ext = image.name.split(".")[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Only image files are allowed. Supported formats: {', '.join(allowed_extensions).upper()}")

    # Check MIME type
    allowed_mime_types = ["image/jpeg", "image/png", "image/webp"]
    if hasattr(image, "content_type") and image.content_type not in allowed_mime_types:
        raise ValidationError("Invalid image file type. Please upload a valid image.")

    return image
