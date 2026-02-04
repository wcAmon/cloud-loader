"""Graph agent for building knowledge graphs from search results."""

import json
from typing import Optional

from anthropic import Anthropic
from openai import OpenAI

from cloud_loader.config import settings


GRAPH_EXTRACTION_PROMPT = """You are a knowledge graph builder. Given search results about a concept, extract entities and relationships.

Concept: {concept_name}
Description: {concept_description}

Previous graph state (if any):
{previous_graph}

New search results:
{search_results}

Extract a knowledge graph with:
1. Nodes: People, organizations, events, concepts, dates
2. Edges: Relationships between nodes

For each node, include:
- id: unique identifier (e.g., "person_powell", "org_fed")
- type: person | organization | event | concept | date | location
- label: display name
- properties: relevant attributes

For each edge, include:
- source: source node id
- target: target node id
- type: relationship type (e.g., "member_of", "announced", "affects")
- label: human-readable description

IMPORTANT:
- If updating an existing graph, identify what's NEW or CHANGED
- Don't repeat information that's already in the previous graph unchanged
- Focus on progress and developments, not static facts

Return ONLY valid JSON in this format:
{{
  "nodes": [...],
  "edges": [...],
  "changes_from_previous": ["description of change 1", "description of change 2"]
}}
"""

SUMMARY_PROMPT = """Based on this knowledge graph and search results about "{concept_name}", write a concise summary (2-3 paragraphs) focusing on:
1. What's the current state/progress of this concept?
2. What changed recently?
3. What are the key implications?

Knowledge graph:
{graph}

Search results:
{search_results}

Write in the same language as the concept name. Be factual and cite sources where relevant.
"""


class GraphAgent:
    """Agent for building and updating knowledge graphs."""

    def __init__(self):
        self.anthropic = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.openai = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def build_graph(
        self,
        concept_name: str,
        concept_description: str,
        search_results: list[dict],
        previous_graph: Optional[dict] = None,
        model: str = "claude-sonnet"
    ) -> dict:
        """Build or update knowledge graph from search results."""

        results_text = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
            for r in search_results[:10]
        ])

        prev_graph_text = json.dumps(previous_graph, indent=2) if previous_graph else "None (first run)"

        prompt = GRAPH_EXTRACTION_PROMPT.format(
            concept_name=concept_name,
            concept_description=concept_description,
            previous_graph=prev_graph_text,
            search_results=results_text
        )

        if "claude" in model.lower() and self.anthropic:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        elif self.openai:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
        else:
            return {"nodes": [], "edges": [], "changes_from_previous": ["No AI model configured"]}

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                graph = json.loads(content[start:end])
                return graph
        except json.JSONDecodeError:
            pass

        return {"nodes": [], "edges": [], "changes_from_previous": ["Failed to parse graph"]}

    async def generate_summary(
        self,
        concept_name: str,
        graph: dict,
        search_results: list[dict],
        model: str = "claude-sonnet"
    ) -> str:
        """Generate a summary based on the graph and search results."""

        results_text = "\n".join([
            f"- {r['title']}: {r['url']}"
            for r in search_results[:10]
        ])

        prompt = SUMMARY_PROMPT.format(
            concept_name=concept_name,
            graph=json.dumps(graph, indent=2),
            search_results=results_text
        )

        if "claude" in model.lower() and self.anthropic:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        elif self.openai:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        return "No summary available - AI model not configured"


# Singleton
graph_agent = GraphAgent()
