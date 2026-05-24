# Isaac Sim 에셋 (Isaac PC에서 가져온 구조)

`sim2real_bundle` 과 동일한 **상대 경로**를 유지합니다.

```
isaac_assets/
├── my_robot/
│   └── sim_to_real_0519.usda    ← Isaac에서 여기를 연다
└── 0518_project/
    └── cube_pick_and_place/
        └── e0509_with_gripper_v2/   ← USD가 참조하는 그리퍼 메시
```

`sim_to_real_0519.usda` 는 `../0518_project/cube_pick_and_place/e0509_with_gripper_v2/` 를 참조합니다.  
**`my_robot/` 과 `0518_project/` 를 분리하거나 이름을 바꾸지 마세요.**

## Isaac Sim

1. `isaac_assets/my_robot/sim_to_real_0519.usda` 열기
2. Play
3. `ros2 topic echo /isaac/joint_states --field name,position`  
   - 팔 6 + 그리퍼 4 (`rh_r1`, `rh_l1`, `rh_r2`, `rh_l2`)
