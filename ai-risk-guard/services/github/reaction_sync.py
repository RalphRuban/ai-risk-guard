"""
services/github/reaction_sync.py

Harvest 🚀/👎 feedback on bot PR comments by polling the GitHub Reactions REST
API. GitHub has no ``reaction`` webhook event, so the learning loop polls
``GET /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions`` on an
interval instead.

Reaction content mapping:
  - ``rocket`` (🚀)  -> ACCEPTED (reviewer approved the patch)
  - ``-1``    (👎)  -> REJECTED (reviewer flagged a false positive)

A reaction is comment-level, so it attributes to every vulnerability type
recorded for that PR (``pr_findings``), matching the previous intent of the
removed webhook handler.
"""

import requests

from services.github.reporter import (
    _RETRY_KWARGS,
    _github_headers,
    _raise_on_rate_limit,
)
from utils.db import (
    get_install_id_for_repo,
    get_pollable_bot_comments,
    get_pr_findings,
    mark_reaction_processed,
    reaction_processed,
    record_feedback,
)
from utils.logger import logger
from utils.retry import retry

_REACTION_OUTCOMES: dict[str, str] = {
    "rocket": "ACCEPTED",
    "-1": "REJECTED",
}


def _retry_logger(exc, attempt, delay):
    logger.warning(f"Reaction API attempt {attempt} failed: {exc}, retrying in {delay:.1f}s", "FEEDBACK")


@retry(**_RETRY_KWARGS, on_retry=_retry_logger)
def fetch_reactions(repo: str, comment_id: int, access_token: str) -> list[dict]:
    """Fetch reactions for a single issue comment.

    Returns a list of reaction dicts (each with ``id``, ``content`` and
    ``user.login``). Non-2xx responses are logged and treated as no reactions
    so a single failed repo never blocks the cycle.
    """
    url = (
        f"https://api.github.com/repos/"
        f"{repo}/issues/comments/{comment_id}/reactions"
        "?per_page=100"
    )
    headers = _github_headers(access_token)
    response = requests.get(url, headers=headers, timeout=15)
    _raise_on_rate_limit(response)
    if response.status_code != 200:
        logger.warning(
            f"Reaction fetch returned {response.status_code}: {response.text[:200]}",
            "FEEDBACK",
        )
        return []
    return response.json() or []


def sync_reaction_feedback(token_provider) -> dict:
    """Poll reactions on tracked bot comments and record feedback.

    Args:
        token_provider: callable ``token_provider(install_id) -> access_token``.
            Injected to avoid a circular import with ``app.app``; the app passes
            ``get_cached_token`` and tests pass a mock.

    Returns a summary dict ``{"accepted": int, "rejected": int, "skipped": int}``.
    Each bot comment is isolated in try/except so one failure never aborts the
    cycle.
    """
    accepted = rejected = skipped = 0
    comments = get_pollable_bot_comments()

    for comment in comments:
        comment_id = comment["comment_id"]
        repo = comment["repo"]
        pr_number = comment["pr_number"]
        try:
            install_id = get_install_id_for_repo(repo)
            if not install_id:
                continue
            access_token = token_provider(install_id)
            reactions = fetch_reactions(repo, comment_id, access_token)
            vuln_types = get_pr_findings(pr_number)

            for reaction in reactions:
                content = reaction.get("content")
                if content not in _REACTION_OUTCOMES:
                    continue
                reaction_id = reaction.get("id")
                user_login = (reaction.get("user") or {}).get("login", "")
                if not reaction_id or reaction_processed(reaction_id):
                    skipped += 1
                    continue

                outcome = _REACTION_OUTCOMES[content]
                for vuln_type in vuln_types:
                    record_feedback(
                        vuln_type,
                        outcome,
                        user_id=user_login,
                        display_name=user_login,
                        pr_number=pr_number,
                    )
                mark_reaction_processed(reaction_id, comment_id, user_login, content)

                if outcome == "ACCEPTED":
                    accepted += 1
                else:
                    rejected += 1
                logger.info(
                    f"Auto-Feedback: {vuln_types or '?'} {outcome.lower()} "
                    f"via {content} by {user_login} (PR #{pr_number})",
                    "FEEDBACK",
                )
        except Exception as e:
            logger.warning(
                f"Reaction sync failed for {repo}#{pr_number}: {e}",
                "FEEDBACK",
            )

    logger.info(
        f"Reaction sync complete: {accepted} accepted, {rejected} rejected, "
        f"{skipped} skipped (across {len(comments)} comments)",
        "FEEDBACK",
    )
    return {"accepted": accepted, "rejected": rejected, "skipped": skipped}
