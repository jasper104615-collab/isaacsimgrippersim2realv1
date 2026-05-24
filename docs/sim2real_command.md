# Isaac Sim → Doosan E0509 Sim2Real 실행 명령

브리지: `isaac_sim_2_real` / `sub_joint_state.py`  
파라미터: `motion_mode` = `move_joint` (amovej) | `servoj_rt` | `servoj`

---

## 0. 한 번만 (빌드)

```bash
source /opt/ros/humble/setup.bash
cd /home/user/doosan-robot2
source install/setup.bash
cd /home/user/ros2_isaac_sim_2_real
source /home/user/doosan-robot2/install/setup.bash
colcon build --packages-select isaac_sim_2_real
source install/setup.bash
```

---

## 1. 공통 — 터미널 1 (두산 bringup)

### Virtual (RViz + 에뮬레이터, twin 테스트)

```bash
source /opt/ros/humble/setup.bash
cd /home/user/doosan-robot2
source install/setup.bash

ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=virtual host:=127.0.0.1 port:=12345 model:=e0509
```

### Real (실로봇)

```bash
source /opt/ros/humble/setup.bash
cd /home/user/doosan-robot2
source install/setup.bash

ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real host:=<로봇_IP> port:=12345 model:=e0509
```

---

## 2. 공통 — 터미널 2 (Isaac Sim)

Isaac Sim 실행 후 E0509 USD 재생  
→ **`/isaac/joint_states`** 토픽이 나가야 함 (기본 입력 토픽)

확인:

```bash
source /opt/ros/humble/setup.bash
ros2 topic hz /isaac/joint_states
ros2 topic echo /isaac/joint_states --field name,position
```

---

## 3. 공통 — 터미널 3 (브리지 실행 전)

```bash
source /opt/ros/humble/setup.bash
cd /home/user/ros2_isaac_sim_2_real
source /home/user/doosan-robot2/install/setup.bash
source install/setup.bash
```

---

## 4. move_joint 모드 (amovej) — **안정 twin / virtual 권장**

| 항목 | 값 |
|------|-----|
| ROS | Service `/dsr01/motion/move_joint` |
| DRFL | `amovej` (`move_joint_sync_type:=1`, 기본) |
| 용도 | Digital twin, virtual RViz, real 안정 추종 |

### 4-1. Virtual 기본 (추천)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=10.0 \
  -p move_joint_sync_type:=1 \
  -p move_joint_min_delta_deg:=1.0
```

### 4-2. Real (안정 twin)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=10.0 \
  -p move_joint_sync_type:=1 \
  -p move_joint_min_delta_deg:=1.0 \
  -p velocity_deg_s:=20.0 \
  -p acceleration_deg_s2:=20.0
```

### 4-3. 조금 더 따라가게 (real move_joint):
```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p move_joint_sync_type:=1 \
  -p max_publish_hz:=15.0 \
  -p move_joint_min_delta_deg:=0.5 \
  -p velocity_deg_s:=30.0 \
  -p acceleration_deg_s2:=20.0
```

### 4-4. Hz 1 (느리게 테스트)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=1.0
```

### 4-5. 로그만 (로봇 안 움직임)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=false
```

---

## 5. servoj_rt 모드 — **real 실시간 추종**

| 항목 | 값 |
|------|-----|
| ROS | Topic `/dsr01/servoj_rt_stream` |
| DRFL | `servoj_rt` (RT 채널) |
| 용도 | Isaac pose 실시간 mirroring |
| 주의 | virtual에서 거의 무효, 노이즈·떨림 튜닝 필요 |

### 5-1. Real 기본

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=servoj_rt \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=15.0 \
  -p velocity_deg_s:=30.0 \
  -p acceleration_deg_s2:=20.0 \
  -p min_publish_delta_deg:=0.2 \
  -p smoothing_alpha:=0.15 \
  -p tracking_step_max_deg:=3.0
```

### 5-2. Real (떨림 줄이기 — 보수 튜닝)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=servoj_rt \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=15.0 \
  -p velocity_deg_s:=10.0 \
  -p acceleration_deg_s2:=10.0 \
  -p min_publish_delta_deg:=0.5 \
  -p smoothing_alpha:=0.05 \
  -p tracking_step_max_deg:=2.0
```

### 5-3. Hz 1 (동작 확인용, 느림)

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=servoj_rt \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=1.0
```

---

## 6. 모드 비교 (한 줄)

| 모드 | 명령 핵심 | Virtual | Real |
|------|-----------|---------|------|
| **move_joint** | `-p motion_mode:=move_joint` | ◎ RViz twin | ◎ 안정 |
| **servoj_rt** | `-p motion_mode:=servoj_rt` | △ 거의 안 됨 | ◎ 빠름, 튜닝 필요 |

---

## 7. 동작 확인 (선택 — 터미널 4)

```bash
source /opt/ros/humble/setup.bash
source /home/user/doosan-robot2/install/setup.bash

# Isaac 입력
ros2 topic hz /isaac/joint_states

# move_joint 모드: 서비스 호출 빈도 (직접 hz는 service call이라 로그로 확인)
ros2 service list | grep move_joint

# servoj_rt 모드: RT 스트림
ros2 topic hz /dsr01/servoj_rt_stream

# 로봇 실제 관절 (RViz / 피드백)
ros2 topic echo /dsr01/joint_states --field name,position
```

---

## 8. 에뮬레이터 / 로봇 단독 테스트

### move_joint 서비스 직접 호출

```bash
ros2 service call /dsr01/motion/move_joint dsr_msgs2/srv/MoveJoint \
"{pos: [0.0, 0.0, 45.0, 0.0, 45.0, 0.0], vel: 30.0, acc: 30.0, time: 0.0, radius: 0.0, mode: 0, blend_type: 0, sync_type: 1}"
```

- `sync_type: 1` = **amovej** (비동기, sim2real과 동일)

---

## 9. 한 줄 요약

| 터미널 | 내용 |
|--------|------|
| 1 | `ros2 launch dsr_bringup2 ... mode:=virtual\|real model:=e0509` |
| 2 | Isaac Sim → `/isaac/joint_states` |
| 3a twin | `sub_joint_state ... motion_mode:=move_joint enable_motion:=true` |
| 3b real-time | `sub_joint_state ... motion_mode:=servoj_rt enable_motion:=true` |

---

## 10. 자주 쓰는 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `motion_mode` | `servoj_rt` | `move_joint` / `servoj_rt` / `servoj` |
| `input_topic` | `/isaac/joint_states` | Isaac JointState |
| `enable_motion` | `false` | `true`여야 실제 명령 발행 |
| `max_publish_hz` | `15.0` | 브리지 타이머 Hz |
| `move_joint_sync_type` | `1` | 0=movej, **1=amovej** |
| `move_joint_min_delta_deg` | `1.0` | move_joint 재전송 최소 각도 |
| `velocity_deg_s` | `30.0` | servoj_rt / move_joint 속도 |
| `acceleration_deg_s2` | `20.0` | servoj_rt / move_joint 가속도 |
| `min_publish_delta_deg` | `0.2` | servoj_rt 발행 스kip 임계 |
| `startup_calibration` | `true` | 시작 시 로봇↔Isaac 정렬 |

**구버전 주의:** `command_mode`, `min_command_delta_deg`, `max_joint_step_deg` 는 **현재 코드에 없음** → 위 파라미터 사용.
