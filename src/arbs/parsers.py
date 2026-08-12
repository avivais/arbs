"""Reason-coded, lineage-preserving replay parsers for the bounded MLB MVP."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from arbs.matching.live import VenueEvent, match_events, normalize_kalshi, normalize_polymarket

PARSER_VERSION = "mlb-mvp-1.0.0"


@dataclass(frozen=True)
class ParseDecision:
    venue: str
    source_ids: tuple[str, ...]
    decision: str
    reason_codes: tuple[str, ...]
    parser_version: str
    source_hashes: tuple[str, ...]
    source_urls: tuple[str, ...]
    received_at: tuple[str, ...]
    source_fields: tuple[str, ...]
    transformations: tuple[str, ...]
    event: VenueEvent | None


def _lineage(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {"source_ids": tuple(r["source_id"] for r in records),
            "source_hashes": tuple(r["payload_sha256"] for r in records),
            "source_urls": tuple(r["source_url"] for r in records),
            "received_at": tuple(r["received_at"] for r in records)}


def parse_kalshi(records: list[dict[str, Any]]) -> list[ParseDecision]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        payload = record["payload"]
        event_id = str(payload.get("event_ticker") or "")
        groups.setdefault(event_id or f"missing:{record['source_id']}", []).append(record)
    out=[]
    for _, group in sorted(groups.items()):
        events = normalize_kalshi([r["payload"] for r in group])
        lineage = _lineage(group)
        if len(events) == 1:
            out.append(ParseDecision("kalshi", **lineage, decision="ACCEPTED", reason_codes=(), parser_version=PARSER_VERSION,
                                     source_fields=("event_ticker","yes_sub_title","expected_expiration_time","rules_primary","rules_secondary"),
                                     transformations=("league-scoped exact alias","UTC normalization","two-contract event grouping"), event=events[0]))
        else:
            reasons=[]
            payloads=[r["payload"] for r in group]
            if any(not p.get("event_ticker") for p in payloads): reasons.append("MISSING_EVENT_ID")
            if any(not p.get("yes_sub_title") for p in payloads): reasons.append("MISSING_PARTICIPANT")
            if len(payloads) != 2: reasons.append("NOT_BINARY_TWO_CONTRACT_EVENT")
            if not reasons: reasons.append("UNSUPPORTED_OR_AMBIGUOUS_KALSHI_EVENT")
            out.append(ParseDecision("kalshi", **lineage, decision="UNSUPPORTED", reason_codes=tuple(reasons), parser_version=PARSER_VERSION,
                                     source_fields=(), transformations=(), event=None))
    return out


def parse_polymarket(records: list[dict[str, Any]]) -> list[ParseDecision]:
    out=[]
    for record in sorted(records, key=lambda r:r["source_id"]):
        events=normalize_polymarket([record["payload"]]); lineage=_lineage([record])
        if len(events)==1:
            out.append(ParseDecision("polymarket", **lineage, decision="ACCEPTED", reason_codes=(), parser_version=PARSER_VERSION,
                                     source_fields=("id","title","markets[].gameStartTime","markets[].sportsMarketType","markets[].outcomes","markets[].clobTokenIds","resolutionSource"),
                                     transformations=("league-scoped exact alias","UTC normalization","winner-market selection","token/outcome orientation"), event=events[0]))
        else:
            event=record["payload"]; markets=event.get("markets")
            reasons=[]
            if not isinstance(markets,list): reasons.append("INVALID_MARKETS_SHAPE")
            elif not markets: reasons.append("NO_MARKETS")
            else: reasons.append("NO_UNIQUE_ACTIVE_WINNER_MARKET")
            out.append(ParseDecision("polymarket", **lineage, decision="UNSUPPORTED", reason_codes=tuple(reasons), parser_version=PARSER_VERSION,
                                     source_fields=(), transformations=(), event=None))
    return out


def replay_decisions(records: list[dict[str, Any]]) -> dict[str, Any]:
    k=parse_kalshi([r for r in records if r["venue"]=="kalshi"])
    p=parse_polymarket([r for r in records if r["venue"]=="polymarket"])
    ke=[x.event for x in k if x.event is not None]; pe=[x.event for x in p if x.event is not None]
    matches=match_events(ke,pe)
    matched_k={m.kalshi["event_id"] for m in matches}; matched_p={m.polymarket["event_id"] for m in matches}
    unpaired=[{"venue":"kalshi","event_id":e.event_id,"decision":"UNPAIRED","reason_codes":["NO_UNIQUE_CROSS_VENUE_CANDIDATE"]}
              for e in ke if e.event_id not in matched_k]
    unpaired += [{"venue":"polymarket","event_id":e.event_id,"decision":"UNPAIRED","reason_codes":["NO_UNIQUE_CROSS_VENUE_CANDIDATE"]}
                 for e in pe if e.event_id not in matched_p]
    return {"parser_version":PARSER_VERSION,"parse_decisions":[asdict(x) for x in k+p],
            "matches":[asdict(x) for x in matches],"unpaired":sorted(unpaired,key=lambda x:(x["venue"],x["event_id"]))}
