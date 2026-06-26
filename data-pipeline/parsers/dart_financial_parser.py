"""DART 재무 원문 dict → FinancialFeatures."""
from __future__ import annotations

from engines.financial_engine import FinancialFeatures


class DartFinancialParser:

    def parse(self, raw_data: dict, entity_id: str, entity_name: str, dart_corp_code: str) -> FinancialFeatures:
        return FinancialFeatures(
            entity_id=entity_id,
            entity_name=entity_name,
            period_end=f"{raw_data.get('period_year', 2024)}-12-31",
            current_assets=raw_data.get("current_assets", 0),
            total_assets=raw_data.get("total_assets", 0),
            retained_earnings=raw_data.get("retained_earnings", 0),
            ebit=raw_data.get("ebit", 0),
            equity=raw_data.get("equity", 0),
            total_debt=raw_data.get("total_debt", 0),
            sales=raw_data.get("sales", 0),
            interest_expense=raw_data.get("interest_expense", 0),
            operating_cf=raw_data.get("operating_cf", 0),
            short_term_debt=raw_data.get("short_term_debt", 0),
        )
