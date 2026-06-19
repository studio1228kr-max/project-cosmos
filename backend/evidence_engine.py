from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import math


class SourceTier(str, Enum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    RECONCILED = "RECONCILED"
    REVIEWED = "REVIEWED"
    PENDING_REVIEW = "PENDING_REVIEW"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"


class ExtractionMethod(str, Enum):
    API = "API"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    PDF_TEXT = "PDF_TEXT"
    OCR = "OCR"
    LLM_EXTRACTION = "LLM_EXTRACTION"
    EMAIL_OR_CHAT = "EMAIL_OR_CHAT"
    MODEL_ASSUMPTION = "MODEL_ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class Criticality(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ModelUseCategory(str, Enum):
    BASE_CASE = "BASE_CASE"
    STRESS_CASE = "STRESS_CASE"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    REJECTED = "REJECTED"


class EvidenceGate(str, Enum):
    PASS = "PASS"
    WATCH = "WATCH"
    HOLD = "HOLD"
    REJECT = "REJECT"


class IssueSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"
    REJECT = "REJECT"


class OverrideDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class OutcomeTag(str, Enum):
    UNKNOWN = "UNKNOWN"
    GOOD = "GOOD"
    BAD = "BAD"
    DEFAULT = "DEFAULT"
    LOSS = "LOSS"
    RECOVERED = "RECOVERED"


SOURCE_TIER_BASE_SCORE: Dict[SourceTier, float] = {
    SourceTier.S1: 95.0,
    SourceTier.S2: 85.0,
    SourceTier.S3: 72.0,
    SourceTier.S4: 52.0,
    SourceTier.S5: 25.0,
}

SOURCE_TIER_RANK: Dict[SourceTier, int] = {
    SourceTier.S1: 1,
    SourceTier.S2: 2,
    SourceTier.S3: 3,
    SourceTier.S4: 4,
    SourceTier.S5: 5,
}

VERIFICATION_SCORE: Dict[VerificationStatus, float] = {
    VerificationStatus.VERIFIED: 100.0,
    VerificationStatus.RECONCILED: 95.0,
    VerificationStatus.REVIEWED: 85.0,
    VerificationStatus.PENDING_REVIEW: 60.0,
    VerificationStatus.UNVERIFIED: 35.0,
    VerificationStatus.CONTRADICTED: 0.0,
    VerificationStatus.REJECTED: 0.0,
}

EXTRACTION_SCORE: Dict[ExtractionMethod, float] = {
    ExtractionMethod.API: 95.0,
    ExtractionMethod.HUMAN_REVIEWED: 95.0,
    ExtractionMethod.MANUAL_ENTRY: 85.0,
    ExtractionMethod.PDF_TEXT: 78.0,
    ExtractionMethod.OCR: 62.0,
    ExtractionMethod.LLM_EXTRACTION: 58.0,
    ExtractionMethod.EMAIL_OR_CHAT: 45.0,
    ExtractionMethod.MODEL_ASSUMPTION: 40.0,
    ExtractionMethod.UNKNOWN: 30.0,
}

CRITICALITY_WEIGHT: Dict[Criticality, float] = {
    Criticality.P0: 2.00,
    Criticality.P1: 1.50,
    Criticality.P2: 1.00,
    Criticality.P3: 0.50,
}


@dataclass(frozen=True)
class DealMaster:
    deal_id: str
    deal_name: str
    asset_class: str
    deal_type: str

    currency: str = "KRW"
    jurisdiction: Optional[str] = None
    borrower: Optional[str] = None
    sponsor: Optional[str] = None
    origination_channel: Optional[str] = None
    strategy: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DealMaster":
        required = {"deal_id", "deal_name", "asset_class", "deal_type"}
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"deal_master missing required fields: {sorted(missing)}")

        known = {
            "deal_id", "deal_name", "asset_class", "deal_type", "currency",
            "jurisdiction", "borrower", "sponsor", "origination_channel", "strategy",
        }

        extra = {k: v for k, v in raw.items() if k not in known}

        return cls(
            deal_id=str(raw["deal_id"]),
            deal_name=str(raw["deal_name"]),
            asset_class=str(raw["asset_class"]),
            deal_type=str(raw["deal_type"]),
            currency=str(raw.get("currency", "KRW")),
            jurisdiction=raw.get("jurisdiction"),
            borrower=raw.get("borrower"),
            sponsor=raw.get("sponsor"),
            origination_channel=raw.get("origination_channel"),
            strategy=raw.get("strategy"),
            extra=extra,
        )


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    source_name: str
    source_type: str
    source_tier: SourceTier

    document_id: Optional[str] = None
    page_number: Optional[int] = None
    line_reference: Optional[str] = None
    excerpt: Optional[str] = None
    source_date: Optional[date] = None
    received_at: Optional[datetime] = None
    owner: Optional[str] = None
    url_or_path: Optional[str] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "SourceReference":
        return cls(
            source_id=str(raw.get("source_id", "")),
            source_name=str(raw.get("source_name", "")),
            source_type=str(raw.get("source_type", "")),
            source_tier=parse_enum(SourceTier, raw.get("source_tier"), SourceTier.S5),
            document_id=raw.get("document_id"),
            page_number=raw.get("page_number"),
            line_reference=raw.get("line_reference"),
            excerpt=raw.get("excerpt"),
            source_date=parse_date(raw.get("source_date")),
            received_at=parse_datetime(raw.get("received_at")),
            owner=raw.get("owner"),
            url_or_path=raw.get("url_or_path"),
        )


