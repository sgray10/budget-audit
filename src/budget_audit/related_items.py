from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

# Semantic cross-linking: find rows/clusters elsewhere in the packet that
# probably belong in the same review conversation as a priority area, without
# claiming they are definitely connected. Three deliberately simple, generic
# mechanisms (no hardcoded pair list):
#
# 1. Fund-name search -- a whole-fund change to "Nursing Home" (Fund 202)
#    finds Fund 101's "NH Investment Income - Nursing Home Funds" and
#    "NH Contributions - Nursing Home" because the fund's name appears in
#    those labels.
# 2. Prefix similarity -- cluster prefixes sharing a 3+ character stem link
#    OPID to OPIA (both opioid-settlement prefixes).
# 3. Distinctive-keyword search -- capitalized words of 6+ letters from a
#    cluster's key labels (e.g. "Opioid", "Connected", "Communities"),
#    minus a generic-budget-vocabulary stoplist, matched against labels in
#    other funds/prefixes.
#
# All three produce *candidates for joint review*, not assertions -- render
# with "potentially related items ... should be reviewed together" language.

MAX_RELATED_ITEMS = 5
MIN_PREFIX_STEM = 3
KEYWORD_RE = re.compile(r"[A-Z][a-z]{5,}")

# Words too generic in budget-label vocabulary to signal a real relationship
# on their own (verified against the real consolidated dataset -- each of
# these appears across many unrelated funds/labels).
#
# "health" and "patient" were added after reviewing a real generated report:
# both cleared the packet-rarity gate (4 and 2 occurrences) but linked
# genuinely unrelated lines -- Fund 171's "Other Health & Welfare Grants"
# to Fund 101's health department budget and Fund 141's school health
# program via the word "Health" alone, and Fund 202 Nursing Home's
# "Patient Charges" to Fund 101's "Inmate/Patient Charges" (jail medical
# billing) via "Patient" alone. Low document frequency is necessary but not
# sufficient for two rows to be worth reviewing together -- these two words
# are common enough in county-budget vocabulary that a shared occurrence is
# coincidence, not signal.
KEYWORD_STOPLIST = {
    "county",
    "federal",
    "general",
    "grants",
    "health",
    "income",
    "insurance",
    "interest",
    "maintenance",
    "miscellaneous",
    "office",
    "other",
    "patient",
    "personnel",
    "program",
    "purpose",
    "revenue",
    "revenues",
    "salaries",
    "salary",
    "school",
    "service",
    "services",
    "supplies",
    "supplement",
    "transfers",
}


@dataclass(frozen=True)
class RelatedItem:
    description: str  # human-readable, with fund/page/account/label
    reason: str  # which mechanism linked it (fund_name / prefix / keyword)


@dataclass(frozen=True)
class LabelIndexEntry:
    fund_number: str
    fund_name: str
    page_number: str
    account: str
    label: str
    prefix_stem: str


def _prefix_stem(label: str) -> str:
    match = re.match(r"^([A-Z0-9]{2,8})\s", label.strip().lstrip("=+~"))
    return match.group(1)[:MIN_PREFIX_STEM] if match else ""


def build_label_index(rows_path: Path) -> list[LabelIndexEntry]:
    rows = list(csv.DictReader(rows_path.open(encoding="utf-8")))
    index: list[LabelIndexEntry] = []
    for row in rows:
        if row.get("row_type") != "line_item":
            continue
        label = row.get("label", "")
        if not label:
            continue
        index.append(
            LabelIndexEntry(
                fund_number=row.get("fund_number", ""),
                fund_name=row.get("fund_name", ""),
                page_number=row.get("page_number", ""),
                account=row.get("account", ""),
                label=label,
                prefix_stem=_prefix_stem(label),
            )
        )
    return index


def _entry_description(entry: LabelIndexEntry) -> str:
    return f"Fund {entry.fund_number} page {entry.page_number} account {entry.account}: {entry.label}"


# Recipient-name phrases are stripped before keyword extraction: in a label
# like "OPID City of Dresden", the word "Dresden" identifies a *recipient*,
# not a program -- letting it through links the opioid-allocation cluster to
# every unrelated Dresden line (library contributions, aging programs).
RECIPIENT_PHRASE_RE = re.compile(r"\b(?:city|town|county) of\s+[A-Z][a-z]+", re.IGNORECASE)


def distinctive_keywords(labels: list[str]) -> set[str]:
    keywords: set[str] = set()
    for label in labels:
        stripped = RECIPIENT_PHRASE_RE.sub(" ", label)
        for word in KEYWORD_RE.findall(stripped):
            if word.lower() not in KEYWORD_STOPLIST:
                keywords.add(word)
    return keywords


