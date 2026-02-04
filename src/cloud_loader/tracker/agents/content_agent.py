"""Content agent for generating content drafts from knowledge updates."""

import json

from anthropic import Anthropic
from openai import OpenAI

from cloud_loader.config import settings


CONTENT_ANALYSIS_PROMPT = """Analyze this knowledge update and determine which content formats are appropriate.

Concept: {concept_name}
Summary: {summary}
Changes: {changes}

Available formats:
- short_video: 60-second vertical video script (good for breaking news, surprising facts, quick explainers)
- x_post: Single tweet or thread (good for opinions, quick updates, engagement)
- medium_article: Long-form article (good for deep analysis, tutorials, thought leadership)

Return JSON with:
{{
  "suggested_formats": ["format1", "format2"],
  "reasoning": "why these formats fit this update"
}}
"""

SHORT_VIDEO_PROMPT = """Write a 60-second short video script about this topic.

Concept: {concept_name}
Summary: {summary}
Key points: {changes}

Format:
- Hook (first 3 seconds): Attention-grabbing opener
- Body (45 seconds): Main content, 3-4 key points
- CTA (10 seconds): Call to action

Return JSON:
{{
  "hook": "opening line",
  "script": "full script with timing notes",
  "duration": "60s",
  "visual_suggestions": ["suggestion 1", "suggestion 2"]
}}
"""

X_POST_PROMPT = """Write an X (Twitter) post or thread about this topic.

Concept: {concept_name}
Summary: {summary}
Key points: {changes}
Sources: {sources}

If a thread is better, provide multiple tweets. Include relevant hashtags.

Return JSON:
{{
  "text": "main tweet text (max 280 chars)",
  "thread": ["tweet 2", "tweet 3"] or null if single tweet is enough,
  "hashtags": ["tag1", "tag2"]
}}
"""

MEDIUM_PROMPT = """Write a Medium article outline about this topic.

Concept: {concept_name}
Summary: {summary}
Key points: {changes}
Sources: {sources}

Return JSON:
{{
  "title": "article title",
  "subtitle": "subtitle",
  "outline": [
    {{"section": "Introduction", "points": ["point 1", "point 2"]}},
    {{"section": "Section Name", "points": ["point 1", "point 2"]}}
  ],
  "conclusion": "conclusion summary",
  "estimated_read_time": "X min"
}}
"""


class ContentAgent:
    """Agent for generating content drafts."""

    def __init__(self):
        self.anthropic = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.openai = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def _call_llm(self, prompt: str, model: str = "claude-sonnet") -> str:
        if "claude" in model.lower() and self.anthropic:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        elif self.openai:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        return "{}"

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        return {}

    async def analyze_formats(
        self,
        concept_name: str,
        summary: str,
        changes: list[str],
        model: str = "claude-sonnet"
    ) -> dict:
        """Determine which content formats are appropriate."""
        prompt = CONTENT_ANALYSIS_PROMPT.format(
            concept_name=concept_name,
            summary=summary,
            changes=json.dumps(changes)
        )

        response = await self._call_llm(prompt, model)
        result = self._parse_json(response)

        return {
            "suggested_formats": result.get("suggested_formats", []),
            "reasoning": result.get("reasoning", "")
        }

    async def generate_short_video(
        self,
        concept_name: str,
        summary: str,
        changes: list[str],
        model: str = "claude-sonnet"
    ) -> dict:
        """Generate short video script."""
        prompt = SHORT_VIDEO_PROMPT.format(
            concept_name=concept_name,
            summary=summary,
            changes=json.dumps(changes)
        )

        response = await self._call_llm(prompt, model)
        return self._parse_json(response)

    async def generate_x_post(
        self,
        concept_name: str,
        summary: str,
        changes: list[str],
        sources: list[str],
        model: str = "claude-sonnet"
    ) -> dict:
        """Generate X/Twitter post or thread."""
        prompt = X_POST_PROMPT.format(
            concept_name=concept_name,
            summary=summary,
            changes=json.dumps(changes),
            sources=json.dumps(sources[:5])
        )

        response = await self._call_llm(prompt, model)
        return self._parse_json(response)

    async def generate_medium_article(
        self,
        concept_name: str,
        summary: str,
        changes: list[str],
        sources: list[str],
        model: str = "claude-sonnet"
    ) -> dict:
        """Generate Medium article outline."""
        prompt = MEDIUM_PROMPT.format(
            concept_name=concept_name,
            summary=summary,
            changes=json.dumps(changes),
            sources=json.dumps(sources[:10])
        )

        response = await self._call_llm(prompt, model)
        return self._parse_json(response)

    async def generate_drafts(
        self,
        concept_name: str,
        summary: str,
        changes: list[str],
        sources: list[str],
        model: str = "claude-sonnet"
    ) -> dict:
        """Generate content drafts for suggested formats."""
        analysis = await self.analyze_formats(concept_name, summary, changes, model)
        suggested = analysis.get("suggested_formats", [])

        drafts = {
            "suggested_formats": suggested,
            "reasoning": analysis.get("reasoning", "")
        }

        if "short_video" in suggested:
            drafts["short_video"] = await self.generate_short_video(
                concept_name, summary, changes, model
            )

        if "x_post" in suggested:
            drafts["x_post"] = await self.generate_x_post(
                concept_name, summary, changes, sources, model
            )

        if "medium_article" in suggested:
            drafts["medium_article"] = await self.generate_medium_article(
                concept_name, summary, changes, sources, model
            )

        return drafts


# Singleton
content_agent = ContentAgent()
