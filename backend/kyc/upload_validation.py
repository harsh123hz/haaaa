from pathlib import Path

from rest_framework import serializers


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def validate_kyc_upload(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError("File must be 5 MB or smaller.")

    extension = Path(uploaded_file.name or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError("Only PDF, JPG, and PNG files are accepted.")

    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    detected_type = _detect_type(header)
    if detected_type is None:
        raise serializers.ValidationError("Only valid PDF, JPG, and PNG files are accepted.")

    expected_type = ALLOWED_EXTENSIONS[extension]
    if detected_type != expected_type:
        raise serializers.ValidationError(
            f"File extension does not match file contents. Expected {expected_type}."
        )

    return uploaded_file


def _detect_type(header):
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None