@dataclass(frozen=True)
class CrossCheck:
    value: Any
    source_tier: SourceTier
    verification_status: VerificationStatus = VerificationStatus.REVIEWED
    source_name: Optional[str] = None
    tolerance_abs: Optional[float] = None
    tolerance_pct: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CrossCheck":
        return cls(
            value=raw.get("value"),
            source_tier=parse_enum(SourceTier, raw.get("source_tier"), SourceTier.S5),
            verification_status=parse_enum(
                VerificationStatus,
                raw.get("verification_status"),
                VerificationStatus.REVIEWED,
            ),
            source_name=raw.get("source_name"),
            tolerance_abs=raw.get("tolerance_abs"),
            tolerance_pct=raw.get("tolerance_pct"),
        )


@dataclass(frozen=True)
class EvidenceItem:
    field_name: str
    value: Any
    unit: Optional[str]
    source: SourceReference

    as_of_date: Optional[date] = None
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    criticality: Criticality = Criticality.P2

    raw_value: Any = None
    adjustment_amount: Optional[float] = None
    adjustment_reason: Optional[str] = None

    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    cross_checks: List[CrossCheck] = field(default_factory=list)
    notes: Optional[str] = None

    temporary_substitute: bool = False
    permanent_substitute: bool = False
    intended_tail_use: bool = False
    intended_narrative_use: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EvidenceItem":
        source_raw = raw.get("source", {})
        if not source_raw:
            source_raw = {
                "source_id": raw.get("source_id", ""),
                "source_name": raw.get("source_name", ""),
                "source_type": raw.get("source_type", ""),
                "source_tier": raw.get("source_tier", "S5"),
                "document_id": raw.get("document_id"),
                "page_number": raw.get("page_number"),
                "line_reference": raw.get("line_reference"),
                "excerpt": raw.get("excerpt"),
                "source_date": raw.get("source_date"),
                "received_at": raw.get("received_at"),
                "owner": raw.get("owner"),
                "url_or_path": raw.get("url_or_path"),
            }

        metadata = dict(raw.get("metadata", {}))

        return cls(
            field_name=str(raw["field_name"]),
            value=raw.get("value"),
            unit=raw.get("unit"),
            source=SourceReference.from_mapping(source_raw),
            as_of_date=parse_date(raw.get("as_of_date")),
            extraction_method=parse_enum(
                ExtractionMethod,
                raw.get("extraction_method"),
                ExtractionMethod.UNKNOWN,
            ),
            verification_status=parse_enum(
                VerificationStatus,
                raw.get("verification_status"),
                VerificationStatus.UNVERIFIED,
            ),
            criticality=parse_enum(Criticality, raw.get("criticality"), Criticality.P2),
            raw_value=raw.get("raw_value"),
            adjustment_amount=raw.get("adjustment_amount"),
            adjustment_reason=raw.get("adjustment_reason"),
            reviewer=raw.get("reviewer"),
            reviewed_at=parse_datetime(raw.get("reviewed_at")),
            cross_checks=[
                CrossCheck.from_mapping(x) if isinstance(x, Mapping) else x
                for x in raw.get("cross_checks", [])
            ],
            notes=raw.get("notes"),
            temporary_substitute=bool(raw.get("temporary_substitute", metadata.get("temporary_substitute", False))),
            permanent_substitute=bool(raw.get("permanent_substitute", metadata.get("permanent_substitute", False))),
            intended_tail_use=bool(raw.get("intended_tail_use", metadata.get("intended_tail_use", False))),
            intended_narrative_use=bool(raw.get("intended_narrative_use", metadata.get("intended_narrative_use", False))),
            metadata=metadata,
        )


@dataclass(frozen=True)
class FieldPolicy:
    required: bool = False

    min_score_for_base_case: float = 80.0
    min_score_for_external_reliance: float = 85.0

    min_source_score_for_base: float = 70.0
    min_verification_score_for_base: float = 85.0
    min_traceability_score_for_base: float = 60.0
    min_cross_check_score_for_base: float = 55.0
    min_recency_score_for_base: float = 55.0

    require_document_id: bool = True
    require_page_or_line: bool = False
    require_excerpt: bool = False
    require_reviewer_for_base_case: bool = True

    max_age_days: Optional[int] = None
    stale_blocks_base_case: bool = False
    stale_blocks_field: bool = False

    require_cross_check_for_p0_base: bool = True
    require_cross_check_for_p1_base: bool = False
    high_tier_mismatch_blocks_field: bool = True
    no_cross_check_blocks_p0_base: bool = True

    allow_temporary_substitute_in_base_case: bool = False
    permanent_low_tier_substitute_rejects: bool = True
    allow_low_tier_key_field_in_base_case: bool = False

    tolerance_abs: Optional[float] = None
    tolerance_pct: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "FieldPolicy":
        return cls(
            required=bool(raw.get("required", False)),
            min_score_for_base_case=float(raw.get("min_score_for_base_case", 80.0)),
            min_score_for_external_reliance=float(raw.get("min_score_for_external_reliance", 85.0)),
            min_source_score_for_base=float(raw.get("min_source_score_for_base", 70.0)),
            min_verification_score_for_base=float(raw.get("min_verification_score_for_base", 85.0)),
            min_traceability_score_for_base=float(raw.get("min_traceability_score_for_base", 60.0)),
            min_cross_check_score_for_base=float(raw.get("min_cross_check_score_for_base", 55.0)),
            min_recency_score_for_base=float(raw.get("min_recency_score_for_base", 55.0)),
            require_document_id=bool(raw.get("require_document_id", True)),
            require_page_or_line=bool(raw.get("require_page_or_line", False)),
            require_excerpt=bool(raw.get("require_excerpt", False)),
            require_reviewer_for_base_case=bool(raw.get("require_reviewer_for_base_case", True)),
            max_age_days=raw.get("max_age_days"),
            stale_blocks_base_case=bool(raw.get("stale_blocks_base_case", False)),
            stale_blocks_field=bool(raw.get("stale_blocks_field", False)),
            require_cross_check_for_p0_base=bool(raw.get("require_cross_check_for_p0_base", True)),
            require_cross_check_for_p1_base=bool(raw.get("require_cross_check_for_p1_base", False)),
            high_tier_mismatch_blocks_field=bool(raw.get("high_tier_mismatch_blocks_field", True)),
            no_cross_check_blocks_p0_base=bool(raw.get("no_cross_check_blocks_p0_base", True)),
            allow_temporary_substitute_in_base_case=bool(raw.get("allow_temporary_substitute_in_base_case", False)),
            permanent_low_tier_substitute_rejects=bool(raw.get("permanent_low_tier_substitute_rejects", True)),
            allow_low_tier_key_field_in_base_case=bool(raw.get("allow_low_tier_key_field_in_base_case", False)),
            tolerance_abs=raw.get("tolerance_abs"),
            tolerance_pct=raw.get("tolerance_pct"),
        )


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    severity: IssueSeverity
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass(frozen=True)
class DimensionScore:
    score: float
    grade: str
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceProfile:
    source: DimensionScore
    verification: DimensionScore
    traceability: DimensionScore
    extraction: DimensionScore
    recency: DimensionScore
    cross_check: DimensionScore
    adjustment: DimensionScore

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "verification": self.verification.to_dict(),
            "traceability": self.traceability.to_dict(),
            "extraction": self.extraction.to_dict(),
            "recency": self.recency.to_dict(),
            "cross_check": self.cross_check.to_dict(),
            "adjustment": self.adjustment.to_dict(),
        }


