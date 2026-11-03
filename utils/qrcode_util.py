"""QR code generation utilities."""
from __future__ import annotations

import base64
import io

import qrcode
from qrcode.image.pil import PilImage


def generate_qr_code_base64(data: str) -> str:
    """
    Generate a QR code from *data* and return the PNG as a base64-encoded string.
    Suitable for embedding directly in HTML email as a data URI.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color="#10324a", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")
