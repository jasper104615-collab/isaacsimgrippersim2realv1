# Isaac Sim → Doosan E0509 Sim2Real  
## MoveJ / ServoJ / ServoJ_RT 정리 (발표용)

> **프로젝트:** `/home/user/ros2_isaac_sim_2_real` — `isaac_sim_2_real` 패키지  
> **브리지:** `sub_joint_state.py`  
> **로봇:** 두산 E0509 (`dsr_bringup2`, `mode:=real`)

---

## 1. 전체 구조 (한 장 요약)

```
Isaac Sim  (/isaac/joint_states)
      ↓
sub_joint_state  (브리지)
      ↓
ROS2  (dsr_controller2)
      ↓
DRFL  (Doosan Robot Framework Library)
      ↓
DRCF  (로봇 컨트롤러 펌웨어)
      ↓
실제 E0509
```

| 계층 | 역할 |
|------|------|
| **Isaac** | 시뮬 관절각 발행 (`state:angular:physics:position`) |
| **브리지** | rad→deg, 필터, 모드별 명령 변환 |
| **ROS2** | 서비스(`move_joint`) 또는 토픽(`servoj_*_stream`) |
| **DRFL** | PC ↔ 컨트롤러 소켓 API |
| **DRCF** | 실제 모션 실행 |

---

## 2. 세 가지 모션 API 비교 (핵심 슬라이드)

| 항목 | **movej / amovej** | **servoj** | **servoj_rt** |
|------|-------------------|------------|---------------|
| ROS 인터페이스 | Service `/dsr01/motion/move_joint` | Topic `/dsr01/servoj_stream` | Topic `/dsr01/servoj_rt_stream` |
| DRFL API | `movej` / `amovej` | `servoj(..., mode)` | `servoj_rt(...)` |
| 통신 | 일반 TCP (12345) | 일반 TCP | **RT 채널** (`rt_host`) |
| 명령 단위 | **waypoint 1개** → 플래너가 구간 이동 | 연속 관절 목표 | **고주기** 연속 관절 목표 |
| 추천 Hz | 3~10 Hz | 낮음 | 15~125 Hz |
| sim2real twin | **◎ 안정** | △ real에서도 약함 | ◎ 빠름, **떨림 주의** |
| virtual 모드 | `amovej` 경로로 동작 | **거의 무효** | RT/real 위주 |

---

## 3. movej vs amovej (move_joint 서비스)

**같은 서비스 `/motion/move_joint`, `sync_type`으로 분기**

| `sync_type` | DRFL | 동작 |
|-------------|------|------|
| **0 (SYNC)** | `movej` | 모션 **완료까지** 대기 후 응답 |
| **1 (ASYNC)** | `amovej` | 명령 접수 후 **즉시** 응답 (백그라운드 이동) |

**우리 브리지 기본값:** `move_joint_sync_type := 1` → **amovej**

**동작 방식 (move_joint 모드):**
- 타이머 `max_publish_hz`(기본 15 Hz)마다 Isaac 목표 확인
- 이전 목표 대비 **≥ 1°** (`move_joint_min_delta_deg`) 일 때만 `move_joint` 호출
- `move_in_flight` — 이전 서비스 응답 전에는 다음 호출 안 함
- 실로봇은 **waypoint를 순차적으로** 따라감 (servoj처럼 매 tick 관절 스트림 아님)

**다른 팀 코드와 동일 계열:**
- `MoveJoint` + `sync_type=1` + `call_async` + rate limit(10 Hz)

---

## 4. servoj vs servoj_rt

### 4.1 servoj (non-RT)

- 메시지: `pos, vel, acc, time, **mode**`
- **mode**
  - `0` Override — 최신 목표만 추종
  - `1` Queue — 경유점 최대 100개 순차 재생
- Isaac **미세 노이즈**를 Queue에 쌓으면 **오히려 악화** 가능
- **virtual / real sim2real:** 반응 약함 (검증 결과)

### 4.2 servoj_rt (RT)

- 메시지: `pos, vel, acc, time` (**mode 없음**)
- RT 제어 세션 위에서 **고주기** 관절 목표 스트림
- **real에서 실제로 움직임** (검증됨)
- **6축 전부** 매 tick 목표 갱신 → Isaac state 노이즈에 **민감**
- joint_1만 움직여도 **다른 축 위아래 흔들림** 관찰

### 4.3 선택 가이드

| 목적 | 권장 |
|------|------|
| Digital twin / 안정 검증 | **move_joint (amovej)** |
| 실시간 mirroring (빠른 반응) | **servoj_rt** + 튜닝 |
| virtual RViz 테스트 | **move_joint** (servoj 무효) |

---

## 5. 우리 코드 (`sub_joint_state.py`) 요약

### 5.1 motion_mode 3종

```bash
# 1) 실시간 (기본)
-p motion_mode:=servoj_rt

# 2) non-RT servoj
-p motion_mode:=servoj

# 3) 안정 twin
-p motion_mode:=move_joint
```

### 5.2 파이프라인

```
Isaac raw (deg)
  → EMA smoothing (smoothing_alpha)
  → [streaming] ramp (tracking_step)
  → [move_joint] min_delta / hold / move_in_flight
  → ROS 발행
```

### 5.3 주요 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `max_publish_hz` | 15 | 브리지 타이머 주기 |
| `move_joint_sync_type` | 1 | amovej |
| `move_joint_min_delta_deg` | 1.0 | move_joint 최소 변화 |
| `velocity_deg_s` / `acceleration_deg_s2` | 30 / 20 | servoj·move_joint 공통 |
| `min_publish_delta_deg` | 0.2 | servoj_rt 발행 스킵 임계 |
| `smoothing_alpha` | 0.15 | Isaac 입력 EMA |

