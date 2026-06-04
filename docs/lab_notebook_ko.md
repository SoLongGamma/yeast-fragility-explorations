# 프로젝트 진행 일지 (한국어 요약)

이 문서는 프로젝트의 전체 진행 과정을 한국어로 간단히 정리한 것이다.
영어 문서 (`decisions.md`, `lab_notebook.md`)와 짝을 이룬다.

---

## 0. 시작점

학부 4학년, 효모 실험실 3일 경험. 코드 처음. 효모 발효의
*재현성 문제*를 *시뮬레이션 도구*로 다뤄보겠다는 발상에서 시작.

## 1. v0.1 — Toy ABM (agent-based model)

가설: "**간헐적 스트레스가 효모 집단을 안정시킨다**" (호르메시스)

Mesa 라이브러리로 효모 cell을 agent로 표현. defense_capital과
intrinsic_robustness 속성. constant 환경 vs variable 환경에서
black swan 충격 (half-Cauchy 분포) 가함.

**결과 (N=200 seed)**: 멸종률 constant 93.5% vs variable 60.5%.
간헐 자극이 *살아남는 비율을 2배 늘림*.

## 2. v0.2 — 통계 안전장치 + 데이터 인프라

ABM 결과를 보고 *진짜로 의미 있는 차이인가* 의심. 학계 표준
통계 도구 추가:
- Welch's t-test, Bonferroni correction
- Bootstrap confidence interval
- 의미 없는 차이는 *TIED* 또는 *WORSE* 라벨
- 너무 많은 schedule 비교 시 *search inflation warning*

데이터 인프라 (`fermentation_run.schema.json`, `loader.py`, 
`sources.yaml`) 만듦. 외부 데이터 들어올 통로 준비.

## 3. v0.3 — Yeast8/ecYeast8로 검증 시도

ABM은 *toy*. 학계 검증된 모델 위에서 같은 가설 확인하려고
Yeast8 (Chalmers consensus 모델, 4131 reactions) 도입.

**Step 1**: Colab notebook으로 Yeast8 로드 + Crabtree scan 시도
→ Yeast8 단독은 Crabtree effect 못 잡음.

**Step 2**: ecYeast8 (enzyme-constrained version, 8144 reactions)로
교체 → Crabtree 임계점 (5-8 mmol/gDW/hr) 직접 확인.

**Step 2 결과**: pulse vs constant 단일 trajectory 비교
- Constant: biomass 66 g/L, ethanol 3 g/L
- Pulse: biomass 35 g/L, ethanol 6.5 g/L (Crabtree overflow)

## 4. *카테고리 오류* 발견 (Decision 5)

ecYeast8로 Monte Carlo 돌리려 하니 *2시간 per run*. timeout.

깨달음: **ecYeast8은 *결정적 (deterministic)* 모델**. 같은 입력 →
같은 출력. *분산 측정 자체가 불가능*. 우리 가설은 *분산 감소*에
대한 것인데 *분산이 없는 모델*로 검증하려 했음.

**결정**: 도구 두 개를 *다른 역할*로 분리:
- ABM = *분산 backend* (Monte Carlo 자연스러움)
- ecYeast8 = *메커니즘 backend* (단일 trajectory mechanistic check)

`decisions.md`에 Decision 5로 기록.

## 5. Phase A heavy — ABM 본 실험 (13시간)

ABM에 Monte Carlo 돌림:
- 2 schedule × 4 σ × 2 swan_scale × N=500 = **8000 trial**
- 사용자 맥에서 789분 (13시간)

**핵심 발견**:
1. sigma_input (agent 속성 perturb) 효과 거의 없음
2. 분포가 *bimodal* (0 또는 carrying cap). Axenie 분석 부적합
3. **swan=1.0**: constant 79% 멸종 vs variable 38%. **-41%p**
4. **swan=2.5**: constant 92% 멸종 vs variable 65%. **-27%p**

가설은 *culture failure rate* 측면에서 명확히 지지됨. Axenie의
skewness 측면에서는 carrying cap 때문에 적용 불가.

## 6. Spitznagel 보험 베팅 발상

Mark Spitznagel의 *97% 자산 + 3% put option*이 *기하 평균*을 높이는
구조. 효모에 매핑:
- 97% 일반 효모 + 3% pre-primed 효모 (bet hedging)
- 또는 정기적 *예방 약자극* (Kim 2015 spermidine과 같은 길)

