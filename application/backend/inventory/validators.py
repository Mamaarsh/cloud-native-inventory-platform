from pathlib import Path
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_PRODUCT_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
PRODUCT_IMAGE_EXTENSIONS = {
    "JPEG": frozenset({".jpg", ".jpeg"}),
    "PNG": frozenset({".png"}),
    "WEBP": frozenset({".webp"}),
}

def validate_product_image(uploaded_file):
    if uploaded_file.size > MAX_PRODUCT_IMAGE_SIZE:
        raise ValidationError("Image size must not exceed 5 MB.")
    try:
        original_position = uploaded_file.tell()
    except (AttributeError, OSError):
        original_position = 0
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image_format = image.format
            image.verify()
    except (OSError, SyntaxError, UnidentifiedImageError, ValueError) as exc:
        raise ValidationError(
            "Upload a valid JPEG, PNG, or WebP image."
        ) from exc
    finally:
        try:
            uploaded_file.seek(original_position)
        except (AttributeError, OSError):
            pass
    if image_format not in ALLOWED_PRODUCT_IMAGE_FORMATS:
        raise ValidationError(
            "Unsupported image format. Use JPEG, PNG, or WebP."
        )
    filename_extension = Path(uploaded_file.name).suffix.lower()
    if filename_extension not in PRODUCT_IMAGE_EXTENSIONS[image_format]:
        raise ValidationError(
            "Image filename extension does not match its content."
        )