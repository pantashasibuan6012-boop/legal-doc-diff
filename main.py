#!/usr/bin/env python3
"""Legal Document Diff."""

import sys, json
from dataclasses import dataclass, field
from pathlib import Path
from difflib import unified_diff

@dataclass
class Clause:
    id: str
    title: str
    text: str
    risk_level: str = "low"

@dataclass
class Change:
    clause_id: str
    type: str
    old_text: str
    new_text: str
    risk_impact: str = "none"
    description: str = ""

@dataclass
class DiffReport:
    file_a: str
    file_b: str
    changes: list = field(default_factory=list)
    risk_summary: dict = field(default_factory=dict)

class LegalDiff:
    RISK_KEYWORDS = {
        "high": ["indemnify", "liability", "terminate", "penalty", "exclusive"],
        "medium": ["warranty", "confidential", "payment", "delivery", "scope"],
        "low": ["notice", "address", "reference", "date", "signature"],
    }

    def compare(self, path_a: str, path_b: str) -> DiffReport:
        text_a = self._read(path_a)
        text_b = self._read(path_b)

        clauses_a = self._parse_clauses(text_a)
        clauses_b = self._parse_clauses(text_b)

        report = DiffReport(file_a=path_a, file_b=path_b)
        report.changes = self._find_changes(clauses_a, clauses_b)
        report.risk_summary = self._assess_risks(report.changes)
        return report

    def _read(self, path: str) -> str:
        p = Path(path)
        if p.suffix == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(p))
                return "\n".join(page.get_text() for page in doc)
            except ImportError:
                return p.read_text()
        return p.read_text()

    def _parse_clauses(self, text: str) -> list:
        clauses = []
        current_title = "Preamble"
        current_text = []
        cid = 0

        for line in text.split("\n"):
            if line.strip() and (line[0].isdigit() or line.startswith("Article") or line.startswith("Section")):
                if current_text:
                    clauses.append(Clause(str(cid), current_title, "\n".join(current_text),
                                          self._clause_risk("\n".join(current_text))))
                    cid += 1
                current_title = line.strip()
                current_text = []
            else:
                current_text.append(line)

        if current_text:
            clauses.append(Clause(str(cid), current_title, "\n".join(current_text),
                                  self._clause_risk("\n".join(current_text))))
        return clauses

    def _clause_risk(self, text: str) -> str:
        lower = text.lower()
        for level in ["high", "medium"]:
            if any(kw in lower for kw in self.RISK_KEYWORDS[level]):
                return level
        return "low"

    def _find_changes(self, clauses_a: list, clauses_b: list) -> list:
        changes = []
        map_a = {c.title: c for c in clauses_a}
        map_b = {c.title: c for c in clauses_b}

        for title, clause_b in map_b.items():
            if title not in map_a:
                changes.append(Change(title, "added", "", clause_b.text, clause_b.risk_level,
                                      f"New clause: {title}"))
            elif clause_b.text != map_a[title].text:
                risk = "high" if clause_b.risk_level == "high" else "medium"
                changes.append(Change(title, "modified", map_a[title].text, clause_b.text, risk,
                                      f"Modified: {title}"))

        for title in map_a:
            if title not in map_b:
                changes.append(Change(title, "removed", map_a[title].text, "", "high",
                                      f"Removed clause: {title}"))

        return changes

    def _assess_risks(self, changes: list) -> dict:
        risks = {"high": 0, "medium": 0, "low": 0, "none": 0}
        for c in changes:
            risks[c.risk_impact] = risks.get(c.risk_impact, 0) + 1
        return risks

def main():
    if len(sys.argv) < 4:
        print("Usage: python main.py compare <file_a> <file_b>")
        sys.exit(1)
    diff = LegalDiff()
    report = diff.compare(sys.argv[2], sys.argv[3])
    print(f"Changes: {len(report.changes)}")
    print(f"Risk: {report.risk_summary}")
    for c in report.changes:
        print(f"  [{c.type}] {c.clause_id} - {c.description}")

if __name__ == "__main__":
    main()