다만 *학계에는 이미 bet hedging이 큰 분야* (Veening 2008, Balaban 2004).
너의 *진짜 새로움*이 *Spitznagel framing*인지 *수단*인지 불명확.

## 7. 문제 정의 다시 — 학계 용어로

직관적 단어를 *학계 표준 용어*로 매핑:
- "변수 청소" → variance reduction / phenotypic synchronization
- "간헐 자극" → intermittent prophylactic perturbation
- "타이밍" → scheduling model / event-triggered control
- "보험 베팅" → bet hedging (Veening 2008)
- "허용 envelope" → design space (ICH Q8)
- "옌센 활용" → convexity-aware optimization
- "extinction rate" → culture failure rate

새 정의:
> "5L *S. cerevisiae* fed-batch에서 *inoculum-size variability*와 
> *rare disturbance*에 의한 batch-to-batch 재현성 문제를 다룬다.
> *Extremum Seeking Control + Event-Triggered Control + dFBA* 위에
> *Jensen's inequality를 활용한 prophylactic perturbation timing*을
> 얹어 *culture failure rate를 줄이고 geometric mean yield를 높이는*
> 추천 모델."

## 8. v1.0 MVP — Streamlit 앱

학계 표준 *manipulated variable*: feed rate + DO setpoint.

가장 단순한 형태:
- 5-state ODE (X, S, E, DO, V)
- Monod kinetics + Crabtree effect
- Grid search로 추천
- Streamlit UI 단일 화면

3개 파일, 약 200줄. 모든 antifragility/Spitznagel/Monte Carlo *나중에*.

## 9. Simplest Monte Carlo 검증

MVP의 5-state ODE 위에 *N=200 Monte Carlo*. 3개 핵심 변수만 변동:
- μ_max ± 15%
- Y_XS ± 10%
- X₀ ± 15%

**결과**:
- Final ethanol: mean 9.9 g/L, CV **20.3%**
- Final biomass: mean 134.7 g/L, CV 8.1%

*3개 매개변수의 작은 변동*이 ethanol에서 *2배 증폭*된 분산을 만듦.
*재현성 문제의 정량적 측정*.

---

## 현재 위치

- v0.1 ABM (검증된 toy)
- v0.2 통계 안전장치 (재사용 가능)
- v0.3 ecYeast8 backend (mechanism check용)
- Phase A heavy 결과 (8000 trial, 멸종률 -41%p)
- v1.0 MVP (Streamlit 앱)
- Simple Monte Carlo (분산 측정 검증)
- 9개 decision 메타 레벨 기록
- 7개 실험 lab notebook 기록

## 다음 가능한 길

1. MVP에 Monte Carlo uncertainty band 통합
2. Schedule comparison (constant vs pulse) on 5-state ODE
3. ecYeast8 dFBA 결과 통합
4. 외부 피드백 (r/microbiology, Bits in Bio 등)
5. 문헌 데이터 디지타이즈로 모델 calibration

## 솔직한 평가

- **가장 단단한 증거**: Phase A heavy의 culture failure rate -41%p.
  N=500 × 8 cell에서 일관됨.
- **가장 약한 부분**: ABM의 *toy assumptions* (defense_capital의 추상성)
  와 *carrying cap이 분포 모양 왜곡*하는 문제.
- **검증된 것**: 학계 표준 manipulated variable (feed+DO) 선택,
  ecYeast8 Crabtree, MVP 추천 합리성.
- **검증 안 된 것**: 진짜 wet-lab strain에서 가설 작동, MVP 추천이
  실제 사용 가능한지.

## 도구별 역할 정리

| 도구 | 역할 | 상태 |
|---|---|---|
| ABM (v0.1/v0.2) | 분산 backend, Monte Carlo | 작동 |
| ecYeast8 (v0.3) | 메커니즘 backend, single trajectory | 작동 |
| 5-state ODE | MVP 추천 backend | 작동 |
| 데이터 인프라 (v0.2) | 외부 데이터 통합 통로 | 빈 상태 |
| 통계 안전장치 (v0.2) | 모든 비교에 재활용 | 작동 |
| Streamlit MVP | 사용자 인터페이스 | 작동 |

세 모델 (ABM, ecYeast8, ODE)은 *같은 가설을 다른 각도에서* 검증.
*하나가 다른 하나를 대체하지 않음*.
