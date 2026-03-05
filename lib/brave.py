"""
Shared Brave Search API client.

Usage:
    from lib.brave import brave_search

    results = brave_search("startup funding 2026")
    # Returns: [{"title": "...", "url": "...", "description": "..."}, ...]
"""

import sys
import requests

from lib.config import config

BRAVE_SEARCH_API_KEY = config.brave_search_api_key


def brave_search(query, count=5):
    """Search using Brave Search API.

    Args:
        query: Search query string.
        count: Number of results (default: 5).

    Returns:
        List of dicts with title, url, description. Empty list on failure.
    """
    if not BRAVE_SEARCH_API_KEY:
        return []
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_SEARCH_API_KEY},
            params={"q": query, "count": count},
            timeout=10
        )
        if response.status_code != 200:
            return []
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("description", "")}
            for r in response.json().get("web", {}).get("results", [])
        ]
    except Exception as e:
        print(f"  Search error: {e}", file=sys.stderr)
        return []
