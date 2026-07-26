"""Provenance and untrusted-text controls shared by the deterministic renderers.

Two boundaries live here.

Provenance: a draft may only reuse a prior record the request actually cited.
The Frappe payload builders emit one `SourceReference` per history entry, so
`cited_history` drops anything that reaches the HTTP boundary without a
citation instead of quoting a record the reviewer cannot trace.

Untrusted text: free-text fields are technician and dispatcher input. They are
data, never instructions, and they must not carry contact details or
credential-shaped values into a durable proposal record. `quote_inline` and
`quote_block` redact and neutralize before the text reaches `draft_content`.
Identifiers, statuses, and record names stay untouched so a reviewer can still
match a draft to its source records.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Any

EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<![\w-])(?:\+?\d[\d .()\-]{7,}\d)(?![\w-])")
# Shape allowlist for operational facts. Dates and money amounts survive; other
# long digit runs redact, which is the safe direction for a contact number.
GROUNDING_FACT_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,3}(?: \d{3})*\.\d{2}")
SENSITIVE_VALUE_PATTERN = re.compile(
	r"(?i)\b(?:api[_ -]?key|access[_ -]?token|bearer|password|secret|credential)\b\s*[:=]?\s*[^\s,;]{4,}"
)

# Deliberately narrow. These shapes have no place in a service note, so
# neutralizing them cannot damage a legitimate technician record. Ordinary
# operational imperatives such as "close the work order once parts arrive" stay
# intact; the renderers already state that a draft performs no ERP action.
INJECTION_PATTERNS = (
	re.compile(
		r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?"
		r"\b(?:previous|prior|preceding|earlier|above|all)\b[^.\n]{0,40}?"
		r"\b(?:instruction|instructions|prompt|prompts|rule|rules|direction|directions)\b"
	),
	re.compile(r"(?i)\b(?:system|developer|assistant)\s+(?:prompt|message|instructions)\b"),
	re.compile(r"(?i)\bnew\s+instructions?\s*:"),
	re.compile(r"(?i)\byou\s+are\s+(?:now\s+)?an?\s+(?:ai|assistant|language\s+model|llm)\b"),
	re.compile(r"(?im)^\s*(?:system|developer|assistant)\s*:"),
	re.compile(r"<\|[a-z_]+\|>"),
)

REDACTION_MARKER = "[REDACTED]"
INJECTION_MARKER = "[removed: instruction-like text in a quoted source]"
QUOTE_PREFIX = "> "


def redact(value: str) -> tuple[str, int]:
	"""Replace contact details and credential-shaped values. Returns text and count."""
	count = 0

	def redact_phone(match: re.Match[str]) -> str:
		nonlocal count
		if GROUNDING_FACT_PATTERN.fullmatch(match.group(0)):
			return match.group(0)
		count += 1
		return REDACTION_MARKER

	value, matches = EMAIL_PATTERN.subn(REDACTION_MARKER, value)
	count += matches
	value = PHONE_PATTERN.sub(redact_phone, value)
	value, matches = SENSITIVE_VALUE_PATTERN.subn(REDACTION_MARKER, value)
	count += matches
	return value, count


def neutralize(value: str) -> tuple[str, int]:
	"""Replace instruction-shaped spans in quoted source text. Returns text and count."""
	count = 0
	for pattern in INJECTION_PATTERNS:
		value, matches = pattern.subn(INJECTION_MARKER, value)
		count += matches
	return value, count


def _sanitize(value: str) -> str:
	value, _ = redact(value)
	value, _ = neutralize(value)
	return value


def quote_inline(value: str) -> str:
	"""Sanitize free text and collapse it to one line for `Label: value` output.

	Collapsing matters: a newline inside a note would otherwise place attacker
	text at the same indentation as the renderer's own governance lines.
	"""
	return " ".join(_sanitize(value).split())


def quote_block(value: str) -> str:
	"""Sanitize free text and mark every line as quoted source, not renderer output."""
	lines = _sanitize(value).splitlines() or [""]
	return "\n".join(f"{QUOTE_PREFIX}{line}".rstrip() for line in lines)


def cited_record_names(sources: Iterable[Any]) -> frozenset[str]:
	"""Return the record names the request cited."""
	return frozenset(source.name for source in sources)


def cited_history(
	entries: Sequence[Any], sources: Iterable[Any]
) -> tuple[list[Any], int]:
	"""Split history into citation-backed entries and a count of omitted ones.

	Kept as a plain Sequence[Any] so the host static gate (Python 3.9 compileall)
	and the control-plane runtime (3.14) share one syntax. Callers pass typed
	history models; the filter only reads ``.name``.
	"""
	allowed = cited_record_names(sources)
	kept = [entry for entry in entries if entry.name in allowed]
	return kept, len(entries) - len(kept)


def omission_note(omitted: int) -> list[str]:
	"""Render a reviewer-visible note when uncited prior records were dropped."""
	if not omitted:
		return []
	if omitted == 1:
		sentence = "1 prior record was omitted because the request supplied no citation for it."
	else:
		sentence = f"{omitted} prior records were omitted because the request supplied no citation for them."
	return ["", "Evidence note", sentence]
