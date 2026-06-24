import requests
from pathlib import Path
from urllib.parse import urlparse
import mimetypes


def download_images(
    urls,
    folder,
    prefix,
    log=print,
):

    Path(folder).mkdir(
        parents=True,
        exist_ok=True
    )

    downloaded = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    for i, url in enumerate(urls, 1):

        try:

            # Fix protocol-relative URLs
            if url.startswith("//"):
                url = "https:" + url

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                stream=True,
            )

            response.raise_for_status()

            # Try to determine extension
            parsed = urlparse(url)
            ext = Path(parsed.path).suffix.lower()

            if not ext or len(ext) > 5:

                content_type = response.headers.get(
                    "Content-Type",
                    ""
                )

                ext = mimetypes.guess_extension(
                    content_type.split(";")[0]
                ) or ".jpg"

            file_path = (
                Path(folder)
                / f"{prefix}_{str(i).zfill(2)}{ext}"
            )

            with open(file_path, "wb") as f:

                for chunk in response.iter_content(8192):

                    if chunk:
                        f.write(chunk)

            downloaded.append(str(file_path))

            log(f"DOWNLOADED -> {file_path}")

        except Exception as e:

            log(f"FAILED -> {url}")
            log(e)

    return downloaded