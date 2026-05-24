# 그리퍼 Sim2Real — T4 (팔 T3와 **동시** 실행)

## 전제: 팔+그리퍼 둘 다 필요

`/isaac/joint_states`에는 팔 6 + 그리퍼 4가 **한 메시지**로 옵니다.

- **T3** `sub_joint_state` → `joint_1~6`만 실로봇
- **T4** `gripper_bridge` → `rh_r1`만 실로봇

**둘 다 켜야** Isaac pose 전체가 real에 반영됩니다.

---

## 동시 sim2real 명령 (T3 + T4)

### source (공통)

```bash
source /opt/ros/humble/setup.bash
source ~/doosan-robot2/install/setup.bash
source ~/sim2real_deploy/ros2_ws/install/setup.bash
```

### T3 — 팔

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states \
  -p max_publish_hz:=10.0 \
  -p move_joint_sync_type:=1
```

### T4 — 그리퍼 (T3 **켜진 상태에서** 같은 Isaac Play)

```bash
ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<ROBOT_IP> \
  enable_command:=true
```

launch 내부:
- `gripper_service_node`: `command_transport:=tcp`, `direct_cmd_topic_enabled:=true`
- `gripper_bridge`: `output_mode:=rh_p12_direct`, `enable_command:=true`

---

## 왜 tcp인가 (동시 가능 이유)

| | drl_start per move | T3와 동시 |
|--|---------------------|-----------|
| T3 move_joint/servoj_rt | 없음 (DRFL) | — |
| T4 + `command_transport:=drl` | **매번** | ❌ |
| T4 + `command_transport:=tcp` | **없음** (초기 TCP 서버 1회) | ✅ |

---

## 확인 (동시 OK 판정)

```bash
ros2 topic hz /isaac/joint_states          # Isaac → ROS
ros2 topic echo /gripper/cmd_direct        # T4 출력
ros2 topic hz /dsr01/servoj_rt_stream      # T3 servoj_rt 시
# move_joint면 sub_joint_state 로그에 move_joint ok
```

세 경로 모두 살아 있으면 **팔+그리퍼 동시 sim2real** 동작 중.

---

## 금지

- T4만 켜고 T3 안 켬 → 그리퍼만 움직임
- `command_transport:=drl` → T3와 충돌
- e0509 C++ gripper + rh_p12 gripper_service_node 동시 Modbus

---

## 변환

`rh_r1` 0 rad → pulse 100 (열림), 1.101 rad → pulse 420 (닫힘)
