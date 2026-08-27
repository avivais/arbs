import unittest

from arbs.source_identifier_audit import (
    audit_match,
    audit_report,
    decode_kalshi,
    decode_polymarket,
)


def _match(kalshi_id: str, polymarket_url: str, participants: list[str]) -> dict:
    return {
        "decision": "REVIEW",
        "participants": participants,
        "kalshi": {"event_id": kalshi_id},
        "polymarket": {"event_id": "123", "source_url": polymarket_url},
    }


class SourceIdentifierAuditTests(unittest.TestCase):
    def test_decodes_identifier_aliases_without_live_parser(self):
        self.assertEqual(
            decode_kalshi("KXMLBGAME-26AUG121540COLAZ"),
            {"date": "2026-08-12", "participants": ["ARI", "COL"], "game_number": None},
        )
        self.assertEqual(
            decode_polymarket("https://polymarket.com/event/mlb-min-oak-2026-08-26"),
            {"date": "2026-08-26", "participants": ["ATH", "MIN"]},
        )

    def test_same_date_and_participants_corroborate_but_never_enable_pricing(self):
        row = audit_match(_match(
            "KXMLBGAME-26AUG121540COLAZ",
            "https://polymarket.com/event/mlb-col-ari-2026-08-12",
            ["ARI", "COL"],
        ))
        self.assertEqual(row["status"], "IDENTIFIERS_CORROBORATE_EVENT")
        self.assertFalse(row["pricing_eligible"])
        self.assertEqual(len(row["evidence_sha256"]), 64)

    def test_date_disagreement_remains_review(self):
        row = audit_match(_match(
            "KXMLBGAME-26AUG291305BOSNYYG1",
            "https://polymarket.com/event/mlb-bos-nyy-2026-06-06",
            ["BOS", "NYY"],
        ))
        self.assertEqual(row["status"], "REVIEW_DATE_IDENTIFIER_CONFLICT")
        self.assertEqual(row["kalshi_identifier"]["game_number"], 1)
        self.assertFalse(row["pricing_eligible"])

    def test_conflicts_and_unknown_formats_fail_closed(self):
        participant = audit_match(_match(
            "KXMLBGAME-26AUG121540COLAZ",
            "https://polymarket.com/event/mlb-col-sf-2026-08-12",
            ["ARI", "COL"],
        ))
        unsupported = audit_match(_match("not-an-id", "https://example.test/nope", []))
        self.assertEqual(participant["status"], "REVIEW_PARTICIPANT_IDENTIFIER_CONFLICT")
        self.assertEqual(unsupported["status"], "UNSUPPORTED_IDENTIFIER_FORMAT")

    def test_automated_report_explicitly_does_not_satisfy_independent_gate(self):
        value = audit_report([_match(
            "KXMLBGAME-26AUG121540COLAZ",
            "https://polymarket.com/event/mlb-col-ari-2026-08-12",
            ["ARI", "COL"],
        )])
        self.assertEqual(value["match_count"], 1)
        self.assertIn("NOT_SATISFIED", value["independent_label_gate_status"])
        self.assertFalse(value["pricing_eligible"])


if __name__ == "__main__":
    unittest.main()
