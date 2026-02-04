"""Search agent for gathering information about concepts."""

from tavily import TavilyClient
from openai import OpenAI

from cloud_loader.config import settings


class SearchAgent:
    """Agent for searching web sources about concepts."""

    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None
        self.openai = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def search_tavily(self, query: str, max_results: int = 10) -> list[dict]:
        """Search using Tavily API."""
        if not self.tavily:
            return []

        try:
            response = self.tavily.search(
                query=query,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                    "source": "tavily"
                })

            return results
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []

    async def search(
        self,
        query: str,
        keywords: list[str],
        max_results: int = 20
    ) -> list[dict]:
        """Combined search from all sources."""
        full_query = f"{query} {' '.join(keywords)}"

        tavily_results = await self.search_tavily(full_query, max_results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []

        for result in tavily_results:
            url = result["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results[:max_results]


# Singleton instance
search_agent = SearchAgent()
