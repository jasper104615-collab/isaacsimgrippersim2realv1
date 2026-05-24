Isaac Sim 5.1.0에서 그리퍼 마스터-미믹 조인트(Mimic Joint)의 밀림 현상을 해결하기 위한 물리 세팅 가이드입니다.

---

# 🛠️ Isaac Sim 5.1.0 그리퍼 미믹 조인트(Mimic Joint) 밀림 해결 세팅

## 1. Mimic Joint 속성 변경 (Non-compliant 상태 전환)

PhysX 5의 미믹 조인트를 완전 비탄성(Constraint) 모드로 변경하여 수학적으로 강제 고정합니다. 이 설정을 적용하면 별도의 Stiffness(강성) 값을 올리지 않아도 무한대에 가까운 고정 효과를 얻을 수 있습니다.

* **대상:** Stage 패널에서 미믹 관계가 걸려 있는 자식 **Joint** 선택
* **설정 (Property 패널 -> Mimic Joint 섹션):**
* Natural Frequency ➡️ **0.0**으로 수정
* Damping Ratio ➡️ **0.0**으로 수정



---

## 2. 주동 조인트(Main Driven Joint) 모터 힘 상향

미믹 조인트를 단단하게 묶었다면, 실제로 그리퍼를 닫아주는 주동 조인트의 모터(Drive)가 큐브의 반작용력을 이길 수 있도록 최대 토크/힘을 올려주어야 합니다.

* **대상:** 실제 모터 구동을 담당하는 마스터 **Joint** 선택
* **설정 (Property 패널 -> Drive 섹션):**
* Max Force (또는 Max Torque) ➡️ 현재 값보다 훨씬 큰 값(예: **1000.0** ~ **10000.0**)으로 상향 조정



---

## 3. Physics Scene 추가 및 Solver 정밀도 상향 (★필수)

씬에 물리 연산 전반을 담당하는 PhysicsScene이 없다면 새로 생성하고, 충돌 연산 오차를 줄이기 위해 반복 계산 횟수(Iterations)를 높여야 합니다.

### ① PhysicsScene 프림 생성

* 상단 메뉴 바: **Create** ➡️ **Physics** ➡️ **Physics Scene** 클릭
* 결과: Stage 패널 최상단에 **/PhysicsScene** 프림이 생성됨

### ② Solver Iterations 수정

* **대상:** 생성된 **PhysicsScene** 프림 선택
* **설정 (Property 패널 -> PhysxSceneAPI / Advanced 섹션):**
* Position Iterations ➡️ 기본값에서 **32** 또는 **64**로 상향
* Velocity Iterations ➡️ 기본값에서 **8** 또는 **16**으로 상향



---

## 4. (체크리스트) 대상 물체(Cube)의 물리 속성 확인

그리퍼가 잡으려는 큐브에 Rigid Body 속성이 빠져 있으면 고정된 벽처럼 인식되어 미믹 조인트가 부서질 수 있습니다.

* **대상:** Stage 패널에서 **Cube** 선택
* **설정 (Property 패널 맨 아래):**
* **Add** ➡️ **Physics** ➡️ **Rigid Body with Colliders Preset**이 정상적으로 적용되어 있는지 확인합니다.
