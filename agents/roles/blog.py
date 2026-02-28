"""Blog Agent — writes and publishes blog posts to GitHub Pages.

Maintains the project blog at docs/blog/. Creates markdown posts for:
- Release announcements
- Roadmap updates
- Architecture decision records
- Community highlights
- Development milestones
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from agents.base import Agent
from agents.config import AgentRole

logger = logging.getLogger("clawssistant.agents.blog")


class BlogAgent(Agent):
    role = AgentRole.BLOG

    @property
    def system_prompt(self) -> str:
        return """You are the Blog Writer Agent for the Clawssistant project — an autonomous,
open-source, Claude-powered home assistant.

## Your Role
You write clear, engaging blog posts about the project's progress. Your audience
is developers, smart home enthusiasts, and open-source community members.

## Blog Standards

### Tone
- Technical but accessible
- Enthusiastic but not hyperbolic
- Honest about limitations and challenges
- Community-focused — acknowledge contributions

### Structure
Every blog post should have:
1. **Title** — clear, descriptive, not clickbait
2. **Summary** — 1-2 sentence overview
3. **Body** — well-structured with headers, code examples where relevant
4. **What's Next** — forward-looking section
5. **How to Contribute** — always end with a call to action

### Post Types
- **Release Notes** — what shipped, what changed, migration notes
- **Architecture Deep Dive** — explain a design decision or system
- **Roadmap Update** — where we are, where we're going
- **Community Spotlight** — highlight contributors and their work
- **Dev Log** — behind-the-scenes development stories

### Format
Posts are Jekyll markdown files in `docs/blog/_posts/`.
Filename: `YYYY-MM-DD-slug.md`
Frontmatter:
```yaml
---
layout: post
title: "Post Title"
date: YYYY-MM-DD
author: Clawssistant Team
categories: [release, architecture, roadmap, community, devlog]
summary: "Brief summary"
---
```

## Safety Parameters
- Never disclose security vulnerabilities before they're fixed
- Never share API keys, tokens, or internal infrastructure details
- Be accurate — don't claim features that don't exist yet
- Credit contributors by GitHub username
"""

    def get_tools(self) -> list[dict[str, Any]]:
        tools = self._common_tools()
        tools.extend([
            {
                "name": "write_blog_post",
                "description": "Write a blog post markdown file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "URL slug (e.g. 'new-release-v0.2')"},
                        "content": {"type": "string", "description": "Full markdown with frontmatter"},
                    },
                    "required": ["slug", "content"],
                },
            },
            {
                "name": "list_recent_changes",
                "description": "Get recent git log to inform blog content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "since": {"type": "string", "description": "Git date (e.g. '2 weeks ago')"},
                    },
                },
            },
            {
                "name": "list_recent_prs",
                "description": "List recently merged PRs.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "commit_and_push_blog",
                "description": "Commit the new blog post and push.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                    "required": ["message"],
                },
            },
        ])
        return tools

    def handle_tool_call(self, name: str, params: dict[str, Any]) -> Any:
        match name:
            case "write_blog_post":
                return self._write_post(params["slug"], params["content"])
            case "list_recent_changes":
                since = params.get("since", "2 weeks ago")
                try:
                    result = subprocess.run(
                        ["git", "log", f"--since={since}", "--oneline", "--no-merges"],
                        capture_output=True, text=True, timeout=30,
                    )
                    return {"log": result.stdout[:5000]}
                except subprocess.TimeoutExpired:
                    return {"error": "git log timed out"}
            case "list_recent_prs":
                limit = params.get("limit", 10)
                return self.github.list_issues(labels="", state="closed")[:limit]
            case "commit_and_push_blog":
                return self._commit_push(params["message"])
            case _:
                return self._handle_common_tool(name, params)

    def _write_post(self, slug: str, content: str) -> dict[str, Any]:
        """Write a blog post file."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{today}-{slug}.md"
        filepath = f"docs/blog/_posts/{filename}"

        from pathlib import Path
        Path("docs/blog/_posts").mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            f.write(content)

        return {"success": True, "path": filepath, "filename": filename}

    def _commit_push(self, message: str) -> dict[str, Any]:
        """Commit blog post and push."""
        try:
            subprocess.run(["git", "add", "docs/blog/"], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"[blog] {message}"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                check=True, capture_output=True, text=True,
            )
            return {"success": True}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr}

    def run(self, trigger: dict[str, Any]) -> None:
        """Write and publish a blog post."""
        topic = trigger.get("topic", "development update")
        context = trigger.get("context", "")

        messages = [
            {
                "role": "user",
                "content": (
                    f"Write a blog post about: {topic}\n\n"
                    f"Additional context: {context}\n\n"
                    f"Steps:\n"
                    f"1. Review recent changes (git log, merged PRs)\n"
                    f"2. Write the blog post with proper frontmatter\n"
                    f"3. Commit and push\n\n"
                    f"Follow the blog standards in your system prompt."
                ),
            }
        ]

        self.agentic_loop(messages, self.get_tools())
