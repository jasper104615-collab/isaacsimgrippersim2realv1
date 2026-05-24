# E0509 Sim2Real + Gripper (Isaac PC)

Isaac Sim → **팔 + 그리퍼 동시** real mirroring.

| | |
|--|--|
| **Repo** | [jasper104615-collab/isaacsimgrippersim2realv1](https://github.com/jasper104615-collab/isaacsimgrippersim2realv1) |
| **Clone** | `git clone https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git ~/sim2real_deploy` |
| **상세 문서** | [docs/ARCHITECTURE_AND_WORKFLOW.md](docs/ARCHITECTURE_AND_WORKFLOW.md) — 파일구조·작동방식·Workflow |

---

## 핵심: T3 + T4 둘 다 켜야 함

| 터미널 | 노드 | Isaac joint | → Real |
|--------|------|-------------|--------|
| **T3** | `sub_joint_state` | `joint_1~6` | E0509 팔 6축 |
| **T4** | `gripper_bridge` + `gripper_service_node` | `rh_r1` | RH-P12 그리퍼 |

T3만 → 팔만 / T4만 → 그리퍼만 / **T3+T4** → **전체 sim2real**

---

## Repo 구조 (요약)

```
sim2real_deploy/
├── isaac_assets/my_robot/sim_to_real_0519.usda   ← T2 Isaac 씬
├── ros2_ws/src/
│   ├── isaac_sim_2_real/          ← T3 팔
│   ├── isaac_gripper_sim2real/    ← T4 그리퍼 브리지
│   └── rh_p12_rna_controller*/    ← T4 Modbus/TCP
└── docs/ARCHITECTURE_AND_WORKFLOW.md
```

→ [전체 트리·메시지 형식·mermaid 다이어그램](docs/ARCHITECTURE_AND_WORKFLOW.md)

---

## 0. 설치 (1회)

```bash
git clone https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git ~/sim2real_deploy

source /opt/ros/humble/setup.bash
source ~/doosan-robot2/install/setup.bash

cd ~/sim2real_deploy/ros2_ws
colcon build --packages-select \
  isaac_sim_2_real isaac_gripper_sim2real \
  rh_p12_rna_controller_interfaces rh_p12_rna_controller
source install/setup.bash
```

---

## Workflow — 터미널별 명령

### 공통 source (T1·T3·T4·T5)

```bash
source /opt/ros/humble/setup.bash
source ~/doosan-robot2/install/setup.bash
source ~/sim2real_deploy/ros2_ws/install/setup.bash
```

### T1 — Doosan bringup

```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real host:=<ROBOT_IP> port:=12345 model:=e0509
```

### T2 — Isaac Sim

`~/sim2real_deploy/isaac_assets/my_robot/sim_to_real_0519.usda` → **Play**

```bash
ros2 topic hz /isaac/joint_states
```

### T3 — 팔 sim2real

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=10.0 \
  -p move_joint_sync_type:=1
```

### T4 — 그리퍼 sim2real (**T3와 동시**)

```bash
ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<ROBOT_IP> enable_command:=true
```

### T5 — 확인

```bash
ros2 topic hz /isaac/joint_states
ros2 topic echo /gripper/cmd_direct --once
ros2 topic echo /gripper/state --field position --once
```

---

## 동시 sim2real 가능 이유

| | drl_start | T3+T4 동시 |
|--|-----------|------------|
| T3 move_joint / servoj_rt | 없음 (DRFL) | ✅ |
| T4 `command_transport:=tcp` | 명령마다 없음 | ✅ |
| T4 `command_transport:=drl` | 명령마다 | ❌ |

launch는 **tcp 고정**. 그리퍼 drl 모드 쓰지 말 것.

---

## 데이터 흐름

```
Isaac /isaac/joint_states
  ├─ joint_1~6 ──► T3 sub_joint_state ──► move_joint | servoj_rt ──► E0509 팔
  └─ rh_r1       ──► T4 gripper_bridge ──► /gripper/cmd_direct
                                           └── gripper_service_node (TCP) ──► RH-P12
```

---

## 문서

| 파일 | 내용 |
|------|------|
| [docs/ARCHITECTURE_AND_WORKFLOW.md](docs/ARCHITECTURE_AND_WORKFLOW.md) | **파일구조·작동방식·Workflow 전체** |
| [docs/GRIPPER_SIM2REAL.md](docs/GRIPPER_SIM2REAL.md) | T4·DRL |
| [docs/sim2real_command.md](docs/sim2real_command.md) | T3·튜닝 |
| [ros2_ws/src/isaac_gripper_sim2real/README.md](ros2_ws/src/isaac_gripper_sim2real/README.md) | T4 API |

---

## 금지

- T3 또는 T4 **하나만** 실행
- `command_transport:=drl` (T3와 충돌)
- `enable_motion:=false` / `enable_command:=false`
