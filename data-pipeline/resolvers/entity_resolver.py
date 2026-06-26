from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AliasRecord:
    raw_alias: str
    normalized_alias: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    observed_at: Optional[str] = None
    source: str = "UNKNOWN"

    def key(self) -> Tuple[str, str, Optional[str], Optional[str], Optional[str], str]:
        return (
            self.raw_alias,
            self.normalized_alias,
            self.valid_from,
            self.valid_to,
            self.observed_at,
            self.source,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_alias": self.raw_alias,
            "normalized_alias": self.normalized_alias,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "observed_at": self.observed_at,
            "source": self.source,
        }


@dataclass
class Entity:
    entity_id: str

    # Global identifiers
    leis: Set[str] = field(default_factory=set)
    bics: Set[str] = field(default_factory=set)
    bic_roots: Set[str] = field(default_factory=set)

    # Korean identifiers
    corp_codes: Set[str] = field(default_factory=set)
    corporate_registration_numbers: Set[str] = field(default_factory=set)
    business_numbers: Set[str] = field(default_factory=set)

    # Names
    aliases: Set[str] = field(default_factory=set)
    normalized_aliases: Set[str] = field(default_factory=set)
    alias_history: List[AliasRecord] = field(default_factory=list)

    # Branch / site qualifiers
    branch_qualifiers: Set[str] = field(default_factory=set)

    # Governance
    sources: Set[str] = field(default_factory=set)
    quality_flags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "leis": sorted(self.leis),
            "bics": sorted(self.bics),
            "bic_roots": sorted(self.bic_roots),
            "corp_codes": sorted(self.corp_codes),
            "corporate_registration_numbers": sorted(self.corporate_registration_numbers),
            "business_numbers": sorted(self.business_numbers),
            "aliases": sorted(self.aliases),
            "normalized_aliases": sorted(self.normalized_aliases),
            "alias_history": [a.to_dict() for a in self.alias_history],
            "branch_qualifiers": sorted(self.branch_qualifiers),
            "sources": sorted(self.sources),
            "quality_flags": sorted(self.quality_flags),
        }


