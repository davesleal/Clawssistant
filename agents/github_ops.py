"""GitHub API operations — unified interface for all agent-GitHub interactions.

Uses the `gh` CLI and REST API via httpx for operations that agents need:
issues, PRs, labels, discussions, deployments, and project board management.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger("clawssistant.agents.github")


class GitHubOps:
    """All GitHub operations agents need, backed by `gh` CLI."""

    def __init__(self, token: str, repo: str) -> None:
        self.token = token
        self.repo = repo  # "owner/repo"
        self._env = {**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token}

    # ------------------------------------------------------------------
    # Internal: run gh commands
    # ------------------------------------------------------------------

    def _gh(self, *args: str, input_data: str | None = None) -> dict[str, Any] | list | str:
        """Run a `gh` CLI command and return parsed JSON or raw output."""
        cmd = ["gh"] + list(args)
        if self.repo and "--repo" not in args and "-R" not in args:
            cmd.extend(["--repo", self.repo])

        logger.debug("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=self._env,
            input=input_data,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error("gh failed: %s", result.stderr)
            return {"error": result.stderr.strip()}

        output = result.stdout.strip()
        if not output:
            return {"success": True}

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    def _api(self, method: str, endpoint: str, data: dict | None = None) -> Any:
        """Call the GitHub REST API via `gh api`."""
        args = ["api", endpoint, "--method", method]
        if data:
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    args.extend(["-f", f"{key}={json.dumps(value)}"])
                elif isinstance(value, bool):
                    args.extend(["-f", f"{key}={'true' if value else 'false'}"])
                else:
                    args.extend(["-f", f"{key}={value}"])
        return self._gh(*args)

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def get_issue(self, number: int) -> dict[str, Any]:
        """Get issue details including comments."""
        issue = self._gh("issue", "view", str(number), "--json",
                         "number,title,body,state,labels,assignees,comments,author,createdAt")
        return issue if isinstance(issue, dict) else {"error": "unexpected response"}

    def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> dict[str, Any]:
        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        result = self._gh(*args)
        # gh issue create returns the URL as plain text
        if isinstance(result, str):
            return {"url": result, "success": True}
        return result if isinstance(result, dict) else {"success": True}

    def comment_on_issue(self, number: int, body: str) -> dict[str, Any]:
        result = self._gh("issue", "comment", str(number), "--body", body)
        return result if isinstance(result, dict) else {"success": True}

    def close_issue(self, number: int, reason: str = "completed") -> dict[str, Any]:
        args = ["issue", "close", str(number)]
        if reason == "not_planned":
            args.append("--reason=not planned")
        result = self._gh(*args)
        return result if isinstance(result, dict) else {"success": True}

    def reopen_issue(self, number: int) -> dict[str, Any]:
        result = self._gh("issue", "reopen", str(number))
        return result if isinstance(result, dict) else {"success": True}

    def add_labels(self, number: int, labels: list[str]) -> dict[str, Any]:
        args = ["issue", "edit", str(number)]
        for label in labels:
            args.extend(["--add-label", label])
        result = self._gh(*args)
        return result if isinstance(result, dict) else {"success": True}

    def remove_labels(self, number: int, labels: list[str]) -> dict[str, Any]:
        args = ["issue", "edit", str(number)]
        for label in labels:
            args.extend(["--remove-label", label])
        result = self._gh(*args)
        return result if isinstance(result, dict) else {"success": True}

    def list_issues(
        self,
        labels: str | None = None,
        state: str = "open",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        args = ["issue", "list", "--json",
                "number,title,state,labels,assignees,createdAt,updatedAt",
                "--state", state, "--limit", str(limit)]
        if labels:
            args.extend(["--label", labels])
        result = self._gh(*args)
        return result if isinstance(result, list) else []

    def assign_issue(self, number: int, assignee: str) -> dict[str, Any]:
        result = self._gh("issue", "edit", str(number), "--add-assignee", assignee)
        return result if isinstance(result, dict) else {"success": True}

    # ------------------------------------------------------------------
    # Pull Requests
    # ------------------------------------------------------------------

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        args = ["pr", "create", "--title", title, "--body", body,
                "--head", head, "--base", base]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        result = self._gh(*args)
        if isinstance(result, str):
            return {"url": result, "success": True}
        return result if isinstance(result, dict) else {"success": True}

    def get_pr(self, number: int) -> dict[str, Any]:
        result = self._gh("pr", "view", str(number), "--json",
                          "number,title,body,state,files,reviews,comments,"
                          "additions,deletions,headRefName,baseRefName,mergeable")
        return result if isinstance(result, dict) else {"error": "unexpected response"}

    def review_pr(self, number: int, event: str, body: str) -> dict[str, Any]:
        """Review a PR. event: 'approve', 'request-changes', 'comment'."""
        args = ["pr", "review", str(number), f"--{event}", "--body", body]
        result = self._gh(*args)
        return result if isinstance(result, dict) else {"success": True}

    def merge_pr(self, number: int, method: str = "squash") -> dict[str, Any]:
        result = self._gh("pr", "merge", str(number), f"--{method}", "--auto")
        return result if isinstance(result, dict) else {"success": True}

    def get_pr_diff(self, number: int) -> str:
        result = self._gh("pr", "diff", str(number))
        return result if isinstance(result, str) else ""

    # ------------------------------------------------------------------
    # Discussions
    # ------------------------------------------------------------------

    def get_discussion(self, number: int) -> dict[str, Any]:
        """Get a discussion via GraphQL API."""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            discussion(number: $number) {
              id
              number
              title
              body
              author { login }
              comments(first: 50) {
                nodes {
                  id
                  body
                  author { login }
                  createdAt
                }
              }
              labels(first: 10) {
                nodes { name }
              }
            }
          }
        }
        """
        owner, repo = self.repo.split("/")
        result = self._gh(
            "api", "graphql",
            "-f", f"query={query}",
            "-f", f"owner={owner}",
            "-f", f"repo={repo}",
            "-F", f"number={number}",
        )
        if isinstance(result, dict) and "data" in result:
            return result["data"]["repository"]["discussion"]
        return result if isinstance(result, dict) else {}

    def reply_to_discussion(self, discussion_id: str, body: str) -> dict[str, Any]:
        """Reply to a discussion via GraphQL mutation."""
        mutation = """
        mutation($discussionId: ID!, $body: String!) {
          addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
            comment { id }
          }
        }
        """
        result = self._gh(
            "api", "graphql",
            "-f", f"query={mutation}",
            "-f", f"discussionId={discussion_id}",
            "-f", f"body={body}",
        )
        return result if isinstance(result, dict) else {"success": True}

    # ------------------------------------------------------------------
    # Labels (ensure they exist)
    # ------------------------------------------------------------------

    def ensure_labels(self, labels: dict[str, str]) -> None:
        """Create labels if they don't exist. labels = {name: color}."""
        for name, color in labels.items():
            self._gh("label", "create", name, "--color", color, "--force")

    # ------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------

    def create_deployment(self, ref: str, environment: str = "production") -> dict[str, Any]:
        result = self._api(
            "POST",
            f"/repos/{self.repo}/deployments",
            {"ref": ref, "environment": environment, "auto_merge": "false"},
        )
        return result if isinstance(result, dict) else {}

    def update_deployment_status(
        self, deployment_id: int, state: str, description: str = ""
    ) -> dict[str, Any]:
        result = self._api(
            "POST",
            f"/repos/{self.repo}/deployments/{deployment_id}/statuses",
            {"state": state, "description": description},
        )
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Git operations (for engineer agents)
    # ------------------------------------------------------------------

    def create_branch(self, branch_name: str, base: str = "main") -> dict[str, Any]:
        """Create a branch via the API."""
        # Get base ref SHA
        ref = self._api("GET", f"/repos/{self.repo}/git/ref/heads/{base}")
        if isinstance(ref, dict) and "object" in ref:
            sha = ref["object"]["sha"]
            result = self._api(
                "POST",
                f"/repos/{self.repo}/git/refs",
                {"ref": f"refs/heads/{branch_name}", "sha": sha},
            )
            return result if isinstance(result, dict) else {"success": True}
        return {"error": "Could not get base ref"}

    # ------------------------------------------------------------------
    # Workflow dispatch (for orchestrator to trigger other agents)
    # ------------------------------------------------------------------

    def dispatch_workflow(
        self, workflow: str, ref: str = "main", inputs: dict[str, str] | None = None
    ) -> dict[str, Any]:
        args = ["workflow", "run", workflow, "--ref", ref]
        if inputs:
            for key, value in inputs.items():
                args.extend(["-f", f"{key}={value}"])
        result = self._gh(*args)
        return result if isinstance(result, dict) else {"success": True}
