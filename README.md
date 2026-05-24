# E0509 Sim2Real + Gripper (Isaac PC용 GitHub 배포)

Isaac Sim PC에서 **git clone 한 번**으로 팔+그리퍼 sim2real.

## DRL 충돌 방지 (중요)

`/dsr01/drl/drl_start`는 **동시에 하나**만 돌아가는 경우가 많습니다.

| 구성 | drl_start | sim2real 병행 |
|------|-----------|---------------|
| 팔 `sub_joint_state` → move_joint / servoj_rt | **사용 안 함** (DRFL) | ✅ |
| 그리퍼 `command_transport:=drl` | **명령마다** | ❌ |
| 그리퍼 `command_transport:=tcp` + `rh_p12_direct` | **초기 1회만** (TCP 서버) | ✅ **권장** |
| 그리퍼 `e0509_topic` | **없음** | ✅ |

**팔 DRL movel + 그리퍼 DRL 동시 사용 금지.**  
그리퍼는 반드시 `command_transport:=tcp` + `gripper_bridge` `rh_p12_direct`.

## 데이터 흐름 (권장)

```
Isaac /isaac/joint_states
  ├─ joint_1~6 ──► sub_joint_state ──► move_joint | servoj_rt  (DRFL)
  └─ rh_r1       ──► gripper_bridge ──► /gripper/cmd_direct
                         ▲
                         └── gripper_service_node (TCP Modbus)
```

## 설치

```bash
git clone https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git ~/sim2real_deploy
source /opt/ros/humble/setup.bash
source ~/doosan-robot2/install/setup.bash
cd ~/sim2real_deploy/ros2_ws
colcon build --packages-select isaac_sim_2_real isaac_gripper_sim2real \
  rh_p12_rna_controller_interfaces rh_p12_rna_controller
source install/setup.bash
```

## 실행 (4터미널)

### T1 — Doosan bringup (팔)

```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real host:=<ROBOT_IP> port:=12345 model:=e0509
```

### T2 — Isaac Sim

`isaac_assets/my_robot/sim_to_real_0519.usda` → Play

### T3 — 팔 sim2real

```bash
ros2 run isaac_sim_2_real sub_joint_state --ros-args \
  -p motion_mode:=move_joint \
  -p enable_motion:=true \
  -p input_topic:=/isaac/joint_states
```

### T4 — 그리퍼 sim2real (권장 launch)

```bash
ros2 launch isaac_gripper_sim2real sim2real_gripper.launch.py \
  robot_ip:=<ROBOT_IP> enable_command:=true
```

`gripper_service_node`(TCP) + `gripper_bridge`(rh_p12_direct) 동시 기동.

## 문서

- `docs/sim2real_command.md` — 팔
- `docs/GRIPPER_SIM2REAL.md` — 그리퍼·DRL
- `ros2_ws/src/isaac_gripper_sim2real/README.md` — 패키지 상세

## GitHub

- Repo: [jasper104615-collab/isaacsimgrippersim2realv1](https://github.com/jasper104615-collab/isaacsimgrippersim2realv1)

### Isaac PC (clone)

```bash
git clone https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git ~/sim2real_deploy
cd ~/sim2real_deploy/ros2_ws
# colcon build ... (위 설치 절차)
```

### 최초 push (개발 PC — `sim2real_deploy/` 내용 올리기)

```bash
cd sim2real_deploy
git init
git add .
git commit -m "E0509 sim2real + gripper bridge (DRL-safe TCP path)"
git branch -M main
git remote add origin https://github.com/jasper104615-collab/isaacsimgrippersim2realv1.git
git push -u origin main
```
