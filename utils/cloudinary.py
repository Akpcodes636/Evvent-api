import asyncio
import io
import os
from typing import BinaryIO

from dotenv import load_dotenv
from PIL import Image, ImageOps

import cloudinary
import cloudinary.uploader


load_dotenv()


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


MAX_IMAGE_SIZE = 2000
JPEG_QUALITY = 90


def optimize_image(file: BinaryIO) -> io.BytesIO:
    """
    Resize and compress an uploaded image in memory.

    - Maximum width/height: 2000px
    - JPEG quality: 90
    - Preserves aspect ratio
    - Corrects phone-camera orientation
    """

    image = Image.open(file)

    # Correct EXIF orientation from phone/camera images
    image = ImageOps.exif_transpose(image)

    # Resize only if the image is larger than 2000px
    image.thumbnail(
        (MAX_IMAGE_SIZE, MAX_IMAGE_SIZE),
        Image.Resampling.LANCZOS,
    )

    # Convert to RGB because JPEG does not support transparency
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, "white")

        if image.mode == "P":
            image = image.convert("RGBA")

        if image.mode in ("RGBA", "LA"):
            background.paste(
                image,
                mask=image.getchannel("A"),
            )
            image = background
        else:
            image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=JPEG_QUALITY,
        optimize=True,
    )

    output.seek(0)

    return output


async def upload_image(
    file: BinaryIO,
    *,
    folder: str,
) -> str:

    optimized_image = await asyncio.to_thread(
        optimize_image,
        file,
    )

    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        optimized_image,
        folder=folder,
        resource_type="image",
        format="jpg",
    )

    return result["secure_url"]