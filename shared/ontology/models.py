"""
shared/ontology/models.py

온톨로지 코어 SQLAlchemy 모델.
data-pipeline/migrations/006_ontology_core.sql 스키마를 1:1 매핑한다
(컬럼명·타입·기본값·제약·FK·인덱스 동일). agent_action_log 는 제외.

NOTE: SQLAlchemy 1.4+ 기준. requirements 미반영 상태.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

try:  # SQLAlchemy 1.4+/2.0
    from sqlalchemy.orm import declarative_base
except ImportError:  # SQLAlchemy < 1.4
    from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class PolicyRule(Base):
    __tablename__ = "policy_rule"

    id = Column(BigInteger, primary_key=True)

    rule_code = Column(Text, nullable=False)
    rule_category = Column(Text)
    rule_name = Column(Text, nullable=False)
    severity = Column(Text)
    gate_action = Column(Text)
    trigger_condition = Column(Text)
    rationale = Column(Text)
    status = Column(Text, nullable=False, server_default=text("'active'"))
    rule_version = Column(Text)

    rule_key = Column(Text, nullable=False)
    rule_kind = Column(Text, nullable=False)
    scope = Column(Text, nullable=False, server_default=text("'global'"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    rule_body = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    es_sync_token = Column(BigInteger, nullable=False, server_default=text("1"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("rule_key", "version", name="uq_policy_rule_key_version"),
        CheckConstraint(
            "severity IS NULL OR severity IN ('INFO','LOW','MEDIUM','HIGH','CRITICAL')",
            name="chk_policy_rule_severity",
        ),
    )

    def __repr__(self) -> str:
        return f"<PolicyRule id={self.id} rule_key={self.rule_key!r} v{self.version}>"


class Borrower(Base):
    __tablename__ = "borrower"

    id = Column(BigInteger, primary_key=True)

    borrower_code = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    entity_type = Column(Text)
    dart_corp_code = Column(Text)
    country = Column(Text, server_default=text("'KR'"))
    sector = Column(Text)

    properties = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    provenance = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    es_sync_token = Column(BigInteger, nullable=False, server_default=text("1"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("borrower_code", name="uq_borrower_code"),
    )

    def __repr__(self) -> str:
        return f"<Borrower id={self.id} code={self.borrower_code!r}>"


class Deal(Base):
    __tablename__ = "deal"

    id = Column(BigInteger, primary_key=True)

    deal_code = Column(Text, nullable=False)
    deal_name = Column(Text)
    deal_type = Column(Text)
    stage = Column(Text)

    borrower_id = Column(BigInteger, ForeignKey("borrower.id"))
    gate_policy_rule_id = Column(BigInteger, ForeignKey("policy_rule.id"))

    # C-07: 기본 게이트는 HOLD.
    gate_status = Column(Text, nullable=False, server_default=text("'HOLD'"))

    exposure_amount = Column(BigInteger)
    currency = Column(Text, nullable=False, server_default=text("'KRW'"))
    maturity_date = Column(Date)

    # 010_deal_legacy_link.sql: 기존 deal_master.id 연결(신·구 딜 매핑)
    legacy_deal_master_id = Column(Integer)

    properties = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    provenance = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    es_sync_token = Column(BigInteger, nullable=False, server_default=text("1"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("deal_code", name="uq_deal_code"),
        CheckConstraint(
            "gate_status IN ('GO','HOLD','KILL')",
            name="chk_deal_gate_status",
        ),
        Index("idx_deal_borrower_id", "borrower_id"),
        Index("idx_deal_gate_policy_rule_id", "gate_policy_rule_id"),
        Index("idx_deal_gate_status", "gate_status"),
    )

    borrower = relationship("Borrower", backref="deals")
    gate_policy_rule = relationship("PolicyRule")
    collaterals = relationship("Collateral", back_populates="deal", cascade="all, delete-orphan")
    valuations = relationship(
        "Valuation",
        foreign_keys="Valuation.deal_id",
        back_populates="deal",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Deal id={self.id} code={self.deal_code!r} gate={self.gate_status}>"


class Collateral(Base):
    __tablename__ = "collateral"

    id = Column(BigInteger, primary_key=True)

    collateral_code = Column(Text)
    deal_id = Column(BigInteger, ForeignKey("deal.id", ondelete="CASCADE"), nullable=False)

    collateral_type = Column(Text)
    lien_position = Column(Text)
    description = Column(Text)
    asset_address = Column(Text)

    # 009_collateral_values.sql: 평가 수치 컬럼 (gate_evaluator collateral.<field> 비교용)
    appraised_value = Column(Numeric)
    first_lien_value = Column(Numeric)
    net_collateral_value = Column(Numeric)

    es_sync_token = Column(BigInteger, nullable=False, server_default=text("1"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("collateral_code", name="uq_collateral_code"),
        Index("idx_collateral_deal_id", "deal_id"),
    )

    deal = relationship("Deal", back_populates="collaterals")
    valuations = relationship(
        "Valuation",
        foreign_keys="Valuation.collateral_id",
        back_populates="collateral",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Collateral id={self.id} deal_id={self.deal_id} code={self.collateral_code!r}>"


class Valuation(Base):
    __tablename__ = "valuation"

    id = Column(BigInteger, primary_key=True)

    collateral_id = Column(BigInteger, ForeignKey("collateral.id", ondelete="CASCADE"))
    deal_id = Column(BigInteger, ForeignKey("deal.id", ondelete="CASCADE"))

    subject_type = Column(Text)
    subject_id = Column(BigInteger)

    valuation_method = Column(Text)
    value_amount = Column(Numeric)
    currency = Column(Text, nullable=False, server_default=text("'KRW'"))
    as_of_date = Column(Date)

    cases = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    primary_case = Column(Text, nullable=False, server_default=text("'downside'"))
    confidence = Column(Text, nullable=False, server_default=text("'UNVERIFIED'"))

    engine_run_id = Column(Text)
    source_doc_id = Column(Text)
    provenance = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    es_sync_token = Column(BigInteger, nullable=False, server_default=text("1"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "engine_run_id IS NOT NULL "
            "OR source_doc_id IS NOT NULL "
            "OR (provenance IS NOT NULL AND provenance != '{}'::jsonb)",
            name="chk_valuation_provenance",
        ),
        Index("idx_valuation_collateral_id", "collateral_id"),
        Index("idx_valuation_deal_id", "deal_id"),
    )

    deal = relationship("Deal", foreign_keys=[deal_id], back_populates="valuations")
    collateral = relationship("Collateral", foreign_keys=[collateral_id], back_populates="valuations")

    def __repr__(self) -> str:
        return f"<Valuation id={self.id} collateral_id={self.collateral_id} primary_case={self.primary_case!r}>"
