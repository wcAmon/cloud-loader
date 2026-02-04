"""Orchestrator for running the full concept tracking pipeline."""

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from cloud_loader.models import Concept, ConceptSnapshot, ConceptRunStatus
from cloud_loader.tracker.services.snapshot_store import (
    save_snapshot,
    get_previous_snapshot,
    list_snapshots,
    get_snapshot,
)
from cloud_loader.tracker.services.md_generator import generate_concept_md
from cloud_loader.tracker.agents.search_agent import search_agent
from cloud_loader.tracker.agents.graph_agent import graph_agent
from cloud_loader.tracker.agents.content_agent import content_agent
from cloud_loader.services.template import create_md_storage


def merge_graphs(previous_graph: dict, new_graph: dict) -> tuple[dict, dict]:
    """Merge previous graph with new additions.

    Returns:
        (merged_graph, additions) - Full merged graph and what was added
    """
    prev_nodes = {n["id"]: n for n in previous_graph.get("nodes", [])}
    prev_edges = {(e["source"], e["target"], e.get("type", "")): e for e in previous_graph.get("edges", [])}

    new_nodes = new_graph.get("nodes", [])
    new_edges = new_graph.get("edges", [])

    # Track additions
    added_nodes = []
    added_edges = []

    # Merge nodes (update existing, add new)
    for node in new_nodes:
        node_id = node.get("id")
        if node_id:
            if node_id not in prev_nodes:
                added_nodes.append(node)
            prev_nodes[node_id] = node  # Update or add

    # Merge edges
    for edge in new_edges:
        edge_key = (edge.get("source"), edge.get("target"), edge.get("type", ""))
        if edge_key[0] and edge_key[1]:
            if edge_key not in prev_edges:
                added_edges.append(edge)
            prev_edges[edge_key] = edge  # Update or add

    merged = {
        "nodes": list(prev_nodes.values()),
        "edges": list(prev_edges.values())
    }

    additions = {
        "nodes": added_nodes,
        "edges": added_edges
    }

    return merged, additions


class Orchestrator:
    """Orchestrates the full search -> graph -> content pipeline."""

    async def run_concept(self, concept: Concept, session: Session) -> dict:
        """Run the full pipeline for a concept."""
        print(f"[Orchestrator] Running concept: {concept.name}")

        # Update run_status to running
        concept.run_status = ConceptRunStatus.RUNNING
        session.add(concept)
        session.commit()

        try:
            result = await self._execute_pipeline(concept, session)

            # Update run_status to ready
            concept.run_status = ConceptRunStatus.READY
            concept.last_searched_at = datetime.now(timezone.utc)
            concept.updated_at = datetime.now(timezone.utc)
            session.add(concept)
            session.commit()

            return result

        except Exception as e:
            print(f"[Orchestrator] Error: {e}")

            # Update run_status to failed
            concept.run_status = ConceptRunStatus.FAILED
            concept.updated_at = datetime.now(timezone.utc)
            session.add(concept)
            session.commit()

            return {"error": str(e), "success": False}

    async def _execute_pipeline(self, concept: Concept, session: Session) -> dict:
        """Execute the actual pipeline steps."""
        # Parse keywords from JSON string
        try:
            keywords = json.loads(concept.keywords) if concept.keywords else []
        except json.JSONDecodeError:
            keywords = []

        # 1. Search
        print("[Orchestrator] Searching...")
        search_results = await search_agent.search(
            query=concept.name,
            keywords=keywords,
            max_results=20
        )

        if not search_results:
            return {"error": "No search results found", "success": False}

        print(f"[Orchestrator] Found {len(search_results)} results")

        # 2. Get previous graph
        previous_snapshot = await get_previous_snapshot(concept.id)
        previous_graph = previous_snapshot.get("graph") if previous_snapshot else {"nodes": [], "edges": []}

        # 3. Build new graph (LLM extracts new knowledge)
        print("[Orchestrator] Building graph...")
        new_graph = await graph_agent.build_graph(
            concept_name=concept.name,
            concept_description=concept.description or "",
            search_results=search_results,
            previous_graph=previous_graph,
            model="claude-sonnet"
        )

        # 4. Explicit merge (don't rely on LLM)
        print("[Orchestrator] Merging graphs...")
        merged_graph, additions = merge_graphs(previous_graph, new_graph)
        changes_from_previous = new_graph.get("changes_from_previous", [])

        # 5. Generate summary
        print("[Orchestrator] Generating summary...")
        summary = await graph_agent.generate_summary(
            concept_name=concept.name,
            graph=merged_graph,
            search_results=search_results,
            model="claude-sonnet"
        )

        # 6. Generate content drafts
        print("[Orchestrator] Generating content drafts...")
        sources = [r["url"] for r in search_results]

        content_drafts = await content_agent.generate_drafts(
            concept_name=concept.name,
            summary=summary,
            changes=changes_from_previous,
            sources=sources,
            model="claude-sonnet"
        )

        # 7. Build snapshot data
        snapshot_data = {
            "graph": merged_graph,
            "additions": additions,
            "changes_from_previous": changes_from_previous,
            "summary": summary,
            "sources": [
                {"url": r["url"], "title": r["title"], "source": r.get("source", "unknown")}
                for r in search_results
            ],
            "content_drafts": content_drafts
        }

        # 8. Save snapshot
        print("[Orchestrator] Saving snapshot...")
        snapshot_path = await save_snapshot(concept.id, snapshot_data)

        # Re-read the saved snapshot (it has timestamp and version)
        saved_snapshot = await get_snapshot(concept.id, "latest")

        # 9. Generate MD for sharing
        print("[Orchestrator] Generating MD...")
        md_code = await self._generate_and_store_md(concept, saved_snapshot, session)

        # 10. Create snapshot record in database
        snapshot_record = ConceptSnapshot(
            concept_id=concept.id,
            snapshot_path=snapshot_path,
            node_count=len(merged_graph.get("nodes", [])),
            edge_count=len(merged_graph.get("edges", [])),
            sources_count=len(search_results),
            summary=summary[:2000] if summary else None,
            md_code=md_code
        )
        session.add(snapshot_record)
        session.commit()

        print(f"[Orchestrator] Done! Snapshot: {snapshot_path}, MD code: {md_code}")

        return {
            "success": True,
            "snapshot_path": snapshot_path,
            "md_code": md_code,
            "nodes_count": len(merged_graph.get("nodes", [])),
            "edges_count": len(merged_graph.get("edges", [])),
            "additions": {
                "nodes_count": len(additions.get("nodes", [])),
                "edges_count": len(additions.get("edges", []))
            },
            "sources_count": len(search_results)
        }

    async def _generate_and_store_md(
        self,
        concept: Concept,
        snapshot: dict,
        session: Session
    ) -> str:
        """Generate MD content and store in md-store."""
        # Get recent snapshots for change history
        recent_snapshots = []
        snapshot_list = await list_snapshots(concept.id)

        for snap_info in snapshot_list[:5]:
            ts = snap_info.get("timestamp")
            if ts:
                snap_data = await get_snapshot(concept.id, ts)
                if snap_data:
                    recent_snapshots.append(snap_data)

        # Generate MD content
        md_content = generate_concept_md(
            concept_name=concept.name,
            concept_description=concept.description,
            snapshot=snapshot,
            recent_changes=recent_snapshots
        )

        # Store in md-store
        md_storage = create_md_storage(
            session=session,
            content=md_content,
            filename=f"{concept.name}.md",
            purpose=f"Knowledge tracking snapshot for: {concept.name}",
            install_path="anywhere"
        )

        return md_storage.code


# Singleton
orchestrator = Orchestrator()