@dataclass(frozen=True)
class EvidenceUseTags:
    model_use_category: ModelUseCategory
    external_reliance_allowed: bool
    narrative_use_allowed: bool
    tail_use_only: bool
    requires_reverification: bool
    base_case_blocked_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_use_category": self.model_use_category.value,
            "external_reliance_allowed": self.external_reliance_allowed,
            "narrative_use_allowed": self.narrative_use_allowed,
            "tail_use_only": self.tail_use_only,
            "requires_reverification": self.requires_reverification,
            "base_case_blocked_reason": self.base_case_blocked_reason,
        }


@dataclass(frozen=True)
class EvidenceScore:
    field_name: str
    value: Any
    unit: Optional[str]

    confidence_score: float
    confidence_grade: str

    profile: EvidenceProfile
    use_tags: EvidenceUseTags

    source_tier: SourceTier
    verification_status: VerificationStatus
    criticality: Criticality
    source: SourceReference

    issues: List[EvidenceIssue]

    used_in_model: bool = False
    overridden: bool = False
    override_direction: Optional[OverrideDirection] = None
    override_reason: Optional[str] = None
    outcome_tag: OutcomeTag = OutcomeTag.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "unit": self.unit,
            "confidence_score": self.confidence_score,
            "confidence_grade": self.confidence_grade,
            "profile": self.profile.to_dict(),
            "use_tags": self.use_tags.to_dict(),
            "source_tier": self.source_tier.value,
            "verification_status": self.verification_status.value,
            "criticality": self.criticality.value,
            "source": asdict(self.source),
            "issues": [x.to_dict() for x in self.issues],
            "used_in_model": self.used_in_model,
            "overridden": self.overridden,
            "override_direction": self.override_direction.value if self.override_direction else None,
            "override_reason": self.override_reason,
            "outcome_tag": self.outcome_tag.value,
        }


@dataclass(frozen=True)
class FieldEvidenceAggregate:
    field_name: str
    selected: Optional[EvidenceScore]
    alternatives: List[EvidenceScore]

    field_conflict: bool
    p0_ready: bool
    required_ready: bool

    blockers: List[EvidenceIssue]
    warnings: List[EvidenceIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "selected": self.selected.to_dict() if self.selected else None,
            "alternatives": [x.to_dict() for x in self.alternatives],
            "field_conflict": self.field_conflict,
            "p0_ready": self.p0_ready,
            "required_ready": self.required_ready,
            "blockers": [x.to_dict() for x in self.blockers],
            "warnings": [x.to_dict() for x in self.warnings],
        }


@dataclass(frozen=True)
class EvidencePackage:
    deal_master: DealMaster
    gate: EvidenceGate

    overall_score: float
    model_grade: str

    p0_ready: bool
    required_ready: bool
    external_reliance_ready: bool

    field_results: List[FieldEvidenceAggregate]

    base_case_inputs: Dict[str, Any]
    stress_case_inputs: Dict[str, Any]
    internal_review_inputs: Dict[str, Any]
    rejected_inputs: Dict[str, Any]
    narrative_inputs: Dict[str, Any]
    tail_only_inputs: Dict[str, Any]

    missing_required_fields: List[str]
    blockers: List[EvidenceIssue]
    warnings: List[EvidenceIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_master": asdict(self.deal_master),
            "gate": self.gate.value,
            "overall_score": self.overall_score,
            "model_grade": self.model_grade,
            "p0_ready": self.p0_ready,
            "required_ready": self.required_ready,
            "external_reliance_ready": self.external_reliance_ready,
            "field_results": [x.to_dict() for x in self.field_results],
            "base_case_inputs": self.base_case_inputs,
            "stress_case_inputs": self.stress_case_inputs,
            "internal_review_inputs": self.internal_review_inputs,
            "rejected_inputs": self.rejected_inputs,
            "narrative_inputs": self.narrative_inputs,
            "tail_only_inputs": self.tail_only_inputs,
            "missing_required_fields": self.missing_required_fields,
            "blockers": [x.to_dict() for x in self.blockers],
            "warnings": [x.to_dict() for x in self.warnings],
        }


