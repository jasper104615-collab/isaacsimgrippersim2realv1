# isaac_gripper_sim2real

Isaac Sim 그리퍼(`rh_r1`, rad) → 실제 RH-P12 그리퍼.  
팔 sim2real은 `isaac_sim_2_real/sub_joint_state.py`, **이 패키지는 그리퍼만** 담당.

> Isaac PC: [isaacsimgrippersim2realv1](https://github.com/jasper104615-collab/isaacsimgrippersim2realv1)  
> `git clone https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git ~/sim2real_deploy`

---

## DRL 충돌 — 왜 구조를 나눴는가

Doosan **`/dsr01/drl/drl_start`는 동시에 하나**만 실행되는 경우가 많습니다.

| 경로 | drl_start 사용 | sim2real 동시 실행 |
|------|----------------|-------------------|
| 팔 `sub_joint_state` → `move_joint` / `servoj_rt` | **없음** (DRFL API) | ✅ |
| 그리퍼 `command_transport:=drl` (기본값) | **매 명령마다** | ❌ 팔·그리퍼 동시 불가 |
| 그리퍼 `command_transport:=tcp` | **초기 1회** (TCP 서버 주입) | ✅ 이후 TCP 소켓만 |
| 그리퍼 `e0509_topic` | **없음** (Flange Modbus) | ✅ |

### 권장 sim2real 구조

```
Isaac /isaac/joint_states
  ├─ joint_1~6 ──► sub_joint_state ──► move_joint | servoj_rt  (DRFL, drl_start X)
  └─ rh_r1       ──► gripper_bridge ──► /gripper/cmd_direct     (TCP Modbus, drl_start X per cmd)
                         ▲
                         └── gripper_service_node (command_transport:=tcp)
```

**절대 금지:** sim2real 중 `gripper_service_node`에 `command_transport:=drl`  
(매 `set_position` / direct cmd가 `drl_start` 점유 → 팔 DRL movel·servoj와 충돌)

---

## 출력 모드 (`output_mode`)

| 모드 | 출력 | DRL | sim2real 권장 |
|------|------|-----|---------------|
| **`rh_p12_direct`** (기본) | `/gripper/cmd_direct` String `custom PULSE CUR` | TCP만 | **◎** |
| `rh_p12_service` | `/gripper/set_position` srv | TCP만 | △ (동기, 느림) |
| `e0509_topic` | `/dsr01/gripper/position_cmd` Int32 | 없음 | ◎ (e0509 bringup 시) |

`rh_p12_direct`는 `gripper_service_node`의 **비동기 큐 + TCP Modbus** 경로를 씁니다.

---

## 변환 (URDF 63°)

```
t = clamp((θ - 0) / 1.101, 0, 1)
pulse  = round(100 + t * (420 - 100))   # rh_p12
stroke = round(t * 700)                 # e0509
```

---

## 빌드

```bash
source /opt/ros/humble/setup.bash
cd sim2real_deploy/ros2_ws
colcon build --packages-select \
  rh_p12_rna_controller_interfaces rh_p12_rna_controller isaac_gripper_sim2real
source install/setup.bash
```

---

## 실행 (권장 — launch 한 번)

```bash
# T1: dsr_bringup2 (팔)
# T2: Isaac Sim → /isaac/joint_states
# T3: sub_joint_state (팔)
# T4: 그리퍼 (아래)

ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<로봇_IP> enable_command:=true
```

launch가 띄우는 것:
- `gripper_service_node` — `command_transport:=tcp`, `direct_cmd_topic_enabled:=true`
- `gripper_bridge` — `output_mode:=rh_p12_direct`

### 수동 실행

**1) gripper owner (TCP 필수)**

```bash
ros2 run rh_p12_rna_controller gripper_service_node --ros-args \
  -p robot_ns:=dsr01 \
  -p command_transport:=tcp \
  -p tcp_external_server:=false \
  -p robot_ip:=<로봇_IP> \
  -p robot_port:=9105 \
  -p direct_cmd_topic_enabled:=true \
  -p direct_cmd_topic:=/gripper/cmd_direct \
  -p gripper_command_action_enabled:=false
```

**2) Isaac 브리지**

```bash
ros2 run isaac_gripper_sim2real gripper_bridge --ros-args \
  -p enable_command:=true \
  -p output_mode:=rh_p12_direct \
  -p direct_cmd_topic:=/gripper/cmd_direct \
  -p closed_rad:=1.101
```

### e0509 (DRL 완전 분리)

```bash
ros2 run isaac_gripper_sim2real gripper_bridge --ros-args \
  -p enable_command:=true \
  -p output_mode:=e0509_topic \
  -p robot_ns:=dsr01
```

---

## 확인

```bash
ros2 topic echo /isaac/joint_states --field name,position
ros2 topic echo /gripper/cmd_direct
ros2 topic hz /dsr01/servoj_rt_stream   # 팔 (sub_joint_state)
```

---

## 파라미터 요약

| 파라미터 | 기본 | 설명 |
|----------|------|------|
| `output_mode` | `rh_p12_direct` | 위 표 참고 |
| `enable_command` | `false` | `true`여야 실제 전송 |
| `closed_rad` | `1.101` | URDF upper (63°) |
| `direct_cmd_topic` | `/gripper/cmd_direct` | rh_p12_direct 출력 |
| `goal_current` | `300` | Modbus goal current |

설정 파일: `config/sim2real_gripper.yaml`
