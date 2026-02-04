"""Generate shareable MD content from concept snapshots."""

from datetime import datetime
from typing import Optional


def generate_concept_md(
    concept_name: str,
    concept_description: Optional[str],
    snapshot: dict,
    recent_changes: list[dict],
) -> str:
    """Generate a shareable MD file from a concept snapshot.

    Args:
        concept_name: Name of the concept
        concept_description: Optional description
        snapshot: Current snapshot data
        recent_changes: List of recent snapshots (for showing change history)

    Returns:
        Markdown content string
    """
    timestamp = snapshot.get("timestamp", datetime.utcnow().isoformat() + "Z")
    version = snapshot.get("version", 1)
    summary = snapshot.get("summary", "")
    graph = snapshot.get("graph", {})
    additions = snapshot.get("additions", {})
    content_drafts = snapshot.get("content_drafts", {})
    sources = snapshot.get("sources", [])

    node_count = len(graph.get("nodes", []))
    edge_count = len(graph.get("edges", []))
    sources_count = len(sources)

    # Build MD content
    lines = [
        f"# {concept_name}",
        "",
    ]

    if concept_description:
        lines.extend([f"> {concept_description}", ""])

    lines.extend([
        f"**Updated:** {timestamp[:10]} | **Version:** #{version} | **Nodes:** {node_count} | **Edges:** {edge_count} | **Sources:** {sources_count}",
        "",
        "---",
        "",
        "## Summary",
        "",
        summary or "_No summary available_",
        "",
    ])

    # Recent changes section (from multiple snapshots)
    if recent_changes:
        lines.extend(["## Recent Changes", ""])
        for change_snapshot in recent_changes[:5]:
            change_ts = change_snapshot.get("timestamp", "")[:10]
            changes = change_snapshot.get("changes_from_previous", [])
            additions_data = change_snapshot.get("additions", {})

            if changes or additions_data:
                lines.append(f"### {change_ts}")

                # Show what was added
                added_nodes = additions_data.get("nodes", [])
                if added_nodes:
                    node_names = [n.get("label", n.get("id", "?")) for n in added_nodes[:5]]
                    if len(added_nodes) > 5:
                        node_names.append(f"...+{len(added_nodes) - 5} more")
                    lines.append(f"- **New nodes:** {', '.join(node_names)}")

                # Show change descriptions
                for change in changes[:5]:
                    lines.append(f"- {change}")

                lines.append("")

    # Content drafts section
    if content_drafts:
        lines.extend(["---", "", "## Content Drafts", ""])

        if content_drafts.get("reasoning"):
            lines.extend([f"_{content_drafts['reasoning']}_", ""])

        # X/Twitter post
        if content_drafts.get("x_post"):
            x = content_drafts["x_post"]
            lines.extend(["### X/Twitter", "", "```"])
            lines.append(x.get("text", ""))
            if x.get("thread"):
                for i, tweet in enumerate(x["thread"], 2):
                    lines.append(f"\n---{i}/---\n{tweet}")
            lines.extend(["```", ""])
            if x.get("hashtags"):
                lines.append(f"Tags: {' '.join('#' + t for t in x['hashtags'])}")
                lines.append("")

        # Short video script
        if content_drafts.get("short_video"):
            v = content_drafts["short_video"]
            lines.extend([
                "### Short Video Script",
                "",
                f"**Hook:** {v.get('hook', '')}",
                "",
                "**Script:**",
                v.get("script", ""),
                "",
            ])
            if v.get("visual_suggestions"):
                lines.append("**Visuals:**")
                for sug in v["visual_suggestions"]:
                    lines.append(f"- {sug}")
                lines.append("")

        # Medium article outline
        if content_drafts.get("medium_article"):
            m = content_drafts["medium_article"]
            lines.extend([
                "### Article Outline",
                "",
                f"**{m.get('title', 'Untitled')}**",
                "",
                f"_{m.get('subtitle', '')}_",
                "",
            ])
            for section in m.get("outline", []):
                lines.append(f"#### {section.get('section', 'Section')}")
                for point in section.get("points", []):
                    lines.append(f"- {point}")
                lines.append("")
            if m.get("conclusion"):
                lines.extend([
                    "#### Conclusion",
                    m["conclusion"],
                    "",
                ])
            if m.get("estimated_read_time"):
                lines.append(f"_Estimated read time: {m['estimated_read_time']}_")
                lines.append("")

    # Sources section
    if sources:
        lines.extend(["---", "", "## Sources", ""])
        for i, src in enumerate(sources[:20], 1):
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            lines.append(f"{i}. [{title}]({url})")
        if len(sources) > 20:
            lines.append(f"_...and {len(sources) - 20} more sources_")
        lines.append("")

    # Footer
    lines.extend([
        "---",
        "",
        f"_Generated by [loader.land](https://loader.land) Loader Tracker_",
    ])

    return "\n".join(lines)