def evaluate_evidence_engine(
    deal_master: Union[DealMaster, Mapping[str, Any]],
    evidence_items: Sequence[Union[EvidenceItem, Mapping[str, Any]]],
    required_fields: Optional[Sequence[str]] = None,
    p0_fields: Optional[Sequence[str]] = None,
    field_policies: Optional[Mapping[str, Union[FieldPolicy, Mapping[str, Any]]]] = None,
    default_policy: Optional[FieldPolicy] = None,
    evaluation_date: Optional[date] = None,
) -> EvidencePackage:
    dm = normalize_deal_master(deal_master)
    items = [normalize_evidence_item(x) for x in evidence_items]

    policies = normalize_field_policies(field_policies)
    default = default_policy or FieldPolicy()
    eval_date = evaluation_date or date.today()

    required = set(required_fields or [])
    p0_set = set(p0_fields or [])

    for field_name, policy in policies.items():
        if policy.required:
            required.add(field_name)

    grouped: Dict[str, List[EvidenceItem]] = {}
    for item in items:
        grouped.setdefault(item.field_name, []).append(item)
        if item.criticality == Criticality.P0:
            p0_set.add(item.field_name)

    missing_required = sorted([x for x in required if x not in grouped])

    field_results: List[FieldEvidenceAggregate] = []
    for field_name, field_items in sorted(grouped.items()):
        policy = policies.get(field_name, default)
        scores = [
            score_evidence_item(item, policy=policy, evaluation_date=eval_date)
            for item in field_items
        ]
        field_results.append(
            aggregate_field_scores(
                field_name=field_name,
                scores=scores,
                policy=policy,
                required=field_name in required,
                p0=field_name in p0_set,
            )
        )

    base_case_inputs: Dict[str, Any] = {}
    stress_case_inputs: Dict[str, Any] = {}
    internal_review_inputs: Dict[str, Any] = {}
    rejected_inputs: Dict[str, Any] = {}
    narrative_inputs: Dict[str, Any] = {}
    tail_only_inputs: Dict[str, Any] = {}

    blockers: List[EvidenceIssue] = []
    warnings: List[EvidenceIssue] = []

    for field_name in missing_required:
        blockers.append(issue(
            code=f"{field_name}:MISSING_REQUIRED_FIELD",
            severity=IssueSeverity.BLOCKER,
            message=f"Required field '{field_name}' has no evidence item.",
        ))

    weighted_scores: List[Tuple[float, float]] = []

    p0_ready = True
    required_ready = True
    external_reliance_ready = True

    seen_fields = {r.field_name for r in field_results}

    for field_name in p0_set:
        if field_name not in seen_fields:
            p0_ready = False
            blockers.append(issue(
                code=f"{field_name}:MISSING_P0_FIELD",
                severity=IssueSeverity.BLOCKER,
                message=f"P0 field '{field_name}' is missing.",
            ))

    for aggregate in field_results:
        blockers.extend(aggregate.blockers)
        warnings.extend(aggregate.warnings)

        selected = aggregate.selected
        if not selected:
            continue

        if selected.criticality == Criticality.P0 and not aggregate.p0_ready:
            p0_ready = False

        if aggregate.field_name in required and not aggregate.required_ready:
            required_ready = False

        if not selected.use_tags.external_reliance_allowed and selected.criticality in {Criticality.P0, Criticality.P1}:
            external_reliance_ready = False

        weighted_scores.append(
            (selected.confidence_score, CRITICALITY_WEIGHT[selected.criticality])
        )

        category = selected.use_tags.model_use_category

        if category == ModelUseCategory.BASE_CASE:
            base_case_inputs[selected.field_name] = selected.value
        elif category == ModelUseCategory.STRESS_CASE:
            stress_case_inputs[selected.field_name] = selected.value
        elif category == ModelUseCategory.INTERNAL_REVIEW:
            internal_review_inputs[selected.field_name] = selected.value
        else:
            rejected_inputs[selected.field_name] = selected.value

        if selected.use_tags.narrative_use_allowed:
            narrative_inputs[selected.field_name] = selected.value

        if selected.use_tags.tail_use_only:
            tail_only_inputs[selected.field_name] = selected.value

    overall_score = round(weighted_average(weighted_scores), 2)
    model_grade = score_to_grade(overall_score)

    gate = determine_evidence_gate_v02(
        overall_score=overall_score,
        p0_ready=p0_ready,
        required_ready=required_ready and not missing_required,
        external_reliance_ready=external_reliance_ready,
        blockers=blockers,
        field_results=field_results,
    )

    return EvidencePackage(
        deal_master=dm,
        gate=gate,
        overall_score=overall_score,
        model_grade=model_grade,
        p0_ready=p0_ready,
        required_ready=required_ready and not missing_required,
        external_reliance_ready=external_reliance_ready,
        field_results=field_results,
        base_case_inputs=base_case_inputs,
        stress_case_inputs=stress_case_inputs,
        internal_review_inputs=internal_review_inputs,
        rejected_inputs=rejected_inputs,
        narrative_inputs=narrative_inputs,
        tail_only_inputs=tail_only_inputs,
        missing_required_fields=missing_required,
        blockers=dedupe_issues(blockers),
        warnings=dedupe_issues(warnings),
    )


