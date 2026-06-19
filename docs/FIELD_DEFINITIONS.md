# COSMOS 필드 정의 / 단위 잠금 (v1.0)

## 1. 금액 단위 (Amount Lock)

| 레이어 | 단위 | 예시 |
|---|---|---|
| DB 저장 | KRW 원 단위 (raw) | `11680000000` (116.8억) |
| API 입력 (`*_input` payload) | KRW 원 단위 (raw) | `value: 11680000000` |
| UI/메모 표시 | 억 원 (display) | `116.8억` |

**규칙**: 모든 엔진(`evidence_engine`, `refi_path_engine`, `recovery_strategy_engine_kr`)의 숫자 입력은 **반드시 원 단위**로 넣는다. "억" 단위로 입력하면 전체 모델이 깨진다 (10^8배 오차).

**검증 절차**: 새 딜 입력 시 다음을 1차 확인:
- 신한 선순위 잔액이 116.8억(11,680,000,000)인지 11.68억(1,168,000,000)인지 재확인 — 자릿수 하나로 LTV/DSCR/Refi Gap/LGD 전체가 무너짐.
- 90억 인수가가 `purchase_price`인지 `asset_value`(감정가)인지 명확히 구분해서 입력.

## 2. Ratio Basis 정의

| 비율 | Numerator 정의 | Denominator 정의 |
|---|---|---|
| DSCR | NOI (순운영소득) — 현 NOI 기준, FastFive 등 pro forma는 별도 scenario | 연간 debt service (이자+상환) |
| LTV | 현재 채무 잔액 | `asset_value` (감정가, 강제매각가 아님) |
| Recovery base value | 강제매각/협의매각 net proceeds (비용 차감 후) | — |

**규칙**: Base case에는 **현재 NOI만** 사용. FastFive 같은 pro forma upside는 `scenario` 또는 `upside_input`으로만 넣고 base_case_inputs에 혼입 금지.

## 3. Source Tier 지정 원칙

| 데이터 | 권장 Source Tier |
|---|---|
| 신한 선순위 잔액 | payoff letter 수령 전 = S4, 수령 후 = S1 |
| 감정평가서 | 1년 이내 + 정식 감정 = S2, 그 외 = S5 |
| 임차보증금/전세권 | 등기부/확정일자 확인 전 = S5, 확인 후 = S2 |
| 세금 체납액 | 국세청 확인 전 = S5, 확인 후 = S1 |

## 4. 회수 분석 전제조건

Recovery base case는 다음이 확인되기 전까지 PASS 불가:
- 임차보증금 / 전세권 / 대항력 / 확정일자
- 세금/공과금 체납 및 압류 여부
- 1순위 담보권 등기 상태

확인 안 되면 `legal_status: UNVERIFIED`로 입력 → 엔진이 자동으로 HOLD 처리.
