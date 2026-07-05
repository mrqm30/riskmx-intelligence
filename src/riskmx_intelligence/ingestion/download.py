from pathlib import Path
import requests


def download_file(url: str, output_path: Path, chunk_size: int = 1024 * 1024) -> Path:
    """
    Download a file from a URL using streaming.

    This is safer for large files because it does not load the whole file into memor
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": "riskmx-intelligence/0.1.0"}

    with requests.get(url, stream=True, timeout=180, headers=headers) as response:
        response.raise_for_status()

        with output_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)

    return output_path