def score_evidence_item(
    item: EvidenceItem,
    policy: FieldPolicy,
    evaluation_date: date,
) -> EvidenceScore:
    issues: List[EvidenceIssue] = []

    source_score = SOURCE_TIER_BASE_SCORE[item.source.source_tier]
    verification_score = VERIFICATION_SCORE[item.verification_status]
    traceability_score, traceability_flags = calculate_traceability_score(item, policy)
    extraction_score = EXTRACTION_SCORE[item.extraction_method]
    recency_score, recency_flags = calculate_recency_score(item, policy, evaluation_date)
    cross_check_score, cross_check_flags, cross_check_issues = calculate_cross_check_score(item, policy)
    adjustment_score, adjustment_flags = calculate_adjustment_score(item)

    issues.extend(cross_check_issues)

    confidence_score = (
        source_score * 0.25
        + verification_score * 0.22
        + traceability_score * 0.16
        + extraction_score * 0.10
        + recency_score * 0.10
        + cross_check_score * 0.12
        + adjustment_score * 0.05
    )

    if item.verification_status in {VerificationStatus.CONTRADICTED, VerificationStatus.REJECTED}:
        confidence_score = min(confidence_score, 20.0)
        issues.append(issue(
            code=f"{item.field_name}:CONTRADICTED_OR_REJECTED",
            severity=IssueSeverity.REJECT,
            message="Evidence is contradicted or rejected.",
        ))

    if policy.require_document_id and not item.source.document_id:
        confidence_score -= 10.0
        issues.append(issue(
            code=f"{item.field_name}:MISSING_DOCUMENT_ID",
            severity=IssueSeverity.WARNING,
            message="Source document id is missing.",
        ))

    if policy.require_page_or_line and not (item.source.page_number or item.source.line_reference):
        confidence_score -= 8.0
        issues.append(issue(
            code=f"{item.field_name}:MISSING_PAGE_OR_LINE",
            severity=IssueSeverity.WARNING,
            message="Page number or line reference is missing.",
        ))

    if policy.require_excerpt and not item.source.excerpt:
        confidence_score -= 8.0
        issues.append(issue(
            code=f"{item.field_name}:MISSING_EXCERPT",
            severity=IssueSeverity.WARNING,
            message="Source excerpt is missing.",
        ))

    if item.extraction_method == ExtractionMethod.LLM_EXTRACTION and item.verification_status not in {
        VerificationStatus.VERIFIED,
        VerificationStatus.RECONCILED,
        VerificationStatus.REVIEWED,
    }:
        confidence_score -= 12.0
        issues.append(issue(
            code=f"{item.field_name}:LLM_EXTRACTION_NOT_REVIEWED",
            severity=IssueSeverity.WARNING,
            message="LLM-extracted evidence has not been human-reviewed.",
        ))

    if (
        item.source.source_tier in {SourceTier.S4, SourceTier.S5}
        and item.criticality in {Criticality.P0, Criticality.P1}
    ):
        confidence_score -= 15.0
        severity = IssueSeverity.BLOCKER if not policy.allow_low_tier_key_field_in_base_case else IssueSeverity.WARNING
        issues.append(issue(
            code=f"{item.field_name}:LOW_TIER_SOURCE_FOR_KEY_FIELD",
            severity=severity,
            message="P0/P1 field is supported only by low-tier evidence.",
        ))

    if item.temporary_substitute:
        issues.append(issue(
            code=f"{item.field_name}:TEMPORARY_SUBSTITUTE",
            severity=IssueSeverity.BLOCKER,
            message="Evidence is a temporary substitute and must be replaced by higher-tier evidence.",
        ))
        if not policy.allow_temporary_substitute_in_base_case:
            confidence_score = min(confidence_score, 65.0)

    if item.permanent_substitute and item.source.source_tier in {SourceTier.S4, SourceTier.S5}:
        severity = IssueSeverity.REJECT if policy.permanent_low_tier_substitute_rejects else IssueSeverity.BLOCKER
        issues.append(issue(
            code=f"{item.field_name}:PERMANENT_LOW_TIER_SUBSTITUTE",
            severity=severity,
            message="Permanent reliance on low-tier substitute evidence is not acceptable.",
        ))
        confidence_score = min(confidence_score, 35.0)

    if "STALE_DATA_BLOCKER" in recency_flags:
        severity = IssueSeverity.BLOCKER if policy.stale_blocks_field else IssueSeverity.WARNING
        issues.append(issue(
            code=f"{item.field_name}:STALE_DATA",
            severity=severity,
            message="Evidence is stale for this field policy.",
        ))

    if "NO_CROSS_CHECK" in cross_check_flags and item.criticality == Criticality.P0 and policy.no_cross_check_blocks_p0_base:
        issues.append(issue(
            code=f"{item.field_name}:P0_NO_CROSS_CHECK",
            severity=IssueSeverity.BLOCKER,
            message="P0 field has no cross-check evidence.",
        ))

    confidence_score = round(clamp(confidence_score, 0.0, 100.0), 2)

    profile = EvidenceProfile(
        source=dim(source_score, flags=[]),
        verification=dim(verification_score, flags=[]),
        traceability=dim(traceability_score, flags=traceability_flags),
        extraction=dim(extraction_score, flags=[]),
        recency=dim(recency_score, flags=recency_flags),
        cross_check=dim(cross_check_score, flags=cross_check_flags),
        adjustment=dim(adjustment_score, flags=adjustment_flags),
    )

    use_tags = determine_use_tags_v02(
        item=item,
        policy=policy,
        confidence_score=confidence_score,
        profile=profile,
        issues=issues,
    )

    return EvidenceScore(
        field_name=item.field_name,
        value=item.value,
        unit=item.unit,
        confidence_score=confidence_score,
        confidence_grade=score_to_grade(confidence_score),
        profile=profile,
        use_tags=use_tags,
        source_tier=item.source.source_tier,
        verification_status=item.verification_status,
        criticality=item.criticality,
        source=item.source,
        issues=dedupe_issues(issues),
    )


