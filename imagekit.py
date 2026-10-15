import httpx
from imagekitio import ImageKit

from config import get_settings

settings = get_settings()

imagekit = ImageKit(
    private_key=settings.imagekit_private_key.get_secret_value(),
)

IMAGEKIT_API_BASE = "https://api.imagekit.io/v1"


def get_upload_auth() -> dict[str, str | int]:
    return imagekit.helper.get_authentication_parameters()


async def get_file_details(file_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{IMAGEKIT_API_BASE}/files/{file_id}/details",
            auth=(
                settings.imagekit_private_key.get_secret_value(),
                "",
            ),
        )
        response.raise_for_status()
        return response.json()


async def delete_file(file_id: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(
            f"{IMAGEKIT_API_BASE}/files/{file_id}",
            auth=(
                settings.imagekit_private_key.get_secret_value(),
                "",
            ),
        )

        if response.status_code != 404:
            response.raise_for_status()
