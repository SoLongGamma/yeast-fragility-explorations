# v0.3 — Pivot to Yeast8

## 왜 pivot?

v0.1과 v0.2는 toy ABM 위에서 만들어졌다. ABM은 직관적이고 만들기 쉽지만,
*검증된 도구*는 아니다. 누가 결과를 보고 "그 모델이 맞다는 증거가 뭐냐"고
물으면 자신있게 답하기 어렵다.

**Yeast8** (https://github.com/SysBioChalmers/yeast-GEM) 은 *S. cerevisiae*의
검증된 genome-scale metabolic model이다. 4131개 반응, 2806개 대사물질,
1161개 유전자가 들어 있다. 시스템생명공학 학계의 표준 도구다.

v0.3부터는 **Yeast8을 backend로 두고, 그 위에 v0.1/v0.2의 *철학*만 얹는다**:
- 변동성 주입 (Monte Carlo wrapper)
- 호르메시스 가설 (intermittent feeding 비교)
- 통계적 안전장치 (multiple comparison, search inflation)

ABM이 사라지는 게 아니라, *engine이 교체*된다.

## 무엇이 살아남고 무엇이 바뀌나

| v0.1/v0.2의 것 | v0.3에서 | 이유 |
|---|---|---|
| Agent-Based Model | ❌ → Yeast8 dFBA | 검증된 모델로 |
| Monte Carlo wrapper | ✅ 그대로 | 핵심 contribution |
| Statistical safeguards | ✅ 그대로 | Taleb framework |
| Data infrastructure | ✅ 그대로 | 균주/조건 통합 |
| Streamlit UI | 보류 | 일단 Colab notebook으로 |
| Hormesis hypothesis | ✅ 그대로 | 검증 대상 |

## 단계 (마일스톤)

1. **Step 1 — Yeast8 손에 익히기** (`01_yeast8_basics.ipynb`)
   - 모델 다운로드, FBA, dFBA basics
   - 학습 일지 작성 (모르는 것 솔직히 기록)
   - *현재 단계*

2. **Step 2 — Monte Carlo wrapper** (`02_yeast8_monte_carlo.ipynb`, 미작성)
   - dFBA를 N번 반복하면서 파라미터 sampling
   - 결과 분포 분석

3. **Step 3 — Hormesis hypothesis 검증** (`03_yeast8_hormesis.ipynb`, 미작성)
   - Pulsed vs Constant feeding 비교
   - 너의 v0.2 통계 안전장치 그대로 적용
   - 결과가 v0.1 ABM과 *같은 방향*인지 확인

4. **Step 4 — Black swan robustness** (`04_yeast8_blackswan.ipynb`, 미작성)
   - Toxin/inhibitor pulse 주입
   - Robustness 비교

## Yeast8 위에서 *진짜* 검증하려는 것

> **"intermittent feeding이 constant feeding보다 fat-tailed disturbance 하에서
> 더 robust한가?"**

세 가지 가능한 결과:
- **A**: 같은 패턴 (v0.1과 일치) → 호르메시스 가설이 *검증된 모델 위에서도* 성립.
- **B**: 반대 패턴 → v0.1 ABM이 *과한 가정*을 했음을 정직하게 발견.
- **C**: 모호한 패턴 → 어떤 조건에서 효과가 나타나는지 추가 분석.

A/B/C 셋 다 가치 있다.

## 실행 방법

각 notebook을 Google Colab에 업로드하고 위에서부터 실행하면 된다.
설치 필요 없음. 첫 실행 시 cobra 패키지만 자동 설치된다.

## 한계 — 정직하게

- Yeast8 dFBA는 *집단 평균* 결정적 모델이다. v0.1 ABM이 가진
  *cell-to-cell variability*는 *구조적으로* 없다. 우리는 그걸
  *외부 wrapper*에서 *파라미터 sampling*으로 *대신* 표현한다.
  이는 trade-off다 — 더 검증된 모델이지만 더 거시적이다.
- Yeast8은 *유전자 발현 동역학*을 다루지 않는다. 호르메시스의 핵심인
  "stress response gene induction"을 직접 표현 못 한다. 우리는 그걸
  *enzyme upper bound constraint 변화*로 *대리*한다. 이게 충분한
  대리인지가 v0.3의 진짜 질문이다.