class EntityResolver:
    """
    Korean + Global Entity Resolution Engine.

    Public methods:
      - normalize_name(name)
      - match(name_a, name_b, ...)
      - resolve(record)
      - batch_resolve(records)

    Governance principles:
      - Strong identifier exact match first.
      - Identifier conflict is never silently merged.
      - Fuzzy / cross-lingual matching without identifier is conservative.
      - Branch/site qualifiers are separated from core legal name.
      - Alias names are stored as point-in-time history.
      - Indexes are updated incrementally, not rebuilt globally.
    """

    CHOSUNG_LIST = [
        "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ",
        "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
        "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ",
        "ㅋ", "ㅌ", "ㅍ", "ㅎ",
    ]

    SIBLING_DISCRIMINATORS = {
        "서비스", "홀딩스", "캐피탈", "자산운용", "증권", "생명", "화재",
        "손해보험", "보험", "카드", "은행", "저축은행", "투자증권",
        "투자파트너스", "벤처스", "로지스틱스", "물류", "글로벌",
        "인터내셔널", "리테일", "디지털", "솔루션", "시스템", "테크",
        "테크놀로지", "바이오", "제약", "건설", "엔지니어링", "산업",
        "상사", "물산", "전자서비스", "모빌리티", "에너지", "이노베이션",
        "케미칼", "중공업", "스틸", "푸드", "FNB",
    }

    DEFAULT_CROSS_LINGUAL_ALIASES = {
        "삼성전자": {"SAMSUNGELECTRONICS", "SAMSUNG"},
        "네이버": {"NAVER"},
        "카카오": {"KAKAO"},
        "현대자동차": {"HYUNDAIMOTOR", "HYUNDAIMOTORS", "HYUNDAI"},
        "기아": {"KIA"},
        "엘지": {"LG"},
        "LG": {"엘지"},
        "에스케이": {"SK"},
        "SK": {"에스케이"},
        "포스코": {"POSCO"},
        "롯데": {"LOTTE"},
        "신세계": {"SHINSEGAE"},
        "한화": {"HANWHA"},
        "두산": {"DOOSAN"},
        "셀트리온": {"CELLTRION"},
    }

    def __init__(
        self,
        threshold: float = 0.85,
        no_identifier_threshold: float = 0.92,
        algorithm: str = "jaro_winkler",
        ambiguous_margin: float = 0.02,
        strict_identifier_conflict: bool = True,
        strict_business_no_on_name_match: bool = True,
        validate_business_no_checksum: bool = True,
        validate_lei_checksum: bool = True,
        use_blocking: bool = True,
        min_fuzzy_name_len: int = 3,
        min_block_overlap: int = 2,
        max_block_candidates: int = 5000,
        full_scan_limit: int = 3000,
        jaro_winkler_prefix_scale: float = 0.05,
        allow_cross_lingual_without_identifier: bool = False,
        enforce_alias_validity: bool = True,
        cross_lingual_aliases: Optional[Dict[str, Set[str]]] = None,
    ) -> None:
        if algorithm not in {"jaro_winkler", "levenshtein"}:
            raise ValueError("algorithm must be 'jaro_winkler' or 'levenshtein'")

        self.threshold = threshold
        self.no_identifier_threshold = no_identifier_threshold
        self.algorithm = algorithm
        self.ambiguous_margin = ambiguous_margin

        self.strict_identifier_conflict = strict_identifier_conflict
        self.strict_business_no_on_name_match = strict_business_no_on_name_match
        self.validate_business_no_checksum = validate_business_no_checksum
        self.validate_lei_checksum = validate_lei_checksum

        self.use_blocking = use_blocking
        self.min_fuzzy_name_len = min_fuzzy_name_len
        self.min_block_overlap = min_block_overlap
        self.max_block_candidates = max_block_candidates
        self.full_scan_limit = full_scan_limit

        self.jaro_winkler_prefix_scale = jaro_winkler_prefix_scale
        self.allow_cross_lingual_without_identifier = allow_cross_lingual_without_identifier
        self.enforce_alias_validity = enforce_alias_validity

        self.entities: Dict[str, Entity] = {}

        # Global identifier indexes
        self.lei_index: Dict[str, str] = {}
        self.bic_index: Dict[str, str] = {}
        self.bic_root_index: Dict[str, Set[str]] = {}

        # Korean identifier indexes
        self.corp_code_index: Dict[str, str] = {}
        self.corporate_registration_no_index: Dict[str, str] = {}
        self.business_no_index: Dict[str, str] = {}

        # Name indexes
        self.name_index: Dict[str, Set[str]] = {}
        self.name_block_index: Dict[str, Set[str]] = {}
        self.chosung_index: Dict[str, Set[str]] = {}
        self.cross_skeleton_index: Dict[str, Set[str]] = {}

        self._counter = 0

        self.cross_lingual_aliases = self._normalize_cross_lingual_alias_map(
            cross_lingual_aliases or self.DEFAULT_CROSS_LINGUAL_ALIASES
        )

    # ============================================================
    # Public normalizers
    # ============================================================

    def normalize_name(self, name: Any) -> str:
        return self._normalize_name_parts(name)["core_name"]

    def normalize_lei(self, lei: Any) -> Optional[str]:
        if lei is None:
            return None

        s = re.sub(r"[^0-9A-Za-z]", "", str(lei)).upper()

        if not re.fullmatch(r"[0-9A-Z]{20}", s):
            return None

        if self.validate_lei_checksum and not self.is_valid_lei(s):
            return None

        return s

    @staticmethod
    def is_valid_lei(lei: str) -> bool:
        """
        LEI checksum validation.
        A=10 ... Z=35, expanded number mod 97 must equal 1.
        """
        if not re.fullmatch(r"[0-9A-Z]{20}", lei):
            return False

        expanded = "".join(
            ch if ch.isdigit() else str(ord(ch) - ord("A") + 10)
            for ch in lei
        )

        return int(expanded) % 97 == 1

    def normalize_bic(self, bic: Any) -> Optional[str]:
        """
        BIC / SWIFT code format validation.
        8 or 11 chars:
          4 letters institution + 2 letters country + 2 alnum location + optional 3 alnum branch.
        """
        if bic is None:
            return None

        s = re.sub(r"[^0-9A-Za-z]", "", str(bic)).upper()

        if re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", s):
            return s

        return None

    @staticmethod
    def bic_root(bic: Optional[str]) -> Optional[str]:
        if not bic or len(bic) not in {8, 11}:
            return None

        return bic[:8]

    def normalize_business_no(
        self,
        business_no: Any,
        *,
        validate_checksum: Optional[bool] = None,
    ) -> Optional[str]:
        if business_no is None:
            return None

        digits = re.sub(r"\D", "", str(business_no))

        if len(digits) != 10:
            return None

        should_validate = (
            self.validate_business_no_checksum
            if validate_checksum is None
            else validate_checksum
        )

        if should_validate and not self.is_valid_business_no(digits):
            return None

        return digits

    @staticmethod
    def is_valid_business_no(digits: str) -> bool:
        if not re.fullmatch(r"\d{10}", digits):
            return False

        nums = [int(ch) for ch in digits]
        weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]

        total = 0

        for i in range(8):
            total += nums[i] * weights[i]

        ninth = nums[8] * weights[8]
        total += ninth // 10
        total += ninth % 10

        check_digit = (10 - (total % 10)) % 10

        return check_digit == nums[9]

    def normalize_corporate_registration_no(self, corporate_no: Any) -> Optional[str]:
        if corporate_no is None:
            return None

        digits = re.sub(r"\D", "", str(corporate_no))

        if len(digits) != 13:
            return None

        return digits

    def normalize_corp_code(self, corp_code: Any) -> Optional[str]:
        if corp_code is None:
            return None

        digits = re.sub(r"\D", "", str(corp_code).strip())

        if not digits:
            return None

        if len(digits) <= 8:
            return digits.zfill(8)

        return None

    # ============================================================
    # Public API
    # ============================================================

    def match(
        self,
        name_a: Any,
        name_b: Any,
        threshold: Optional[float] = None,
        has_matching_identifier: bool = False,
    ) -> Dict[str, Any]:
        a_parts = self._normalize_name_parts(name_a)
        b_parts = self._normalize_name_parts(name_b)

        a = a_parts["core_name"]
        b = b_parts["core_name"]

        if threshold is None:
            threshold = self.threshold if has_matching_identifier else self.no_identifier_threshold

        score, method, flags = self._best_name_score(
            a,
            b,
            has_matching_identifier=has_matching_identifier,
        )

        is_match = score >= threshold

        if not has_matching_identifier and "SIBLING_GUARD" in flags:
            is_match = False

        if (
            not has_matching_identifier
            and method == "cross_lingual"
            and not self.allow_cross_lingual_without_identifier
        ):
            is_match = False

        return {
            "is_match": is_match,
            "score": score,
            "threshold": threshold,
            "algorithm": self.algorithm,
            "method": method,
            "flags": flags,
            "normalized_a": a,
            "normalized_b": b,
            "branch_qualifiers_a": sorted(a_parts["branch_qualifiers"]),
            "branch_qualifiers_b": sorted(b_parts["branch_qualifiers"]),
        }

    def resolve(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            raise TypeError("record must be dict")

        parsed = self._parse_record(record)

        # 1. Strong identifier exact match
        identifier_candidates = self._find_identifier_candidates(parsed)

        if identifier_candidates:
            conflicts = self._detect_identifier_conflict(
                identifier_candidates,
                parsed,
                context="identifier",
            )

            if conflicts and self.strict_identifier_conflict:
                return self._make_conflict_result(
                    candidate_ids=identifier_candidates,
                    parsed=parsed,
                    conflicts=conflicts,
                    reason="identifier_conflict",
                    score=None,
                )

            entity_id = self._merge_entities_if_needed(identifier_candidates)
            self._update_entity(entity_id, parsed)

            return self._make_result(
                action="merged" if len(identifier_candidates) > 1 else "updated",
                entity_id=entity_id,
                reason="identifier_exact",
                score=1.0,
                parsed=parsed,
            )

        # 2. Exact normalized name match
        exact_name_candidates = self._find_exact_name_candidates(parsed)

        if exact_name_candidates:
            if len(exact_name_candidates) > 1 and not self._has_any_identifier(parsed):
                return self._make_ambiguous_result(
                    candidates=[
                        {
                            "entity_id": entity_id,
                            "score": 1.0,
                            "reason": "normalized_name_exact_collision",
                        }
                        for entity_id in sorted(exact_name_candidates)
                    ],
                    parsed=parsed,
                    reason="ambiguous_exact_name_collision",
                )

            if self._branch_qualifier_risk(
                exact_name_candidates,
                parsed,
                context="exact_name",
            ) and not self._has_any_identifier(parsed):
                return self._make_ambiguous_result(
                    candidates=[
                        {
                            "entity_id": entity_id,
                            "score": 1.0,
                            "reason": "branch_qualifier_risk",
                            "entity_branch_qualifiers": sorted(
                                self.entities[entity_id].branch_qualifiers
                            ),
                        }
                        for entity_id in sorted(exact_name_candidates)
                    ],
                    parsed=parsed,
                    reason="ambiguous_branch_qualifier_match",
                )

            pit_block = self._point_in_time_blocked_candidates(
                exact_name_candidates,
                parsed,
            )

            if pit_block:
                return self._make_ambiguous_result(
                    candidates=pit_block,
                    parsed=parsed,
                    reason="ambiguous_alias_validity_conflict",
                )

            conflicts = self._detect_identifier_conflict(
                exact_name_candidates,
                parsed,
                context="exact_name",
            )

            if conflicts and self.strict_identifier_conflict:
                return self._make_conflict_result(
                    candidate_ids=exact_name_candidates,
                    parsed=parsed,
                    conflicts=conflicts,
                    reason="exact_name_identifier_conflict",
                    score=1.0,
                )

            entity_id = self._merge_entities_if_needed(exact_name_candidates)
            self._update_entity(entity_id, parsed)

            return self._make_result(
                action="merged" if len(exact_name_candidates) > 1 else "updated",
                entity_id=entity_id,
                reason="normalized_name_exact",
                score=1.0,
                parsed=parsed,
            )

        # 3. Fuzzy / cross-lingual match
        fuzzy_candidates = self._find_fuzzy_candidates(parsed)

        if fuzzy_candidates:
            valid_candidates: List[Dict[str, Any]] = []
            blocked_candidates: List[Dict[str, Any]] = []
            conflicting_candidates: List[Dict[str, Any]] = []

            for candidate in fuzzy_candidates:
                candidate_entity_id = candidate["entity_id"]
                has_matching_identifier = bool(candidate.get("has_matching_identifier"))

                if "SIBLING_GUARD" in candidate.get("flags", []) and not has_matching_identifier:
                    blocked = dict(candidate)
                    blocked["blocked_reason"] = "sibling_guard_without_matching_identifier"
                    blocked_candidates.append(blocked)
                    continue

                if (
                    candidate.get("method") == "cross_lingual"
                    and not has_matching_identifier
                    and not self.allow_cross_lingual_without_identifier
                ):
                    blocked = dict(candidate)
                    blocked["blocked_reason"] = "cross_lingual_without_matching_identifier"
                    blocked_candidates.append(blocked)
                    continue

                if (
                    self._branch_qualifier_risk({candidate_entity_id}, parsed, context="fuzzy")
                    and not has_matching_identifier
                ):
                    blocked = dict(candidate)
                    blocked["blocked_reason"] = "branch_qualifier_risk_without_matching_identifier"
                    blocked_candidates.append(blocked)
                    continue

                pit_block = self._point_in_time_blocked_candidates(
                    {candidate_entity_id},
                    parsed,
                )

                if pit_block:
                    blocked = dict(candidate)
                    blocked["blocked_reason"] = "alias_validity_conflict"
                    blocked["pit_block"] = pit_block
                    blocked_candidates.append(blocked)
                    continue

                conflicts = self._detect_identifier_conflict(
                    {candidate_entity_id},
                    parsed,
                    context="fuzzy",
                )

                if conflicts and self.strict_identifier_conflict:
                    enriched = dict(candidate)
                    enriched["conflicts"] = conflicts
                    conflicting_candidates.append(enriched)
                    continue

                valid_candidates.append(candidate)

            if valid_candidates:
                best = valid_candidates[0]
                second = valid_candidates[1] if len(valid_candidates) > 1 else None

                if (
                    second is not None
                    and best["score"] - second["score"] <= self.ambiguous_margin
                ):
                    return self._make_ambiguous_result(
                        candidates=valid_candidates[:5],
                        parsed=parsed,
                        reason="ambiguous_fuzzy_match",
                        skipped_conflicting_candidates=conflicting_candidates[:5],
                        blocked_candidates=blocked_candidates[:5],
                    )

                entity_id = best["entity_id"]
                self._update_entity(entity_id, parsed)

                result = self._make_result(
                    action="updated",
                    entity_id=entity_id,
                    reason="fuzzy_name",
                    score=best["score"],
                    parsed=parsed,
                    candidate=best,
                )

                if conflicting_candidates:
                    result["skipped_conflicting_candidates"] = conflicting_candidates[:5]

                if blocked_candidates:
                    result["blocked_candidates"] = blocked_candidates[:5]

                return result

            if blocked_candidates:
                return self._make_ambiguous_result(
                    candidates=blocked_candidates[:5],
                    parsed=parsed,
                    reason="all_fuzzy_candidates_blocked_by_governance",
                    skipped_conflicting_candidates=conflicting_candidates[:5],
                    blocked_candidates=blocked_candidates[:5],
                )

            if conflicting_candidates:
                top = conflicting_candidates[0]

                return self._make_conflict_result(
                    candidate_ids={top["entity_id"]},
                    parsed=parsed,
                    conflicts=top.get("conflicts", []),
                    reason="all_fuzzy_candidates_conflicted",
                    score=top["score"],
                    candidates=conflicting_candidates[:5],
                )

        # 4. New entity
        entity_id = self._create_entity(parsed)

        return self._make_result(
            action="created",
            entity_id=entity_id,
            reason="new_entity",
            score=None,
            parsed=parsed,
        )

    def batch_resolve(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.resolve(record) for record in records]

    def resolve_name_at(self, entity_id: str, as_of: Any) -> Dict[str, Any]:
        if entity_id not in self.entities:
            raise KeyError(f"unknown entity_id: {entity_id}")

        as_of_iso = self._parse_date(as_of)

        if as_of_iso is None:
            raise ValueError("as_of must be parseable as YYYY-MM-DD or YYYYMMDD")

        entity = self.entities[entity_id]

        valid_aliases = []
        unknown_validity_aliases = []

        for alias_record in entity.alias_history:
            status = self._alias_temporal_status(alias_record, as_of_iso)

            if status == "valid":
                valid_aliases.append(alias_record.to_dict())
            elif status == "unknown":
                unknown_validity_aliases.append(alias_record.to_dict())

        return {
            "entity_id": entity_id,
            "as_of": as_of_iso,
            "valid_aliases": valid_aliases,
            "unknown_validity_aliases": unknown_validity_aliases,
        }

    # ============================================================
    # Parsing
    # ============================================================

    def _parse_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        quality_flags: List[str] = []

        source = str(
            record.get("source")
            or record.get("data_source")
            or record.get("origin")
            or "UNKNOWN"
        )

        as_of_date = self._parse_date(
            record.get("as_of_date")
            or record.get("report_date")
            or record.get("record_date")
            or record.get("filing_date")
            or record.get("기준일")
        )

        alias_valid_from = self._parse_date(
            record.get("alias_valid_from")
            or record.get("valid_from")
            or record.get("name_valid_from")
        )

        alias_valid_to = self._parse_date(
            record.get("alias_valid_to")
            or record.get("valid_to")
            or record.get("name_valid_to")
        )

        lei_raw = record.get("lei") or record.get("LEI") or record.get("legal_entity_identifier")
        lei = self.normalize_lei(lei_raw)
        if lei_raw and lei is None:
            quality_flags.append("INVALID_LEI")

        bic_raw = record.get("bic") or record.get("BIC") or record.get("swift_bic") or record.get("swift")
        bic = self.normalize_bic(bic_raw)
        if bic_raw and bic is None:
            quality_flags.append("INVALID_BIC")

        bic_root = self.bic_root(bic)

        corp_code = self.normalize_corp_code(
            record.get("corp_code")
            or record.get("dart_corp_code")
            or record.get("dartCorpCode")
        )

        corporate_registration_no = self.normalize_corporate_registration_no(
            record.get("corporate_registration_no")
            or record.get("corporate_registration_number")
            or record.get("corp_reg_no")
            or record.get("jurir_no")
            or record.get("jurirNo")
            or record.get("법인등록번호")
        )

        raw_business_no = (
            record.get("business_no")
            or record.get("business_number")
            or record.get("biz_no")
            or record.get("bizr_no")
            or record.get("bsn_no")
            or record.get("사업자번호")
        )

        raw_business_digits = (
            re.sub(r"\D", "", str(raw_business_no))
            if raw_business_no is not None
            else None
        )

        business_no = self.normalize_business_no(raw_business_no)

        if raw_business_digits and len(raw_business_digits) == 10 and business_no is None:
            quality_flags.append("INVALID_BUSINESS_NO_CHECKSUM")

        raw_names: List[str] = []

        for key in [
            "corp_name",
            "corp_nm",
            "corpName",
            "company_name",
            "companyName",
            "legal_name",
            "name",
            "english_name",
            "name_en",
            "trade_name",
            "법인명",
            "상호",
        ]:
            value = record.get(key)
            if value:
                raw_names.append(str(value))

        aliases = record.get("aliases") or []

        if isinstance(aliases, str):
            aliases = [aliases]

        if isinstance(aliases, list):
            raw_names.extend(str(alias) for alias in aliases if alias)

        aliases_clean: List[str] = []
        normalized_aliases: List[str] = []
        alias_records: List[AliasRecord] = []
        branch_qualifiers: Set[str] = set()

        seen_raw: Set[str] = set()
        seen_norm: Set[str] = set()
        seen_alias_record_keys: Set[Tuple[str, str, Optional[str], Optional[str], Optional[str], str]] = set()

        for raw_name in raw_names:
            stripped = str(raw_name).strip()

            if not stripped or stripped in seen_raw:
                continue

            seen_raw.add(stripped)
            aliases_clean.append(stripped)

            parts = self._normalize_name_parts(stripped)
            quality_flags.extend(parts["quality_flags"])
            branch_qualifiers.update(parts["branch_qualifiers"])

            norm = parts["core_name"]

            if norm and norm not in seen_norm:
                seen_norm.add(norm)
                normalized_aliases.append(norm)

            if norm:
                alias_record = AliasRecord(
                    raw_alias=stripped,
                    normalized_alias=norm,
                    valid_from=alias_valid_from,
                    valid_to=alias_valid_to,
                    observed_at=as_of_date,
                    source=source,
                )

                if alias_record.key() not in seen_alias_record_keys:
                    seen_alias_record_keys.add(alias_record.key())
                    alias_records.append(alias_record)

        if not normalized_aliases:
            quality_flags.append("NO_VALID_NORMALIZED_NAME")

        return {
            "lei": lei,
            "bic": bic,
            "bic_root": bic_root,
            "corp_code": corp_code,
            "corporate_registration_no": corporate_registration_no,
            "business_no": business_no,
            "raw_business_no": raw_business_no,
            "raw_business_digits": raw_business_digits,
            "aliases": aliases_clean,
            "normalized_aliases": normalized_aliases,
            "alias_records": alias_records,
            "branch_qualifiers": sorted(branch_qualifiers),
            "source": source,
            "as_of_date": as_of_date,
            "alias_valid_from": alias_valid_from,
            "alias_valid_to": alias_valid_to,
            "quality_flags": sorted(set(quality_flags)),
        }

    def _public_parsed(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(parsed)
        out["alias_records"] = [
            record.to_dict()
            if isinstance(record, AliasRecord)
            else record
            for record in parsed.get("alias_records", [])
        ]
        return out

    # ============================================================
    # Name normalization
    # ============================================================

    def _normalize_name_parts(self, name: Any) -> Dict[str, Any]:
        branch_qualifiers: Set[str] = set()
        quality_flags: List[str] = []

        if name is None:
            return {
                "core_name": "",
                "branch_qualifiers": branch_qualifiers,
                "quality_flags": ["EMPTY_NAME"],
            }

        s = str(name).strip()

        if not s:
            return {
                "core_name": "",
                "branch_qualifiers": branch_qualifiers,
                "quality_flags": ["EMPTY_NAME"],
            }

        s = unicodedata.normalize("NFKC", s)
        s = self._strip_latin_diacritics(s)
        s = s.upper()
        s = s.replace(" ", " ")
        s = s.replace("㈜", "(주)")

        s, captured = self._remove_brackets_preserving_qualifiers(s)

        for item in captured:
            q = self._normalize_branch_qualifier(item)
            if q:
                branch_qualifiers.add(q)

        if branch_qualifiers:
            quality_flags.append("BRANCH_QUALIFIER_PRESENT")

        legal_patterns = [
            r"\(\s*주\s*\)",
            r"주\s*식\s*회\s*사",
            r"유\s*한\s*책\s*임\s*회\s*사",
            r"유\s*한\s*회\s*사",
            r"합\s*자\s*회\s*사",
            r"합\s*명\s*회\s*사",
            r"사\s*단\s*법\s*인",
            r"재\s*단\s*법\s*인",
            r"학\s*교\s*법\s*인",
            r"의\s*료\s*법\s*인",
            r"농\s*업\s*회\s*사\s*법\s*인",
            r"어\s*업\s*회\s*사\s*법\s*인",
            r"영\s*농\s*조\s*합\s*법\s*인",
            r"영\s*어\s*조\s*합\s*법\s*인",
            r"사\s*회\s*적\s*협\s*동\s*조\s*합",
            r"협\s*동\s*조\s*합",
            r"株式会社",
            r"有限会社",
            r"合同会社",
            r"股份有限公司",
            r"有限责任公司",
            r"有限公司",
        ]

        for pattern in legal_patterns:
            s = re.sub(pattern, "", s)

        s = re.sub(r"\s+", "", s)

        # Keep unicode letters and digits.
        s = "".join(ch for ch in s if ch.isalnum())

        compact_legal_terms = [
            "주식회사", "유한책임회사", "유한회사", "합자회사", "합명회사",
            "사단법인", "재단법인", "학교법인", "의료법인", "농업회사법인",
            "어업회사법인", "영농조합법인", "영어조합법인", "사회적협동조합",
            "협동조합",
            "株式会社", "有限会社", "合同会社",
            "股份有限公司", "有限责任公司", "有限公司",
        ]

        for term in compact_legal_terms:
            s = s.replace(term, "")

        s = self._strip_global_legal_suffixes(s)

        if not s:
            quality_flags.append("EMPTY_CORE_NAME_AFTER_NORMALIZATION")

        return {
            "core_name": s,
            "branch_qualifiers": branch_qualifiers,
            "quality_flags": quality_flags,
        }

    def _remove_brackets_preserving_qualifiers(self, text: str) -> Tuple[str, List[str]]:
        captured: List[str] = []
        pattern = re.compile(r"[\(\[\{（［【](.*?)[\)\]\}）］】]")

        def repl(match: re.Match[str]) -> str:
            inner = match.group(1).strip()
            inner_norm = re.sub(r"\s+", "", inner.upper())

            legal_markers = {
                "주", "株", "유", "有限", "주식회사", "유한회사",
                "CO", "LTD", "INC", "LLC", "PLC",
            }

            if inner_norm in legal_markers:
                return ""

            captured.append(inner)
            return ""

        return pattern.sub(repl, text), captured

    def _normalize_branch_qualifier(self, value: Any) -> str:
        if value is None:
            return ""

        s = str(value).strip()
        s = unicodedata.normalize("NFKC", s)
        s = self._strip_latin_diacritics(s)
        s = s.upper()
        s = s.replace(" ", " ")
        s = re.sub(r"\s+", "", s)
        s = "".join(ch for ch in s if ch.isalnum())

        for token in ["주식회사", "유한회사", "유한책임회사", "법인"]:
            s = s.replace(token, "")

        return s

    @staticmethod
    def _strip_latin_diacritics(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    def _strip_global_legal_suffixes(self, compact_name: str) -> str:
        suffixes = [
            "PUBLICLIMITEDCOMPANY",
            "PRIVATE LIMITED",
            "COMPANYLIMITED",
            "CORPORATION",
            "INCORPORATED",
            "COLIMITED",
            "COLTD",
            "COINC",
            "LIMITED",
            "CORP",
            "LTD",
            "INC",
            "LLC",
            "LLP",
            "PLC",
            "LP",
            "CO",
            "GMBH",
            "AG",
            "SAS",
            "SARL",
            "SA",
            "BV",
            "NV",
            "SPA",
            "SRL",
            "OY",
            "ASA",
            "AS",
            "AB",
            "PTELTD",
            "PTYLTD",
            "PTE",
            "PTY",
            "KK",
            "GK",
        ]

        s = compact_name
        changed = True

        while changed:
            changed = False

            for suffix in suffixes:
                normalized_suffix = re.sub(r"\s+", "", suffix.upper())

                if len(s) > len(normalized_suffix) + 2 and s.endswith(normalized_suffix):
                    s = s[: -len(normalized_suffix)]
                    changed = True
                    break

        return s

    # ============================================================
    # Entity mutation / indexing
    # ============================================================

    def _create_entity(self, parsed: Dict[str, Any]) -> str:
        self._counter += 1
        entity_id = f"ENT-{self._counter:08d}"

        self.entities[entity_id] = Entity(entity_id=entity_id)
        self._update_entity(entity_id, parsed)

        return entity_id

    def _update_entity(self, entity_id: str, parsed: Dict[str, Any]) -> None:
        entity = self.entities[entity_id]

        self._remove_entity_from_indexes(entity)

        if parsed["lei"]:
            entity.leis.add(parsed["lei"])

        if parsed["bic"]:
            entity.bics.add(parsed["bic"])

        if parsed["bic_root"]:
            entity.bic_roots.add(parsed["bic_root"])

        if parsed["corp_code"]:
            entity.corp_codes.add(parsed["corp_code"])

        if parsed["corporate_registration_no"]:
            entity.corporate_registration_numbers.add(parsed["corporate_registration_no"])

        if parsed["business_no"]:
            entity.business_numbers.add(parsed["business_no"])

        for alias in parsed["aliases"]:
            entity.aliases.add(alias)

        for norm in parsed["normalized_aliases"]:
            entity.normalized_aliases.add(norm)

        existing_alias_keys = {a.key() for a in entity.alias_history}

        for alias_record in parsed["alias_records"]:
            if alias_record.key() not in existing_alias_keys:
                entity.alias_history.append(alias_record)
                existing_alias_keys.add(alias_record.key())

        for q in parsed["branch_qualifiers"]:
            entity.branch_qualifiers.add(q)

        entity.sources.add(parsed["source"])

        for flag in parsed["quality_flags"]:
            entity.quality_flags.add(flag)

        self._add_entity_to_indexes(entity)

    def _merge_entities_if_needed(self, entity_ids: Set[str]) -> str:
        if not entity_ids:
            raise ValueError("entity_ids cannot be empty")

        if len(entity_ids) == 1:
            return next(iter(entity_ids))

        primary_id = sorted(entity_ids)[0]
        primary = self.entities[primary_id]

        for entity_id in sorted(entity_ids):
            self._remove_entity_from_indexes(self.entities[entity_id])

        alias_keys = {a.key() for a in primary.alias_history}

        for entity_id in sorted(entity_ids):
            if entity_id == primary_id:
                continue

            entity = self.entities[entity_id]

            primary.leis.update(entity.leis)
            primary.bics.update(entity.bics)
            primary.bic_roots.update(entity.bic_roots)
            primary.corp_codes.update(entity.corp_codes)
            primary.corporate_registration_numbers.update(entity.corporate_registration_numbers)
            primary.business_numbers.update(entity.business_numbers)
            primary.aliases.update(entity.aliases)
            primary.normalized_aliases.update(entity.normalized_aliases)
            primary.branch_qualifiers.update(entity.branch_qualifiers)
            primary.sources.update(entity.sources)
            primary.quality_flags.update(entity.quality_flags)

            for alias_record in entity.alias_history:
                if alias_record.key() not in alias_keys:
                    primary.alias_history.append(alias_record)
                    alias_keys.add(alias_record.key())

            del self.entities[entity_id]

        self._add_entity_to_indexes(primary)

        return primary_id

    def _remove_entity_from_indexes(self, entity: Entity) -> None:
        entity_id = entity.entity_id

        for lei in entity.leis:
            if self.lei_index.get(lei) == entity_id:
                self.lei_index.pop(lei, None)

        for bic in entity.bics:
            if self.bic_index.get(bic) == entity_id:
                self.bic_index.pop(bic, None)

        for root in entity.bic_roots:
            ids = self.bic_root_index.get(root)
            if ids:
                ids.discard(entity_id)
                if not ids:
                    self.bic_root_index.pop(root, None)

        for corp_code in entity.corp_codes:
            if self.corp_code_index.get(corp_code) == entity_id:
                self.corp_code_index.pop(corp_code, None)

        for corporate_no in entity.corporate_registration_numbers:
            if self.corporate_registration_no_index.get(corporate_no) == entity_id:
                self.corporate_registration_no_index.pop(corporate_no, None)

        for business_no in entity.business_numbers:
            if self.business_no_index.get(business_no) == entity_id:
                self.business_no_index.pop(business_no, None)

        for norm_name in entity.normalized_aliases:
            ids = self.name_index.get(norm_name)

            if ids:
                ids.discard(entity_id)
                if not ids:
                    self.name_index.pop(norm_name, None)

            for block_key in self._blocking_keys(norm_name):
                block_ids = self.name_block_index.get(block_key)
                if block_ids:
                    block_ids.discard(entity_id)
                    if not block_ids:
                        self.name_block_index.pop(block_key, None)

            chosung = self._extract_chosung(norm_name)
            if chosung:
                ch_ids = self.chosung_index.get(chosung)
                if ch_ids:
                    ch_ids.discard(entity_id)
                    if not ch_ids:
                        self.chosung_index.pop(chosung, None)

            skeleton = self._cross_script_skeleton(norm_name)
            if skeleton:
                sk_ids = self.cross_skeleton_index.get(skeleton)
                if sk_ids:
                    sk_ids.discard(entity_id)
                    if not sk_ids:
                        self.cross_skeleton_index.pop(skeleton, None)

    def _add_entity_to_indexes(self, entity: Entity) -> None:
        entity_id = entity.entity_id

        for lei in entity.leis:
            self._set_unique_index(self.lei_index, lei, entity_id, "lei_index")

        for bic in entity.bics:
            self._set_unique_index(self.bic_index, bic, entity_id, "bic_index")

        for root in entity.bic_roots:
            self.bic_root_index.setdefault(root, set()).add(entity_id)

        for corp_code in entity.corp_codes:
            self._set_unique_index(self.corp_code_index, corp_code, entity_id, "corp_code_index")

        for corporate_no in entity.corporate_registration_numbers:
            self._set_unique_index(
                self.corporate_registration_no_index,
                corporate_no,
                entity_id,
                "corporate_registration_no_index",
            )

        for business_no in entity.business_numbers:
            self._set_unique_index(
                self.business_no_index,
                business_no,
                entity_id,
                "business_no_index",
            )

        for norm_name in entity.normalized_aliases:
            self.name_index.setdefault(norm_name, set()).add(entity_id)

            for block_key in self._blocking_keys(norm_name):
                self.name_block_index.setdefault(block_key, set()).add(entity_id)

            chosung = self._extract_chosung(norm_name)
            if chosung:
                self.chosung_index.setdefault(chosung, set()).add(entity_id)

            skeleton = self._cross_script_skeleton(norm_name)
            if skeleton:
                self.cross_skeleton_index.setdefault(skeleton, set()).add(entity_id)

    def _set_unique_index(
        self,
        index: Dict[str, str],
        key: str,
        entity_id: str,
        index_name: str,
    ) -> None:
        existing = index.get(key)

        if existing is not None and existing != entity_id:
            raise RuntimeError(
                f"index collision in {index_name}: key={key}, "
                f"existing={existing}, incoming={entity_id}"
            )

        index[key] = entity_id

    # ============================================================
    # Candidate search
    # ============================================================

    def _find_identifier_candidates(self, parsed: Dict[str, Any]) -> Set[str]:
        candidates: Set[str] = set()

        if parsed["lei"] and parsed["lei"] in self.lei_index:
            candidates.add(self.lei_index[parsed["lei"]])

        if parsed["bic"] and parsed["bic"] in self.bic_index:
            candidates.add(self.bic_index[parsed["bic"]])

        if parsed["corp_code"] and parsed["corp_code"] in self.corp_code_index:
            candidates.add(self.corp_code_index[parsed["corp_code"]])

        if (
            parsed["corporate_registration_no"]
            and parsed["corporate_registration_no"] in self.corporate_registration_no_index
        ):
            candidates.add(self.corporate_registration_no_index[parsed["corporate_registration_no"]])

        if parsed["business_no"] and parsed["business_no"] in self.business_no_index:
            candidates.add(self.business_no_index[parsed["business_no"]])

        return candidates

    def _find_exact_name_candidates(self, parsed: Dict[str, Any]) -> Set[str]:
        candidates: Set[str] = set()

        for norm in parsed["normalized_aliases"]:
            candidates.update(self.name_index.get(norm, set()))

        return candidates

    def _find_fuzzy_candidates(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        input_aliases = [
            alias
            for alias in parsed["normalized_aliases"]
            if len(alias) >= self.min_fuzzy_name_len
        ]

        if not input_aliases:
            return []

        candidate_entity_ids = self._candidate_entity_ids_by_block(input_aliases, parsed)

        if not candidate_entity_ids:
            return []

        candidates: List[Dict[str, Any]] = []

        for entity_id in candidate_entity_ids:
            entity = self.entities[entity_id]
            has_matching_identifier = self._has_matching_identifier(entity, parsed)

            best_score = 0.0
            best_input_alias = None
            best_entity_alias = None
            best_method = "none"
            best_flags: List[str] = []

            for input_alias in input_aliases:
                for entity_alias in entity.normalized_aliases:
                    score, method, flags = self._best_name_score(
                        input_alias,
                        entity_alias,
                        has_matching_identifier=has_matching_identifier,
                    )

                    if score > best_score:
                        best_score = score
                        best_input_alias = input_alias
                        best_entity_alias = entity_alias
                        best_method = method
                        best_flags = flags

            dynamic_threshold = (
                self.threshold if has_matching_identifier else self.no_identifier_threshold
            )

            if best_score == 1.0:
                dynamic_threshold = self.threshold

            if best_score >= dynamic_threshold:
                candidates.append({
                    "entity_id": entity_id,
                    "score": best_score,
                    "threshold": dynamic_threshold,
                    "input_alias": best_input_alias,
                    "matched_alias": best_entity_alias,
                    "method": best_method,
                    "flags": best_flags,
                    "has_matching_identifier": has_matching_identifier,
                })

        candidates.sort(key=lambda x: (-x["score"], x["entity_id"]))

        return candidates

    def _candidate_entity_ids_by_block(
        self,
        input_aliases: List[str],
        parsed: Dict[str, Any],
    ) -> Set[str]:
        counts: Counter[str] = Counter()

        # BIC root is only a candidate-expansion signal, not an auto-merge key.
        if parsed.get("bic_root"):
            for entity_id in self.bic_root_index.get(parsed["bic_root"], set()):
                counts[entity_id] += 5

        if not self.use_blocking:
            if len(self.entities) <= self.full_scan_limit:
                return set(self.entities.keys())

            logger.warning(
                "full fuzzy scan blocked because entity count exceeds full_scan_limit: %d",
                len(self.entities),
            )
            return set()

        for alias in input_aliases:
            for block_key in self._blocking_keys(alias):
                for entity_id in self.name_block_index.get(block_key, set()):
                    counts[entity_id] += 1

            chosung = self._extract_chosung(alias)
            if chosung:
                for entity_id in self.chosung_index.get(chosung, set()):
                    counts[entity_id] += 2

            skeleton = self._cross_script_skeleton(alias)
            if skeleton:
                for entity_id in self.cross_skeleton_index.get(skeleton, set()):
                    counts[entity_id] += 2

        if not counts:
            if len(self.entities) <= self.full_scan_limit:
                return set(self.entities.keys())

            return set()

        filtered = [
            (entity_id, count)
            for entity_id, count in counts.items()
            if count >= self.min_block_overlap
        ]

        if not filtered:
            filtered = list(counts.items())

        filtered.sort(key=lambda x: (-x[1], x[0]))

        return {
            entity_id
            for entity_id, _ in filtered[: self.max_block_candidates]
        }

    def _blocking_keys(self, normalized_name: str) -> Set[str]:
        name = normalized_name

        if not name:
            return set()

        keys: Set[str] = set()
        length = len(name)
        script = self._dominant_script(name)

        keys.add(f"SCRIPT:{script}")
        keys.add(f"LEN:{length // 2}")

        if length >= 1:
            keys.add(f"P1:{name[:1]}")
            keys.add(f"S1:{name[-1:]}")
            keys.add(f"GP1:{name[:1]}")

        if length >= 2:
            keys.add(f"P2:{name[:2]}")
            keys.add(f"S2:{name[-2:]}")

        if length >= 3:
            keys.add(f"P3:{name[:3]}")
            keys.add(f"S3:{name[-3:]}")

        for i in range(max(0, length - 1)):
            keys.add(f"BG:{name[i:i + 2]}")

        if length >= 5:
            for i in range(length - 2):
                keys.add(f"TG:{name[i:i + 3]}")

        chosung = self._extract_chosung(name)
        if chosung:
            keys.add(f"CH:{chosung}")
            if len(chosung) >= 2:
                keys.add(f"CHP2:{chosung[:2]}")

        skeleton = self._cross_script_skeleton(name)
        if skeleton:
            keys.add(f"XS:{skeleton}")
            if len(skeleton) >= 2:
                keys.add(f"XSP2:{skeleton[:2]}")

        return keys

    # ============================================================
    # Similarity / scripts
    # ============================================================

    def _best_name_score(
        self,
        a: str,
        b: str,
        *,
        has_matching_identifier: bool,
    ) -> Tuple[float, str, List[str]]:
        flags: List[str] = []

        if not a or not b:
            return 0.0, "none", ["EMPTY_NAME"]

        if a == b:
            return 1.0, "exact", []

        if min(len(a), len(b)) < self.min_fuzzy_name_len:
            return 0.0, "too_short", ["TOO_SHORT_FOR_FUZZY"]

        if self._sibling_guard(a, b, has_matching_identifier=has_matching_identifier):
            flags.append("SIBLING_GUARD")

        if self.algorithm == "jaro_winkler":
            fuzzy_score = self._jaro_winkler(
                a,
                b,
                prefix_scale=self.jaro_winkler_prefix_scale,
            )
        else:
            fuzzy_score = self._levenshtein_ratio(a, b)

        cross_score = 0.0

        if self._is_cross_lingual(a, b):
            cross_score, _ = self._cross_lingual_score(a, b)

        if cross_score > fuzzy_score:
            flags.append("CROSS_LINGUAL_HEURISTIC")
            return cross_score, "cross_lingual", flags

        return fuzzy_score, self.algorithm, flags

    def _sibling_guard(
        self,
        a: str,
        b: str,
        *,
        has_matching_identifier: bool,
    ) -> bool:
        if has_matching_identifier:
            return False

        if a == b:
            return False

        shorter, longer = (a, b) if len(a) < len(b) else (b, a)

        if not longer.startswith(shorter):
            return False

        remainder = longer[len(shorter):]

        if not remainder:
            return False

        if remainder in self.SIBLING_DISCRIMINATORS:
            return True

        return any(token and token in remainder for token in self.SIBLING_DISCRIMINATORS)

    def _is_cross_lingual(self, s1: str, s2: str) -> bool:
        script1 = self._dominant_script(s1)
        script2 = self._dominant_script(s2)

        return script1 != script2 and "OTHER" not in {script1, script2}

    def _cross_lingual_score(self, s1: str, s2: str) -> Tuple[float, str]:
        known = self._known_cross_lingual_score(s1, s2)

        if known > 0:
            return known, "known_alias_map"

        sk1 = self._cross_script_skeleton(s1)
        sk2 = self._cross_script_skeleton(s2)

        if not sk1 or not sk2:
            return 0.0, "cross_lingual_none"

        ratio = self._lcs_ratio(sk1, sk2)

        if ratio >= 0.70:
            return 0.91, "cross_script_lcs_high"

        if ratio >= 0.55:
            return 0.88, "cross_script_lcs_medium"

        return 0.0, "cross_lingual_low"

    def _known_cross_lingual_score(self, s1: str, s2: str) -> float:
        a = self._strip_global_legal_suffixes(s1)
        b = self._strip_global_legal_suffixes(s2)

        if a in self.cross_lingual_aliases and b in self.cross_lingual_aliases[a]:
            return 0.97

        if b in self.cross_lingual_aliases and a in self.cross_lingual_aliases[b]:
            return 0.97

        return 0.0

    def _normalize_cross_lingual_alias_map(
        self,
        alias_map: Dict[str, Set[str]],
    ) -> Dict[str, Set[str]]:
        normalized: Dict[str, Set[str]] = {}

        for k, values in alias_map.items():
            nk = self.normalize_name(k)

            if not nk:
                continue

            normalized.setdefault(nk, set())

            for v in values:
                nv = self.normalize_name(v)
                if nv:
                    normalized[nk].add(nv)

        return normalized

    def _dominant_script(self, text: str) -> str:
        counts: Counter[str] = Counter()

        for ch in text:
            code = ord(ch)

            if 0xAC00 <= code <= 0xD7A3:
                counts["KOREAN"] += 1
            elif 0x3040 <= code <= 0x30FF:
                counts["JAPANESE"] += 1
            elif 0x4E00 <= code <= 0x9FFF:
                counts["CJK"] += 1
            elif "A" <= ch <= "Z":
                counts["LATIN"] += 1
            elif ch.isdigit():
                counts["DIGIT"] += 1
            else:
                counts["OTHER"] += 1

        if not counts:
            return "OTHER"

        counts.pop("DIGIT", None)
        counts.pop("OTHER", None)

        if not counts:
            return "OTHER"

        return counts.most_common(1)[0][0]

    def _extract_chosung(self, text: str) -> str:
        result: List[str] = []

        for ch in text:
            code = ord(ch)

            if 0xAC00 <= code <= 0xD7A3:
                index = (code - 0xAC00) // 588
                result.append(self.CHOSUNG_LIST[index])

        return "".join(result)

    def _english_to_chosung_skeleton(self, text: str) -> str:
        mapping = {
            "B": "ㅂ", "P": "ㅂ", "V": "ㅂ", "F": "ㅂ",
            "J": "ㅈ", "Z": "ㅈ",
            "C": "ㅋ", "K": "ㄱ", "G": "ㄱ", "Q": "ㄱ",
            "D": "ㄷ", "T": "ㄷ",
            "S": "ㅅ", "X": "ㅅ",
            "M": "ㅁ", "N": "ㄴ",
            "L": "ㄹ", "R": "ㄹ",
            "H": "ㅎ",
        }

        skeleton: List[str] = []

        for ch in text:
            if ch in {"A", "E", "I", "O", "U", "Y", "W"}:
                continue

            mapped = mapping.get(ch)

            if mapped:
                skeleton.append(mapped)

        return self._collapse_consecutive("".join(skeleton))

    def _cross_script_skeleton(self, text: str) -> str:
        script = self._dominant_script(text)

        if script == "KOREAN":
            return self._extract_chosung(text)

        if script == "LATIN":
            return self._english_to_chosung_skeleton(text)

        if script in {"CJK", "JAPANESE"}:
            if not text:
                return ""

            return f"{text[:1]}{len(text)}{text[-1:]}"

        return ""

    @staticmethod
    def _collapse_consecutive(text: str) -> str:
        result: List[str] = []

        for ch in text:
            if not result or result[-1] != ch:
                result.append(ch)

        return "".join(result)

    # ============================================================
    # Conflict / governance
    # ============================================================

    def _detect_identifier_conflict(
        self,
        candidate_entity_ids: Set[str],
        parsed: Dict[str, Any],
        *,
        context: str,
    ) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []

        singleton_checks = [
            ("lei", "leis", parsed["lei"]),
            ("bic", "bics", parsed["bic"]),
            ("corp_code", "corp_codes", parsed["corp_code"]),
            (
                "corporate_registration_no",
                "corporate_registration_numbers",
                parsed["corporate_registration_no"],
            ),
        ]

        for field_name, entity_attr, incoming_value in singleton_checks:
            existing_values: Set[str] = set()

            for entity_id in candidate_entity_ids:
                entity = self.entities[entity_id]
                existing_values.update(getattr(entity, entity_attr))

            if len(existing_values) > 1:
                conflicts.append({
                    "type": "existing_singleton_identifier_conflict",
                    "field": field_name,
                    "existing_values": sorted(existing_values),
                    "candidate_entity_ids": sorted(candidate_entity_ids),
                })

            if incoming_value and existing_values and incoming_value not in existing_values:
                conflicts.append({
                    "type": "incoming_singleton_identifier_conflict",
                    "field": field_name,
                    "incoming_value": incoming_value,
                    "existing_values": sorted(existing_values),
                    "candidate_entity_ids": sorted(candidate_entity_ids),
                })

        incoming_business_no = parsed["business_no"]
        existing_business_numbers: Set[str] = set()

        for entity_id in candidate_entity_ids:
            entity = self.entities[entity_id]
            existing_business_numbers.update(entity.business_numbers)

        if (
            context in {"exact_name", "fuzzy"}
            and self.strict_business_no_on_name_match
            and incoming_business_no
            and existing_business_numbers
            and incoming_business_no not in existing_business_numbers
        ):
            conflicts.append({
                "type": "business_no_conflict_on_name_based_match",
                "field": "business_no",
                "incoming_value": incoming_business_no,
                "existing_values": sorted(existing_business_numbers),
                "context": context,
                "candidate_entity_ids": sorted(candidate_entity_ids),
            })

        return conflicts

    def _branch_qualifier_risk(
        self,
        candidate_entity_ids: Set[str],
        parsed: Dict[str, Any],
        *,
        context: str,
    ) -> bool:
        incoming = set(parsed.get("branch_qualifiers") or [])

        for entity_id in candidate_entity_ids:
            entity = self.entities[entity_id]
            existing = set(entity.branch_qualifiers)

            if not incoming and not existing:
                continue

            if incoming and existing and incoming & existing:
                continue

            if context in {"exact_name", "fuzzy"}:
                return True

        return False

    def _point_in_time_blocked_candidates(
        self,
        candidate_entity_ids: Set[str],
        parsed: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not self.enforce_alias_validity:
            return []

        as_of = parsed.get("as_of_date")

        if not as_of:
            return []

        blocked: List[Dict[str, Any]] = []

        for entity_id in candidate_entity_ids:
            entity = self.entities[entity_id]

            for norm in parsed["normalized_aliases"]:
                status = self._entity_alias_temporal_status(entity, norm, as_of)

                if status == "invalid":
                    blocked.append({
                        "entity_id": entity_id,
                        "score": 1.0,
                        "reason": "alias_outside_validity_window",
                        "normalized_alias": norm,
                        "as_of_date": as_of,
                    })

        return blocked

    def _entity_alias_temporal_status(
        self,
        entity: Entity,
        normalized_alias: str,
        as_of_iso: str,
    ) -> str:
        records = [
            r
            for r in entity.alias_history
            if r.normalized_alias == normalized_alias
        ]

        if not records:
            return "unknown"

        has_unknown = False

        for record in records:
            status = self._alias_temporal_status(record, as_of_iso)

            if status == "valid":
                return "valid"

            if status == "unknown":
                has_unknown = True

        return "unknown" if has_unknown else "invalid"

    def _alias_temporal_status(
        self,
        alias_record: AliasRecord,
        as_of_iso: str,
    ) -> str:
        if not alias_record.valid_from and not alias_record.valid_to:
            return "unknown"

        if alias_record.valid_from and as_of_iso < alias_record.valid_from:
            return "invalid"

        if alias_record.valid_to and as_of_iso > alias_record.valid_to:
            return "invalid"

        return "valid"

    def _has_any_identifier(self, parsed: Dict[str, Any]) -> bool:
        return bool(
            parsed.get("lei")
            or parsed.get("bic")
            or parsed.get("corp_code")
            or parsed.get("corporate_registration_no")
            or parsed.get("business_no")
        )

    def _has_matching_identifier(self, entity: Entity, parsed: Dict[str, Any]) -> bool:
        return bool(
            (parsed.get("lei") and parsed["lei"] in entity.leis)
            or (parsed.get("bic") and parsed["bic"] in entity.bics)
            or (parsed.get("corp_code") and parsed["corp_code"] in entity.corp_codes)
            or (
                parsed.get("corporate_registration_no")
                and parsed["corporate_registration_no"] in entity.corporate_registration_numbers
            )
            or (parsed.get("business_no") and parsed["business_no"] in entity.business_numbers)
        )

    # ============================================================
    # String similarity
    # ============================================================

    def _levenshtein_ratio(self, a: str, b: str) -> float:
        if a == b:
            return 1.0

        if not a or not b:
            return 0.0

        m, n = len(a), len(b)
        dp = list(range(n + 1))

        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i

            for j in range(1, n + 1):
                temp = dp[j]
                cost = 0 if a[i - 1] == b[j - 1] else 1

                dp[j] = min(
                    dp[j] + 1,
                    dp[j - 1] + 1,
                    prev + cost,
                )

                prev = temp

        return 1.0 - dp[n] / max(m, n)

    def _jaro_winkler(
        self,
        s1: str,
        s2: str,
        prefix_scale: Optional[float] = None,
        max_prefix: int = 4,
    ) -> float:
        if prefix_scale is None:
            prefix_scale = self.jaro_winkler_prefix_scale

        jaro = self._jaro_similarity(s1, s2)
        prefix = 0

        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                prefix += 1
            else:
                break

            if prefix == max_prefix:
                break

        return jaro + prefix * prefix_scale * (1 - jaro)

    def _jaro_similarity(self, s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)

        if len1 == 0 or len2 == 0:
            return 0.0

        match_distance = max(max(len1, len2) // 2 - 1, 0)

        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0

        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j]:
                    continue

                if s1[i] != s2[j]:
                    continue

                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        transpositions = 0
        k = 0

        for i in range(len1):
            if not s1_matches[i]:
                continue

            while not s2_matches[k]:
                k += 1

            if s1[i] != s2[k]:
                transpositions += 1

            k += 1

        transpositions /= 2

        return (
            matches / len1
            + matches / len2
            + (matches - transpositions) / matches
        ) / 3

    def _lcs_ratio(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0

        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m):
            for j in range(n):
                if a[i] == b[j]:
                    dp[i + 1][j + 1] = dp[i][j] + 1
                else:
                    dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])

        return dp[m][n] / max(m, n)

    # ============================================================
    # Date / result helpers
    # ============================================================

    @staticmethod
    def _parse_date(value: Any) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        s = str(value).strip()

        if not s:
            return None

        if re.fullmatch(r"\d{8}", s):
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s[:10]):
            return s[:10]

        return None

    def _make_result(
        self,
        *,
        action: str,
        entity_id: str,
        reason: str,
        score: Optional[float],
        parsed: Dict[str, Any],
        candidate: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {
            "action": action,
            "entity_id": entity_id,
            "entity": self.entities[entity_id].to_dict(),
            "match_reason": reason,
            "match_score": score,
            "conflicts": [],
            "parsed": self._public_parsed(parsed),
        }

        if candidate:
            result["matched_alias"] = candidate.get("matched_alias")
            result["input_alias"] = candidate.get("input_alias")
            result["match_method"] = candidate.get("method")
            result["match_flags"] = candidate.get("flags", [])
            result["match_threshold"] = candidate.get("threshold")
            result["has_matching_identifier"] = candidate.get("has_matching_identifier", False)

        return result

    def _make_conflict_result(
        self,
        *,
        candidate_ids: Set[str],
        parsed: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        reason: str,
        score: Optional[float],
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        result = {
            "action": "conflict",
            "entity_id": None,
            "entity": None,
            "match_reason": reason,
            "match_score": score,
            "candidate_entity_ids": sorted(candidate_ids),
            "conflicts": conflicts,
            "parsed": self._public_parsed(parsed),
        }

        if candidates is not None:
            result["candidates"] = candidates

        return result

    def _make_ambiguous_result(
        self,
        *,
        candidates: List[Dict[str, Any]],
        parsed: Dict[str, Any],
        reason: str,
        skipped_conflicting_candidates: Optional[List[Dict[str, Any]]] = None,
        blocked_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        result = {
            "action": "ambiguous",
            "entity_id": None,
            "entity": None,
            "match_reason": reason,
            "match_score": candidates[0].get("score") if candidates else None,
            "candidates": candidates,
            "conflicts": [],
            "parsed": self._public_parsed(parsed),
        }

        if skipped_conflicting_candidates:
            result["skipped_conflicting_candidates"] = skipped_conflicting_candidates

        if blocked_candidates:
            result["blocked_candidates"] = blocked_candidates

        return result

    # ============================================================
    # Diagnostics
    # ============================================================

    def dump_entities(self) -> List[Dict[str, Any]]:
        return [
            entity.to_dict()
            for _, entity in sorted(self.entities.items())
        ]

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "entity_count": len(self.entities),
            "lei_index_count": len(self.lei_index),
            "bic_index_count": len(self.bic_index),
            "bic_root_index_count": len(self.bic_root_index),
            "corp_code_index_count": len(self.corp_code_index),
            "corporate_registration_no_index_count": len(self.corporate_registration_no_index),
            "business_no_index_count": len(self.business_no_index),
            "name_index_count": len(self.name_index),
            "name_block_index_count": len(self.name_block_index),
            "chosung_index_count": len(self.chosung_index),
            "cross_skeleton_index_count": len(self.cross_skeleton_index),
            "algorithm": self.algorithm,
            "threshold": self.threshold,
            "no_identifier_threshold": self.no_identifier_threshold,
            "jaro_winkler_prefix_scale": self.jaro_winkler_prefix_scale,
            "use_blocking": self.use_blocking,
            "allow_cross_lingual_without_identifier": self.allow_cross_lingual_without_identifier,
            "enforce_alias_validity": self.enforce_alias_validity,
        }
