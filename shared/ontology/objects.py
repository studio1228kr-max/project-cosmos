"""
shared/ontology/objects.py

온톨로지 SDK (도메인 객체 레이어).
models.py 의 SQLAlchemy 모델을 감싸 사용성 높은 래퍼를 제공한다.

  - DB 세션: DATABASE_URL (data-pipeline 과 동일한 URL 소스) 기반 SQLAlchemy 엔진/세션.
  - PropertyAccessor: JSONB properties/provenance 를 obj.props.<key>.value 점표기로 접근.
  - Deal/Borrower/Collateral/Valuation: get()/where()/props/관계 래핑.
  - PolicyRule: get_active(rule_key).

세션 수명: get()/where()/get_active() 는 세션을 열어 래퍼에 보관한다(관계 lazy-load 용).
사용 후 wrapper.close() 로 직접 닫거나, context manager(with)로 자동 종료한다.

    # context manager — 블록 종료 시 세션 자동 close()
    with Deal.get(1) as deal:
        print(deal.props.dscr.value)

    # 수동 종료도 그대로 가능
    deal = Deal.get(1)
    try:
        ...
    finally:
        deal.close()
"""
from __future__ import annotations

import os
from typing import Any, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.ontology.models import (
    Borrower as BorrowerModel,
    Collateral as CollateralModel,
    Deal as DealModel,
    PolicyRule as PolicyRuleModel,
    Valuation as ValuationModel,
)


# ──────────────────────────────────────────────────────────────
# 엔진 / 세션 (lazy — import 시 연결하지 않는다)
# ──────────────────────────────────────────────────────────────
_engine = None
_SessionFactory = None


def _get_engine():
    """DATABASE_URL 기반 SQLAlchemy 엔진 (data-pipeline 과 동일 URL 소스)."""
    global _engine
    if _engine is None:
        _engine = create_engine(os.environ["DATABASE_URL"], future=True)
    return _engine


def get_session():
    """새 SQLAlchemy 세션 반환."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine())
    return _SessionFactory()


# ──────────────────────────────────────────────────────────────
# PropertyAccessor — JSONB properties/provenance 점표기 접근
# ──────────────────────────────────────────────────────────────
class _PropertyField:
    """
    단일 프로퍼티 접근자.
      .value            → properties[key]
      .source           → provenance[key]['origin']
      .gate_eligibility → provenance[key]['gate_eligibility']
    키/하위키 없으면 None (에러 없음).
    """

    __slots__ = ("_key", "_properties", "_provenance")

    def __init__(self, properties: dict, provenance: dict, key: str):
        self._key = key
        self._properties = properties
        self._provenance = provenance

    def _prov_entry(self) -> dict:
        entry = self._provenance.get(self._key)
        return entry if isinstance(entry, dict) else {}

    @property
    def value(self) -> Any:
        return self._properties.get(self._key)

    @property
    def source(self) -> Any:
        return self._prov_entry().get("origin")

    @property
    def gate_eligibility(self) -> Any:
        return self._prov_entry().get("gate_eligibility")

    def __repr__(self) -> str:
        return f"<PropertyField {self._key!r} value={self.value!r}>"


class PropertyAccessor:
    """obj.props.<key> → _PropertyField. 키 없어도 None 반환."""

    def __init__(self, properties: Optional[dict], provenance: Optional[dict]):
        # __getattr__ 재귀 방지를 위해 __dict__ 직접 사용
        self.__dict__["_properties"] = properties or {}
        self.__dict__["_provenance"] = provenance or {}

    def __getattr__(self, name: str) -> _PropertyField:
        # 정상 속성 조회 실패 시에만 호출됨 (_properties/_provenance 는 __dict__ 에 있음)
        return _PropertyField(self.__dict__["_properties"], self.__dict__["_provenance"], name)

    def __getitem__(self, key: str) -> _PropertyField:
        return _PropertyField(self.__dict__["_properties"], self.__dict__["_provenance"], key)

    def __repr__(self) -> str:
        return f"<PropertyAccessor keys={list(self.__dict__['_properties'].keys())}>"


# ──────────────────────────────────────────────────────────────
# 래퍼 베이스
# ──────────────────────────────────────────────────────────────
class _Wrapper:
    _model = None  # 하위 클래스가 SQLAlchemy 모델로 지정

    def __init__(self, obj, session):
        self._obj = obj
        self._session = session

    @property
    def raw(self):
        """내부 SQLAlchemy 객체 (디버깅용)."""
        return self._obj

    @property
    def props(self) -> PropertyAccessor:
        return PropertyAccessor(
            getattr(self._obj, "properties", None),
            getattr(self._obj, "provenance", None),
        )

    def close(self) -> None:
        """보관 중인 세션 종료 (수동 호출 가능)."""
        if self._session is not None:
            self._session.close()

    # context manager — with 블록 종료 시 self.close() 자동 호출
    def __enter__(self) -> "_Wrapper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False  # 예외 억제하지 않음 (그대로 전파)

    @classmethod
    def get(cls, id: Any) -> Optional["_Wrapper"]:
        session = get_session()
        obj = session.get(cls._model, id)
        if obj is None:
            session.close()
            return None
        return cls(obj, session)

    @classmethod
    def where(cls, **kwargs) -> List["_Wrapper"]:
        session = get_session()
        rows = session.query(cls._model).filter_by(**kwargs).all()
        return [cls(o, session) for o in rows]

    def _wrap(self, wrapper_cls, obj):
        return wrapper_cls(obj, self._session) if obj is not None else None

    def _wrap_list(self, wrapper_cls, objs) -> list:
        return [wrapper_cls(o, self._session) for o in (objs or [])]

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._obj!r}>"


# ──────────────────────────────────────────────────────────────
# 도메인 래퍼
# ──────────────────────────────────────────────────────────────
class Borrower(_Wrapper):
    _model = BorrowerModel

    @property
    def deals(self) -> list:
        return self._wrap_list(Deal, self._obj.deals)


class Collateral(_Wrapper):
    _model = CollateralModel

    @property
    def deal(self) -> Optional["Deal"]:
        return self._wrap(Deal, self._obj.deal)

    @property
    def valuations(self) -> list:
        return self._wrap_list(Valuation, self._obj.valuations)


class Valuation(_Wrapper):
    _model = ValuationModel

    @property
    def deal(self) -> Optional["Deal"]:
        return self._wrap(Deal, self._obj.deal)

    @property
    def collateral(self) -> Optional["Collateral"]:
        return self._wrap(Collateral, self._obj.collateral)


class Deal(_Wrapper):
    _model = DealModel

    @property
    def borrower(self) -> Optional["Borrower"]:
        return self._wrap(Borrower, self._obj.borrower)

    @property
    def collaterals(self) -> list:
        return self._wrap_list(Collateral, self._obj.collaterals)

    @property
    def valuations(self) -> list:
        return self._wrap_list(Valuation, self._obj.valuations)


class PolicyRule(_Wrapper):
    _model = PolicyRuleModel

    @classmethod
    def get_active(cls, rule_key: str) -> Optional["PolicyRule"]:
        """rule_key 의 활성(is_active) 버전 중 최신 1건. 없으면 None."""
        session = get_session()
        obj = (
            session.query(PolicyRuleModel)
            .filter(
                PolicyRuleModel.rule_key == rule_key,
                PolicyRuleModel.is_active.is_(True),
            )
            .order_by(PolicyRuleModel.version.desc())
            .first()
        )
        if obj is None:
            session.close()
            return None
        return cls(obj, session)

    @property
    def rule_body(self) -> dict:
        """JSONB rule_body (이미 dict)."""
        return self._obj.rule_body