### 5.4 Hz 1로 테스트

```bash
-p max_publish_hz:=1.0
```

---

## 6. 검증 결과 (실험 요약)

| 테스트 | 결과 |
|--------|------|
| `move_joint` + virtual | **joint_1 잘 따라감** (RViz OK) |
| `servoj` + virtual | **거의 안 움직임** |
| `servoj_rt` + real | **움직이려 함**, 떨림·충돌(9011) 가능 |
| `max_publish_hz=1` + servoj_rt | joint_1만 움직여도 **타축 흔들림** |
| 입력 deadband (0.3°) | 목표 미도달·흔들림 유지 → **제거** |

---

## 7. Isaac 쪽 이슈 (떨림 원인)

**ROS2PublishJointState**는 Physics Inspector의 **drive target**이 아니라  
**PhysX `state:angular:physics:position`** 을 발행.

| 현상 | 원인 |
|------|------|
| 고정 pose인데 값 변동 | PD 제어 + articulation 결합 |
| joint_3 target=90°, state≈89.99° | solver 오차 |
| servoj_rt 6축 동시 추종 | **안 움직인 축도** 미세 목표 갱신 |

**대응 (우선순위):**
1. `motion_mode:=move_joint` (twin)
2. servoj_rt: `velocity`/`acc` ↓, `min_publish_delta_deg` ↑
3. Isaac: damping ↑ (stiffness만 ↓는 비추)
4. (선택) drive target 발행 / 출력측 필터

---

## 8. DRFL · H2R (참고, sim2real 비사용)

### DRFL (Doosan Robot Framework Library)
- PC에서 DRCF와 통신하는 **공식 C++ API**
- `dsr_controller2`가 ROS → DRFL 변환
- 일반: `movej`, `servoj` / RT: `servoj_rt`

### H2R (Hold-to-Run)
- **Host-to-Robot 아님** → **홀드 버튼 누른 동안만** 안전 이동
- API: `movej_h2r`, ROS Action `/motion/movej_h2r`
- 실행 중 `hold2run()` ~100 Hz 필요
- **sim2real 자율 mirroring에는 부적합** (move_joint보다 느림·보수적)

---

## 9. 다른 팀 Sim2Real 코드 vs 우리

| | 다른 팀 | 우리 (`sub_joint_state`) |
|--|---------|---------------------------|
| Isaac 입력 | `/joint_states` | `/isaac/joint_states` (기본) |
| 실로봇 | `move_joint` (amovej) | `move_joint` / `servoj` / `servoj_rt` 선택 |
| 트리거 | Isaac **메시지** + 10 Hz limit | **타이머** + min_delta + in-flight |
| MuJoCo | Float64MultiArray 병행 | 없음 |
| 필터 | 없음 | EMA, ramp, hold, min_delta |

---

## 10. 권장 실행 명령 (발표 데모용)

### 안정 Digital Twin (real / virtual)

```bash
source /home/user/doosan-robot2/install/setup.bash
source /home/user/ros2_isaac_sim_2_real/install/setup.bash

ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p max_publish_hz:=10.0 \
  -p move_joint_min_delta_deg:=1.0
```

### 실시간 mirroring (real, 주의)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=servoj_rt \
  -p enable_motion:=true \
  -p max_publish_hz:=15.0 \
  -p velocity_deg_s:=10.0 \
  -p acceleration_deg_s2:=10.0 \
  -p min_publish_delta_deg:=0.5
```

### Bringup (별 터미널)

```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real model:=e0509
```

---

## 11. PPT 슬라이드 구성 제안 (7~10장)

1. **목표** — Isaac Sim pose → 실로봇 E0509 mirroring  
2. **시스템 구조** — Isaac → 브리지 → ROS → DRFL → DRCF  
3. **API 3종 비교표** — movej / servoj / servoj_rt  
4. **amovej waypoint 방식** — move_joint + 다른 팀 코드  
5. **servoj_rt 실시간 방식** — 빠르지만 노이즈 민감  
6. **실험 결과** — virtual/real, 떨림, move_joint 안정  
7. **Isaac state 노이즈** — PhysX state 발행 이슈  
8. **결론·권장** — twin=move_joint, real-time=servoj_rt+튜닝  
9. **(부록)** DRFL, H2R, sync/async  

---

## 12. 한 줄 결론

> **Digital twin·안정 추종 → `move_joint`(amovej) waypoint**  
> **실시간 mirroring → `servoj_rt` (Isaac 입력 품질·튜닝 필수)**  
> **servoj(non-RT)는 sim2real에 잘 맞지 않음**  
> **H2R은 sim2real과 무관 (안전 수동 모드)**

---

## 참고 링크

- [servoj() 매뉴얼 (V3.6.0)](https://manual.doosanrobotics.com/ko/programming-manual/3.6.0/publish/servoj)
- [Doosan ROS2 Manual (Humble)](https://doosanrobotics.github.io/doosan-robotics-ros-manual/humble/index.html)
- 브리지 소스: `/home/user/ros2_isaac_sim_2_real/src/isaac_sim_2_real/isaac_sim_2_real/sub_joint_state.py`
- USD 참고: `/home/user/my_robot/sim_to_real_0519.usda`

---

*작성일: 2026-05-19 · Isaac Sim 5.1.0 + Doosan dsr_bringup2 (E0509) sim2real 검증 기준*