def determine_use_tags_v02(
    item: EvidenceItem,
    policy: FieldPolicy,
    confidence_score: float,
    profile: EvidenceProfile,
    issues: List[EvidenceIssue],
) -> EvidenceUseTags:
    issue_codes = {x.code for x in issues}
    severities = {x.severity for x in issues}

    if IssueSeverity.REJECT in severities:
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.REJECTED,
            external_reliance_allowed=False,
            narrative_use_allowed=False,
            tail_use_only=False,
            requires_reverification=True,
            base_case_blocked_reason="REJECT_ISSUE_PRESENT",
        )

    if item.verification_status in {VerificationStatus.CONTRADICTED, VerificationStatus.REJECTED}:
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.REJECTED,
            external_reliance_allowed=False,
            narrative_use_allowed=False,
            tail_use_only=False,
            requires_reverification=True,
            base_case_blocked_reason="CONTRADICTED_OR_REJECTED",
        )

    base_block_reason = first_base_case_block_reason(item, policy, confidence_score, profile, issues)

    narrative_allowed = (
        item.intended_narrative_use
        or item.source.source_tier in {SourceTier.S1, SourceTier.S2, SourceTier.S3}
        or item.verification_status in {VerificationStatus.REVIEWED, VerificationStatus.RECONCILED, VerificationStatus.VERIFIED}
    )

    tail_only = item.intended_tail_use

    if not base_block_reason:
        external_reliance = confidence_score >= policy.min_score_for_external_reliance
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.BASE_CASE,
            external_reliance_allowed=external_reliance,
            narrative_use_allowed=True,
            tail_use_only=False,
            requires_reverification=False,
            base_case_blocked_reason=None,
        )

    if item.temporary_substitute or item.intended_tail_use:
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.STRESS_CASE,
            external_reliance_allowed=False,
            narrative_use_allowed=narrative_allowed,
            tail_use_only=True,
            requires_reverification=True,
            base_case_blocked_reason=base_block_reason,
        )

    if confidence_score >= 60.0 and IssueSeverity.BLOCKER not in severities:
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.STRESS_CASE,
            external_reliance_allowed=False,
            narrative_use_allowed=narrative_allowed,
            tail_use_only=tail_only,
            requires_reverification=True,
            base_case_blocked_reason=base_block_reason,
        )

    if confidence_score >= 40.0:
        return EvidenceUseTags(
            model_use_category=ModelUseCategory.INTERNAL_REVIEW,
            external_reliance_allowed=False,
            narrative_use_allowed=narrative_allowed,
            tail_use_only=tail_only,
            requires_reverification=True,
            base_case_blocked_reason=base_block_reason,
        )

    return EvidenceUseTags(
        model_use_category=ModelUseCategory.REJECTED,
        external_reliance_allowed=False,
        narrative_use_allowed=False,
        tail_use_only=False,
        requires_reverification=True,
        base_case_blocked_reason=base_block_reason,
    )


def first_base_case_block_reason(
    item: EvidenceItem,
    policy: FieldPolicy,
    confidence_score: float,
    profile: EvidenceProfile,
    issues: List[EvidenceIssue],
) -> Optional[str]:
    if confidence_score < policy.min_score_for_base_case:
        return "AGGREGATE_SCORE_BELOW_BASE_THRESHOLD"

    if profile.source.score < policy.min_source_score_for_base:
        return "SOURCE_SCORE_BELOW_BASE_THRESHOLD"

    if profile.verification.score < policy.min_verification_score_for_base:
        return "VERIFICATION_SCORE_BELOW_BASE_THRESHOLD"

    if profile.traceability.score < policy.min_traceability_score_for_base:
        return "TRACEABILITY_SCORE_BELOW_BASE_THRESHOLD"

    if profile.recency.score < policy.min_recency_score_for_base:
        return "RECENCY_SCORE_BELOW_BASE_THRESHOLD"

    if profile.cross_check.score < policy.min_cross_check_score_for_base:
        return "CROSS_CHECK_SCORE_BELOW_BASE_THRESHOLD"

    if policy.require_reviewer_for_base_case and item.verification_status not in {
        VerificationStatus.VERIFIED,
        VerificationStatus.RECONCILED,
        VerificationStatus.REVIEWED,
    }:
        return "HUMAN_REVIEW_REQUIRED_FOR_BASE_CASE"

    if item.temporary_substitute and not policy.allow_temporary_substitute_in_base_case:
        return "TEMPORARY_SUBSTITUTE_NOT_ALLOWED_FOR_BASE_CASE"

    if (
        item.source.source_tier in {SourceTier.S4, SourceTier.S5}
        and item.criticality in {Criticality.P0, Criticality.P1}
        and not policy.allow_low_tier_key_field_in_base_case
    ):
        return "LOW_TIER_KEY_FIELD_NOT_ALLOWED_FOR_BASE_CASE"

    if policy.stale_blocks_base_case and any("STALE_DATA" in x.code for x in issues):
        return "STALE_DATA_BLOCKS_BASE_CASE"

    if item.criticality == Criticality.P0 and policy.require_cross_check_for_p0_base and "NO_CROSS_CHECK" in profile.cross_check.flags:
        return "P0_CROSS_CHECK_REQUIRED"

    if item.criticality == Criticality.P1 and policy.require_cross_check_for_p1_base and "NO_CROSS_CHECK" in profile.cross_check.flags:
        return "P1_CROSS_CHECK_REQUIRED"

    if any(x.severity in {IssueSeverity.BLOCKER, IssueSeverity.REJECT} for x in issues):
        return "BLOCKER_OR_REJECT_ISSUE_PRESENT"

    return None


def calculate_traceability_score(item: EvidenceItem, policy: FieldPolicy) -> Tuple[float, List[str]]:
    score = 0.0
    flags: List[str] = []

    if item.source.source_id:
        score += 10
    else:
        flags.append("MISSING_SOURCE_ID")

    if item.source.source_name:
        score += 10
    else:
        flags.append("MISSING_SOURCE_NAME")

    if item.source.document_id:
        score += 25
    else:
        flags.append("MISSING_DOCUMENT_ID")

    if item.source.page_number is not None:
        score += 15

    if item.source.line_reference:
        score += 15

    if not item.source.page_number and not item.source.line_reference:
        flags.append("MISSING_PAGE_OR_LINE")

    if item.source.excerpt:
        score += 20
    else:
        flags.append("MISSING_EXCERPT")

    if item.source.owner:
        score += 5

    return clamp(score, 0, 100), flags


