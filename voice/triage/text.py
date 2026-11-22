"""Text normalization: the single source is the API's rules module, so rules and classifier always agree."""
from app.services.triage_rules import normalize  # noqa: F401
