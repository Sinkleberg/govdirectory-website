#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Offline sort checks: install rdflib, then run python scripts/tests/test-query-order.py."""

import re
import unittest
from pathlib import Path

from rdflib import Graph
from rdflib.plugins.sparql.parser import parseQuery

ROOT = Path(__file__).resolve().parents[2]


def order_clause(query):
    match = re.search(r"\bORDER\s+BY\s+(.+)$", query, re.IGNORECASE | re.MULTILINE)
    if not match:
        raise AssertionError("Missing ORDER BY")
    return match.group(1).strip()


def ordered_labels(clause, rows):
    query = """
        SELECT ?orgLabel ?type ?typeLabel WHERE {
            VALUES (?orgLabel ?type ?typeLabel) { %s }
        } ORDER BY %s
    """ % (rows, clause)
    return [str(row.orgLabel) for row in Graph().query(query)]


class AgencyOrderTests(unittest.TestCase):
    def test_organization_labels_ignore_case_and_language_tag(self):
        # Deliberately shuffled input, mixed case, and language fallbacks.
        rows = """
            ("charlie" <urn:type:1> "Ministries"@en)
            ("Bravo"@de <urn:type:1> "Ministries"@en)
            ("delta"@en <urn:type:1> "Ministries"@en)
            ("alpha"@en <urn:type:1> "Ministries"@en)
        """
        for path in sorted((ROOT / "queries/generators").rglob("*.rq")):
            with self.subTest(query=path.relative_to(ROOT)):
                query = path.read_text(encoding="utf-8")
                parseQuery(query)
                self.assertEqual(
                    ordered_labels(order_clause(query), rows),
                    ["alpha", "Bravo", "charlie", "delta"],
                )

    def test_type_label_order_keeps_groups_before_organization_names(self):
        rows = """
            ("zulu" <urn:type:1> "alpha"@en)
            ("aardvark" <urn:type:1> "Bravo"@de)
        """
        for path in sorted((ROOT / "queries/generators").rglob("*.rq")):
            clause = order_clause(path.read_text(encoding="utf-8"))
            if "?typeLabel" not in clause:
                continue
            with self.subTest(query=path.relative_to(ROOT)):
                # The US deliberately displays type labels in descending order.
                expected = ["aardvark", "zulu"] if path.name == "united-states.rq" else ["zulu", "aardvark"]
                self.assertEqual(ordered_labels(clause, rows), expected)

    def test_type_identifiers_keep_their_existing_group_order(self):
        rows = """
            ("aardvark" <urn:type:2> "Alpha")
            ("zulu" <urn:type:1> "Zulu")
        """
        for path in sorted((ROOT / "queries/generators").rglob("*.rq")):
            clause = order_clause(path.read_text(encoding="utf-8"))
            if not re.match(r"(?:DESC\()?\?type\b", clause):
                continue
            with self.subTest(query=path.relative_to(ROOT)):
                # South Africa deliberately displays type identifiers descending.
                expected = ["aardvark", "zulu"] if path.name == "south-africa.rq" else ["zulu", "aardvark"]
                self.assertEqual(ordered_labels(clause, rows), expected)

    def test_country_guide_agency_examples(self):
        guide = (ROOT / "ADD_A_COUNTRY.md").read_text(encoding="utf-8")
        clauses = re.findall(r"^\s*ORDER BY (.*\?orgLabel.*)$", guide, re.MULTILINE)
        self.assertEqual(len(clauses), 2)
        rows = '("Bravo" <urn:type:1> "Ministries") ("alpha" <urn:type:1> "Ministries")'
        for clause in clauses:
            with self.subTest(clause=clause):
                self.assertEqual(ordered_labels(clause, rows), ["alpha", "Bravo"])


if __name__ == "__main__":
    unittest.main()