def calculate_recency_score(
    item: EvidenceItem,
    policy: FieldPolicy,
    evaluation_date: date,
) -> Tuple[float, List[str]]:
    flags: List[str] = []

    if not policy.max_age_days:
        if item.source.source_date:
            return 80.0, []
        return 60.0, ["NO_SOURCE_DATE"]

    if not item.source.source_date:
        return 45.0, ["NO_SOURCE_DATE", "STALE_DATA_BLOCKER"]

    age_days = (evaluation_date - item.source.source_date).days

    if age_days <= policy.max_age_days:
        return 100.0, []

    if age_days <= policy.max_age_days * 2:
        flags.append("STALE_DATA_WARNING")
        return 70.0, flags

    flags.append("STALE_DATA_BLOCKER")
    return 30.0, flags


def calculate_cross_check_score(
    item: EvidenceItem,
    policy: FieldPolicy,
) -> Tuple[float, List[str], List[EvidenceIssue]]:
    flags: List[str] = []
    issues: List[EvidenceIssue] = []

    if not item.cross_checks:
        return 55.0, ["NO_CROSS_CHECK"], issues

    scores: List[float] = []
    high_tier_mismatch = False
    any_match = False

    for check in item.cross_checks:
        same = values_match(
            left=item.value,
            right=check.value,
            tolerance_abs=check.tolerance_abs if check.tolerance_abs is not None else policy.tolerance_abs,
            tolerance_pct=check.tolerance_pct if check.tolerance_pct is not None else policy.tolerance_pct,
        )

        base = SOURCE_TIER_BASE_SCORE[check.source_tier]
        verification = VERIFICATION_SCORE[check.verification_status]

        if same:
            any_match = True
            scores.append(base * 0.60 + verification * 0.40)
        else:
            flags.append("CROSS_CHECK_MISMATCH")
            mismatch_score = 20.0

            if check.source_tier in {SourceTier.S1, SourceTier.S2}:
                high_tier_mismatch = True
                mismatch_score = 0.0
                flags.append("HIGH_TIER_CROSS_CHECK_MISMATCH")

            scores.append(mismatch_score)

    if high_tier_mismatch:
        severity = IssueSeverity.BLOCKER if policy.high_tier_mismatch_blocks_field else IssueSeverity.WARNING
        issues.append(issue(
            code=f"{item.field_name}:HIGH_TIER_CROSS_CHECK_MISMATCH",
            severity=severity,
            message="A high-tier cross-check contradicts the selected evidence.",
        ))
        return 10.0, flags, issues

    if not any_match:
        issues.append(issue(
            code=f"{item.field_name}:ALL_CROSS_CHECKS_MISMATCH",
            severity=IssueSeverity.WARNING,
            message="Cross-checks exist but none matched within tolerance.",
        ))

    return clamp(sum(scores) / len(scores), 0, 100), flags, issues


def calculate_adjustment_score(item: EvidenceItem) -> Tuple[float, List[str]]:
    flags: List[str] = []

    if item.adjustment_amount is None:
        return 90.0, []

    if item.adjustment_reason and item.verification_status in {
        VerificationStatus.VERIFIED,
        VerificationStatus.RECONCILED,
        VerificationStatus.REVIEWED,
    }:
        return 85.0, ["ADJUSTED_WITH_REASON"]

    if item.adjustment_reason:
        return 65.0, ["ADJUSTED_NOT_FULLY_VERIFIED"]

    return 35.0, ["ADJUSTED_WITHOUT_REASON"]


def aggregate_field_scores(
    field_name: str,
    scores: List[EvidenceScore],
    policy: FieldPolicy,
    required: bool,
    p0: bool,
) -> FieldEvidenceAggregate:
    if not scores:
        return FieldEvidenceAggregate(
            field_name=field_name,
            selected=None,
            alternatives=[],
            field_conflict=False,
            p0_ready=False if p0 else True,
            required_ready=False if required else True,
            blockers=[issue(
                code=f"{field_name}:NO_EVIDENCE",
                severity=IssueSeverity.BLOCKER,
                message="No evidence available for field.",
            )],
            warnings=[],
        )

    sorted_scores = sorted(scores, key=lambda x: x.confidence_score, reverse=True)
    selected = sorted_scores[0]
    alternatives = sorted_scores[1:]

    field_conflict, conflict_issue = detect_field_conflict(sorted_scores, policy)

    blockers: List[EvidenceIssue] = []
    warnings: List[EvidenceIssue] = []

    for score in sorted_scores:
        for iss in score.issues:
            if iss.severity in {IssueSeverity.BLOCKER, IssueSeverity.REJECT}:
                blockers.append(iss)
            elif iss.severity == IssueSeverity.WARNING:
                warnings.append(iss)

    if conflict_issue:
        if conflict_issue.severity in {IssueSeverity.BLOCKER, IssueSeverity.REJECT}:
            blockers.append(conflict_issue)
        else:
            warnings.append(conflict_issue)

    p0_ready = True
    required_ready = True

    if p0 and selected.use_tags.model_use_category != ModelUseCategory.BASE_CASE:
        p0_ready = False
        blockers.append(issue(
            code=f"{field_name}:P0_NOT_BASE_CASE_READY",
            severity=IssueSeverity.BLOCKER,
            message="P0 field is not ready for base-case model use.",
        ))

    if required and selected.use_tags.model_use_category not in {
        ModelUseCategory.BASE_CASE,
        ModelUseCategory.STRESS_CASE,
    }:
        required_ready = False
        blockers.append(issue(
            code=f"{field_name}:REQUIRED_FIELD_NOT_USABLE",
            severity=IssueSeverity.BLOCKER,
            message="Required field is not usable for model input.",
        ))

    return FieldEvidenceAggregate(
        field_name=field_name,
        selected=selected,
        alternatives=alternatives,
        field_conflict=field_conflict,
        p0_ready=p0_ready,
        required_ready=required_ready,
        blockers=dedupe_issues(blockers),
        warnings=dedupe_issues(warnings),
    )


