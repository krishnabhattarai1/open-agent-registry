"""Built-in capability taxonomy and matching logic.

Capabilities use a `domain.action[.qualifier]` hierarchy.
Agents match on codes — no natural language parsing required.
"""

TAXONOMY_VERSION = 1

# domain -> list of actions (qualifiers expressed as nested dots)
TAXONOMY: dict[str, list[str]] = {
    "code": [
        "review", "gen", "fix", "lint", "test", "refactor",
        "doc", "translate", "explain", "debug",
    ],
    "data": [
        "transform", "validate", "enrich", "clean", "dedupe",
        "merge", "aggregate", "parse", "convert",
    ],
    "text": [
        "summarize", "translate", "classify", "extract", "generate",
        "edit", "sentiment", "embed", "qa",
    ],
    "web": [
        "scrape", "browse", "monitor", "screenshot", "api.call", "crawl",
    ],
    "search": [
        "semantic", "keyword", "rag", "vector", "index",
    ],
    "reason": [
        "plan", "math", "decide", "decompose", "verify",
    ],
    "media": [
        "img.gen", "img.edit", "img.describe",
        "audio.transcribe", "audio.gen", "video.summarize",
    ],
    "file": [
        "read", "write", "convert", "compress", "parse",
    ],
    "db": [
        "query", "migrate", "model", "optimize",
    ],
    "sec": [
        "scan", "audit", "pentest", "monitor",
    ],
    "infra": [
        "deploy", "provision", "monitor", "scale", "backup",
    ],
    "comms": [
        "email.send", "email.read", "chat.send", "notify",
    ],
}


def all_codes() -> list[str]:
    """Return all valid capability codes."""
    codes: list[str] = []
    for domain, actions in TAXONOMY.items():
        for action in actions:
            codes.append(f"{domain}.{action}")
    return codes


_ALL_CODES_SET: set[str] | None = None


def _get_all_codes_set() -> set[str]:
    global _ALL_CODES_SET
    if _ALL_CODES_SET is None:
        _ALL_CODES_SET = set(all_codes())
    return _ALL_CODES_SET


def is_valid_code(code: str) -> bool:
    """Check if a capability code is in the taxonomy."""
    return code in _get_all_codes_set()


def validate_codes(codes: list[str]) -> list[str]:
    """Return list of invalid codes (empty if all valid)."""
    valid = _get_all_codes_set()
    return [c for c in codes if c not in valid]


def match_prefix(prefix: str, agent_codes: list[str]) -> bool:
    """Check if any of the agent's codes start with the given prefix."""
    return any(c == prefix or c.startswith(prefix + ".") for c in agent_codes)


def match_exact(code: str, agent_codes: list[str]) -> bool:
    """Check if the agent has the exact capability code."""
    return code in agent_codes


def match_all(required: list[str], agent_codes: list[str]) -> bool:
    """Check if the agent has ALL required capabilities (exact or prefix match)."""
    agent_set = set(agent_codes)
    for req in required:
        if req in agent_set:
            continue
        if not match_prefix(req, agent_codes):
            return False
    return True


def match_any(wanted: list[str], agent_codes: list[str]) -> bool:
    """Check if the agent has ANY of the wanted capabilities."""
    agent_set = set(agent_codes)
    for w in wanted:
        if w in agent_set or match_prefix(w, agent_codes):
            return True
    return False


def match_none(excluded: list[str], agent_codes: list[str]) -> bool:
    """Check that the agent has NONE of the excluded capabilities."""
    agent_set = set(agent_codes)
    for ex in excluded:
        if ex in agent_set or match_prefix(ex, agent_codes):
            return False
    return True


def compute_match_score(
    need: list[str],
    want: list[str] | None,
    agent_codes: list[str],
) -> int:
    """Compute a 0-100 match score.

    - need matches contribute the base score (0-70)
    - want matches contribute a bonus (0-30)
    """
    if not need:
        return 0

    # Base score: proportion of need codes matched
    need_matched = sum(1 for n in need if match_exact(n, agent_codes) or match_prefix(n, agent_codes))
    base = int((need_matched / len(need)) * 70)

    # Bonus: proportion of want codes matched
    bonus = 0
    if want:
        want_matched = sum(
            1 for w in want if match_exact(w, agent_codes) or match_prefix(w, agent_codes)
        )
        bonus = int((want_matched / len(want)) * 30)

    return base + bonus


def get_taxonomy_compact() -> dict:
    """Return the taxonomy in compact format for the API."""
    return {
        "v": TAXONOMY_VERSION,
        "domains": TAXONOMY,
    }
