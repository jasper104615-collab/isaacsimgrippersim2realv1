# isaac_gripper_sim2real

Isaac 그리퍼(`rh_r1`) → 실 RH-P12. **팔 브리지와 반드시 동시에** 켭니다.

> Clone: [isaacsimgrippersim2realv1](https://github.com/jasper104615-collab/isaacsimgrippersim2realv1)  
> **전체 동시 실행 명령:** repo 루트 `README.md` (T1~T5)

---

## 이 패키지 역할 (T4)

| | T3 `sub_joint_state` | **T4 `gripper_bridge` (이 패키지)** |
|--|----------------------|-------------------------------------|
| Isaac에서 가져옴 | `joint_1`~`6` | `rh_r1` |
| 실로봇으로 | move_joint / servoj_rt | `/gripper/cmd_direct` |
| drl_start | 없음 | **명령마다 없음** (tcp 모드) |

**T3 + T4 = 팔 + 그리퍼 동시 sim2real**

---

## 동시 실행 명령 (요약)

```bash
source /opt/ros/humble/setup.bash
source ~/doosan-robot2/install/setup.bash
source ~/sim2real_deploy/ros2_ws/install/setup.bash
```

**T3 팔 (별도 터미널):**

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states
```

**T4 그리퍼 (별도 터미널, T3와 동시):**

```bash
ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<ROBOT_IP> \
  enable_command:=true
```

**확인:**

```bash
ros2 topic hz /isaac/joint_states
ros2 topic hz /dsr01/servoj_rt_stream    # 또는 move_joint 로그
ros2 topic echo /gripper/cmd_direct
```

---

## DRL — 동시 가능 조건

| T3 + T4 조합 | 팔+그리퍼 동시 |
|--------------|----------------|
| move_joint + **tcp** + rh_p12_direct | **✅** |
| servoj_rt + **tcp** + rh_p12_direct | **✅** |
| * + 그리퍼 **drl** | **❌** |

`gripper_service_node`는 **`command_transport:=tcp`** (launch 기본).  
`command_transport:=drl` 쓰면 T3와 **동시 불가**.

---

## 출력 모드

| `output_mode` | 출력 | T3와 동시 |
|---------------|------|-----------|
| **`rh_p12_direct`** (기본) | `/gripper/cmd_direct` | ✅ |
| `rh_p12_service` | `/gripper/set_position` srv | ✅ (느림) |
| `e0509_topic` | `/dsr01/gripper/position_cmd` | ✅ (e0509 bringup) |

---

## 변환

```
t = clamp(rh_r1 / 1.101, 0, 1)
pulse = round(100 + t * 320)
```

---

## 빌드

```bash
cd ~/sim2real_deploy/ros2_ws
colcon build --packages-select \
  rh_p12_rna_controller_interfaces rh_p12_rna_controller isaac_gripper_sim2real
source install/setup.bash
```

설정: `config/sim2real_gripper.yaml`
