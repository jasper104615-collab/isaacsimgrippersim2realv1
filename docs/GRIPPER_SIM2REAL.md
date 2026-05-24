# 그리퍼 Sim2Real + DRL 충돌 회피

## 문제

- 팔 sim2real: `sub_joint_state` → `move_joint` / `servoj_rt` (**DRFL**, `drl_start` 아님)
- 그리퍼 `rh_p12_rna_controller` 기본: `command_transport:=drl` → **매 이동마다 `drl_start`**
- → 팔·그리퍼 **동시 sim2real 불가** (한쪽만 동작)

## 해결

### rh_p12 (권장)

1. `gripper_service_node`: **`command_transport:=tcp`**
   - 시작 시 DRL TCP 서버 **1회** 주입 (백그라운드)
   - 이후 Modbus는 **TCP 소켓** (9105) — `drl_start` 재호출 없음

2. `gripper_bridge`: **`output_mode:=rh_p12_direct`**
   - `/gripper/cmd_direct`에 `custom PULSE CUR` 발행
   - `direct_cmd_topic_enabled:=true`인 gripper_service_node가 큐 처리

```bash
ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<IP> enable_command:=true
```

### e0509 (DRL 완전 분리)

```bash
ros2 run isaac_gripper_sim2real gripper_bridge --ros-args \
  -p output_mode:=e0509_topic -p enable_command:=true
```

`e0509_gripper_description` bringup 필요. Flange Modbus만 사용.

## 금지

- sim2real 중 `command_transport:=drl` on gripper
- `gripper_service_node` + `e0509` C++ gripper Modbus **동시** 기동

## 변환

`rh_r1` [rad] 0~1.101 → pulse 100~420 (또는 stroke 0~700)

## 확인

```bash
ros2 topic echo /gripper/cmd_direct
ros2 topic hz /dsr01/servoj_rt_stream
```

둘 다 Hz 나오면 팔·그리퍼 **병행 OK**.
