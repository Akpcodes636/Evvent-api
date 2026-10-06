import asyncio
from typing import BinaryIO

import cloudinary
import cloudinary.uploader


async def upload_image(
    file: BinaryIO,
    *,
    folder: str,
) -> str:

    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file,
        folder=folder,
        resource_type="image",
    )

    return result["secure_url"]