def related_for_fund_name(
    fund_number: str, fund_name: str, index: list[LabelIndexEntry], limit: int = MAX_RELATED_ITEMS
) -> list[RelatedItem]:
    """Rows in *other* funds whose label mentions this fund's name -- e.g. a
    Fund 202 Nursing Home structural change linking to Fund 101's
    'NH ... Nursing Home Funds' revenue lines.
    """
    if not fund_name.strip():
        return []
    needle = fund_name.strip().lower()
    related: list[RelatedItem] = []
    for entry in index:
        if entry.fund_number == fund_number:
            continue
        if needle in entry.label.lower():
            related.append(RelatedItem(description=_entry_description(entry), reason="fund_name"))
            if len(related) >= limit:
                break
    return related


def related_for_prefix(
    fund_number: str,
    prefix: str,
    cluster_rows: list[dict[str, str]],
    limit: int = MAX_RELATED_ITEMS,
) -> list[RelatedItem]:
    """Clusters (any fund) whose prefix shares a leading stem with this one --
    e.g. OPID <-> OPIA, both opioid-settlement prefixes.
    """
    stem = prefix.lstrip("=+~")[:MIN_PREFIX_STEM]
    if len(stem) < MIN_PREFIX_STEM:
        return []
    related: list[RelatedItem] = []
    for row in cluster_rows:
        other_prefix = row.get("prefix", "").lstrip("=+~")
        if row.get("fund_number") == fund_number and row.get("prefix") == prefix:
            continue
        if other_prefix[:MIN_PREFIX_STEM] == stem:
            related.append(
                RelatedItem(
                    description=(
                        f"Cluster {row.get('cluster_id', '')} (Fund {row.get('fund_number', '')}): "
                        f"{row.get('sample_labels', '')}"
                    ),
                    reason="prefix",
                )
            )
            if len(related) >= limit:
                break
    return related


# A keyword may link two rows on its own only if it is rare across the whole
# packet -- "Opioid" (appears in a handful of settlement-fund rows) is a real
# relationship signal; "Building" (appears in maintenance, insurance, and
# construction labels across every fund) is not. Rarity is computed from the
# actual index rather than hand-maintaining a bigger stoplist, so the same
# rule transfers to future packets/counties unchanged.
MAX_KEYWORD_DOCUMENT_FREQUENCY = 4


def related_for_keywords(
    source_labels: list[str],
    exclude_fund: str,
    exclude_prefix_stem: str,
    index: list[LabelIndexEntry],
    limit: int = MAX_RELATED_ITEMS,
) -> list[RelatedItem]:
    """Rows elsewhere in the packet whose label shares a *rare* distinctive
    keyword with the source labels -- e.g. 'Opioid' linking OPID cluster
    labels to OPIA rows. Excludes rows in the same fund+prefix as the
    source, since those are the cluster itself, not a related discovery.
    """
    keywords = distinctive_keywords(source_labels)
    if not keywords:
        return []

    frequency: dict[str, int] = dict.fromkeys(keywords, 0)
    for entry in index:
        for keyword in keywords:
            if keyword in entry.label:
                frequency[keyword] += 1
    rare_keywords = {k for k, count in frequency.items() if count <= MAX_KEYWORD_DOCUMENT_FREQUENCY}
    if not rare_keywords:
        return []

    related: list[RelatedItem] = []
    seen: set[str] = set()
    for entry in index:
        if entry.fund_number == exclude_fund and entry.prefix_stem == exclude_prefix_stem:
            continue
        if any(keyword in entry.label for keyword in rare_keywords):
            description = _entry_description(entry)
            if description in seen:
                continue
            seen.add(description)
            related.append(RelatedItem(description=description, reason="keyword"))
            if len(related) >= limit:
                break
    return related


def dedupe_related(items: list[RelatedItem], limit: int = MAX_RELATED_ITEMS) -> list[RelatedItem]:
    seen: set[str] = set()
    result: list[RelatedItem] = []
    for item in items:
        if item.description not in seen:
            seen.add(item.description)
            result.append(item)
            if len(result) >= limit:
                break
    return result


__all__ = [
    "MAX_RELATED_ITEMS",
    "LabelIndexEntry",
    "RelatedItem",
    "build_label_index",
    "dedupe_related",
    "distinctive_keywords",
    "related_for_fund_name",
    "related_for_keywords",
    "related_for_prefix",
]
