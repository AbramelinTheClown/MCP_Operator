import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from .server import Tool

class NasaImagesTool(Tool):
    BASE_URL = "https://images-api.nasa.gov"
    
    def __init__(self):
        self.api_key = os.getenv("NASA_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _make_request(self, endpoint, params=None):
        try:
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            return {"error": str(e), "status_code": e.response.status_code}

    def search(self, q=None, media_type=None, year_start=None, year_end=None, page=1, page_size=100):
        params = {
            "q": q,
            "media_type": media_type,
            "year_start": year_start,
            "year_end": year_end,
            "page": page,
            "page_size": page_size
        }
        return self._make_request("/search", {k: v for k, v in params.items() if v is not None})

    def get_asset(self, nasa_id):
        return self._make_request(f"/asset/{nasa_id}")

    def get_metadata(self, nasa_id):
        return self._make_request(f"/metadata/{nasa_id}")

    def get_captions(self, nasa_id):
        return self._make_request(f"/captions/{nasa_id}")

    def get_album(self, album_name, page=1):
        return self._make_request(f"/album/{album_name}", {"page": page})