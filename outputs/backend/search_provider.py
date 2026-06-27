import json
import os
import urllib.error
import urllib.parse
import urllib.request


class SearchProvider:
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY", "").strip()
        self.endpoint = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str) -> list:
        if not self.api_key or not query.strip():
            return []

        params = urllib.parse.urlencode(
            {
                "q": query,
                "count": 10,
                "safesearch": "moderate",
            }
        )
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "X-Subscription-Token": self.api_key,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []

        results = []
        for item in payload.get("web", {}).get("results", []):
            url = item.get("url", "").strip()
            if not url:
                continue
            results.append(
                {
                    "title": item.get("title", "").strip(),
                    "url": url,
                    "snippet": item.get("description", "").strip(),
                    "source": "Brave Search",
                    "confidence": "high",
                }
            )
        return results