def detect_field_conflict(
    scores: List[EvidenceScore],
    policy: FieldPolicy,
) -> Tuple[bool, Optional[EvidenceIssue]]:
    if len(scores) <= 1:
        return False, None

    selected = scores[0]

    for other in scores[1:]:
        if other.confidence_score < 60:
            continue

        same = values_match(
            left=selected.value,
            right=other.value,
            tolerance_abs=policy.tolerance_abs,
            tolerance_pct=policy.tolerance_pct,
        )

        if same:
            continue

        high_tier_involved = (
            selected.source_tier in {SourceTier.S1, SourceTier.S2}
            or other.source_tier in {SourceTier.S1, SourceTier.S2}
        )

        if high_tier_involved:
            severity = IssueSeverity.BLOCKER if policy.high_tier_mismatch_blocks_field else IssueSeverity.WARNING
            return True, issue(
                code=f"{selected.field_name}:FIELD_VALUE_CONFLICT_HIGH_TIER",
                severity=severity,
                message="Selected evidence conflicts with another credible high-tier source.",
            )

        return True, issue(
            code=f"{selected.field_name}:FIELD_VALUE_CONFLICT",
            severity=IssueSeverity.WARNING,
            message="Selected evidence conflicts with another credible source.",
        )

    return False, None


def determine_evidence_gate_v02(
    overall_score: float,
    p0_ready: bool,
    required_ready: bool,
    external_reliance_ready: bool,
    blockers: Sequence[EvidenceIssue],
    field_results: Sequence[FieldEvidenceAggregate],
) -> EvidenceGate:
    if any(x.severity == IssueSeverity.REJECT for x in blockers):
        return EvidenceGate.REJECT

    if not p0_ready:
        return EvidenceGate.HOLD

    if not required_ready:
        return EvidenceGate.HOLD

    if any(x.severity == IssueSeverity.BLOCKER for x in blockers):
        return EvidenceGate.HOLD

    if overall_score >= 85 and external_reliance_ready:
        return EvidenceGate.PASS

    if overall_score >= 70:
        return EvidenceGate.WATCH

    return EvidenceGate.HOLD


@dataclass(frozen=True)
class EvidenceOutcomeRecord:
    deal_id: str
    field_name: str
    evidence_source_id: str

    used_in_model: bool
    overridden: bool = False
    override_direction: Optional[OverrideDirection] = None
    override_reason: Optional[str] = None

    outcome_tag: OutcomeTag = OutcomeTag.UNKNOWN
    realized_loss_amount: Optional[float] = None
    realized_loss_rate: Optional[float] = None

    reviewed_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None


def normalize_deal_master(raw: Union[DealMaster, Mapping[str, Any]]) -> DealMaster:
    if isinstance(raw, DealMaster):
        return raw
    if isinstance(raw, Mapping):
        return DealMaster.from_mapping(raw)
    raise TypeError("deal_master must be DealMaster or mapping")


def normalize_evidence_item(raw: Union[EvidenceItem, Mapping[str, Any]]) -> EvidenceItem:
    if isinstance(raw, EvidenceItem):
        return raw
    if isinstance(raw, Mapping):
        return EvidenceItem.from_mapping(raw)
    raise TypeError("evidence_items must contain EvidenceItem or mapping")


def normalize_field_policies(
    raw: Optional[Mapping[str, Union[FieldPolicy, Mapping[str, Any]]]]
) -> Dict[str, FieldPolicy]:
    if not raw:
        return {}

    out: Dict[str, FieldPolicy] = {}
    for field_name, policy in raw.items():
        if isinstance(policy, FieldPolicy):
            out[field_name] = policy
        elif isinstance(policy, Mapping):
            out[field_name] = FieldPolicy.from_mapping(policy)
        else:
            raise TypeError(f"Invalid policy for {field_name}")

    return out


def issue(code: str, severity: IssueSeverity, message: str) -> EvidenceIssue:
    return EvidenceIssue(code=code, severity=severity, message=message)


def dim(score: float, flags: Optional[List[str]] = None) -> DimensionScore:
    score = round(clamp(score, 0, 100), 2)
    return DimensionScore(score=score, grade=score_to_grade(score), flags=flags or [])


def dedupe_issues(items: Sequence[EvidenceIssue]) -> List[EvidenceIssue]:
    seen = set()
    out: List[EvidenceIssue] = []

    for item in items:
        key = (item.code, item.severity.value)
        if key not in seen:
            seen.add(key)
            out.append(item)

    return sorted(out, key=lambda x: (x.severity.value, x.code))


def parse_enum(enum_cls: Any, value: Any, default: Any) -> Any:
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except ValueError:
        return default


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Cannot parse date from {value!r}")


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Cannot parse datetime from {value!r}")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def values_match(
    left: Any,
    right: Any,
    tolerance_abs: Optional[float] = None,
    tolerance_pct: Optional[float] = None,
) -> bool:
    if left == right:
        return True

    if is_number(left) and is_number(right):
        l = float(left)
        r = float(right)

        if tolerance_abs is not None and abs(l - r) <= tolerance_abs:
            return True

        if tolerance_pct is not None:
            denominator = max(abs(l), abs(r), 1e-9)
            return abs(l - r) / denominator <= tolerance_pct

        denominator = max(abs(l), abs(r), 1e-9)
        return abs(l - r) / denominator <= 0.0001

    return False


def weighted_average(values: Sequence[Tuple[float, float]]) -> float:
    if not values:
        return 0.0
    numerator = sum(score * weight for score, weight in values)
    denominator = sum(weight for _, weight in values)
    return numerator / denominator if denominator else 0.0


def score_to_grade(score: float) -> str:
    if score >= 92:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"
