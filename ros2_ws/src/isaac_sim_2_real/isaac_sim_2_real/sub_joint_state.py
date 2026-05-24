"""Bridge Isaac JointState to Doosan: servoj_rt (streaming) or move_joint (stable twin)."""

import math
from typing import Sequence

from dsr_msgs2.msg import ServojRtStream, ServojStream  # type: ignore[import-not-found]
from dsr_msgs2.srv import MoveJoint  # type: ignore[import-not-found]
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState

MOTION_SERVOJ_RT = 'servoj_rt'
MOTION_SERVOJ = 'servoj'
MOTION_MOVE_JOINT = 'move_joint'


class DoosanJointStateBridge(Node):
    """Isaac sim2real bridge for E0509."""

    def __init__(self) -> None:
        super().__init__('sub_joint_state')

        self.declare_parameter('input_topic', '/isaac/joint_states')
        self.declare_parameter('robot_feedback_topic', '/dsr01/joint_states')
        self.declare_parameter(
            'motion_mode', MOTION_SERVOJ_RT,
        )
        self.declare_parameter('servoj_topic', '/dsr01/servoj_stream')
        self.declare_parameter('servoj_rt_topic', '/dsr01/servoj_rt_stream')
        self.declare_parameter(
            'move_joint_service', '/dsr01/motion/move_joint',
        )
        self.declare_parameter(
            'joint_names',
            ['joint_1', 'joint_2', 'joint_3',
             'joint_4', 'joint_5', 'joint_6'],
        )
        self.declare_parameter('source_joint_names', [])
        self.declare_parameter('enable_motion', False)
        self.declare_parameter('input_in_radians', True)
        self.declare_parameter('use_dual_input_qos', True)
        self.declare_parameter('input_timeout_sec', 3.0)
        self.declare_parameter('max_publish_hz', 15.0)
        self.declare_parameter('servo_time', 0.0)
        self.declare_parameter('velocity_deg_s', 30.0)
        self.declare_parameter('acceleration_deg_s2', 20.0)
        self.declare_parameter('servoj_mode', 1)
        self.declare_parameter('tracking_step_deg', 0.5)
        self.declare_parameter('tracking_step_max_deg', 3.0)
        self.declare_parameter('min_publish_delta_deg', 0.2)
        self.declare_parameter('smoothing_alpha', 0.15)
        self.declare_parameter('smoothing_reset_delta_deg', 5.0)
        self.declare_parameter('startup_calibration', True)
        self.declare_parameter('calibration_step_deg', 0.3)
        self.declare_parameter('calibration_done_deg', 2.0)
        self.declare_parameter('calibration_robot_done_deg', 1.5)
        self.declare_parameter('calibration_settle_sec', 2.0)
        self.declare_parameter('calibration_velocity_deg_s', 15.0)
        self.declare_parameter('calibration_acceleration_deg_s2', 10.0)
        self.declare_parameter('hold_enter_deg', 2.0)
        self.declare_parameter('hold_exit_deg', 3.0)
        self.declare_parameter('move_joint_min_delta_deg', 1.0)
        self.declare_parameter('move_joint_sync_type', 1)
        self.declare_parameter('enforce_joint_limits', True)
        self.declare_parameter(
            'min_joint_limits_deg',
            [-180.0, -95.0, -135.0, -180.0, -135.0, -180.0],
        )
        self.declare_parameter(
            'max_joint_limits_deg',
            [180.0, 95.0, 135.0, 180.0, 135.0, 180.0],
        )
        self.declare_parameter('debug_log_hz', 2.0)

        self.motion_mode = self._param_str('motion_mode').strip().lower()
        if self.motion_mode not in (
            MOTION_SERVOJ_RT,
            MOTION_SERVOJ,
            MOTION_MOVE_JOINT,
        ):
            raise ValueError(
                f"motion_mode must be '{MOTION_SERVOJ_RT}', "
                f"'{MOTION_SERVOJ}', or '{MOTION_MOVE_JOINT}'."
            )

        self.is_streaming = self.motion_mode in (
            MOTION_SERVOJ_RT,
            MOTION_SERVOJ,
        )
        self.input_topic = self._param_str('input_topic')
        self.robot_feedback_topic = self._param_str('robot_feedback_topic')
        self.servoj_topic = self._param_str('servoj_topic')
        self.servoj_rt_topic = self._param_str('servoj_rt_topic')
        self.move_joint_service = self._param_str('move_joint_service')
        self.joint_names = self._param_str_list('joint_names')
        self.source_joint_names = self._param_str_list('source_joint_names')
        self.enable_motion = self._param_bool('enable_motion')
        self.input_in_radians = self._param_bool('input_in_radians')
        self.use_dual_input_qos = self._param_bool('use_dual_input_qos')
        self.input_timeout_sec = self._param_float('input_timeout_sec')
        self.max_publish_hz = self._param_float('max_publish_hz')
        self.servo_time = self._param_float('servo_time')
        self.velocity_deg_s = self._param_float('velocity_deg_s')
        self.acceleration_deg_s2 = self._param_float('acceleration_deg_s2')
        self.servoj_mode = self._param_int('servoj_mode')
        self.tracking_step_deg = self._param_float('tracking_step_deg')
        self.tracking_step_max_deg = self._param_float('tracking_step_max_deg')
        self.min_publish_delta_deg = self._param_float('min_publish_delta_deg')
        self.smoothing_alpha = self._param_float('smoothing_alpha')
        self.smoothing_reset_delta_deg = self._param_float(
            'smoothing_reset_delta_deg'
        )
        self.startup_calibration = self._param_bool('startup_calibration')
        self.calibration_step_deg = self._param_float('calibration_step_deg')
        self.calibration_done_deg = self._param_float('calibration_done_deg')
        self.calibration_robot_done_deg = self._param_float(
            'calibration_robot_done_deg'
        )
        self.calibration_settle_sec = self._param_float('calibration_settle_sec')
        self.calibration_velocity_deg_s = self._param_float(
            'calibration_velocity_deg_s'
        )
        self.calibration_acceleration_deg_s2 = self._param_float(
            'calibration_acceleration_deg_s2'
        )
        self.hold_enter_deg = self._param_float('hold_enter_deg')
        self.hold_exit_deg = self._param_float('hold_exit_deg')
        self.move_joint_min_delta_deg = self._param_float(
            'move_joint_min_delta_deg'
        )
        self.move_joint_sync_type = self._param_int('move_joint_sync_type')
        self.enforce_joint_limits = self._param_bool('enforce_joint_limits')
        self.min_joint_limits_deg = self._param_float_list('min_joint_limits_deg')
        self.max_joint_limits_deg = self._param_float_list('max_joint_limits_deg')
        debug_hz = self._param_float('debug_log_hz')

        if len(self.joint_names) != 6:
            raise ValueError('joint_names must have 6 entries.')
        if self.max_publish_hz <= 0.0:
            raise ValueError('max_publish_hz must be > 0.')

        self.lookup_joint_names = (
            self.source_joint_names or self.joint_names
        )

        self.latest_positions_rad: list[float] | None = None
        self.latest_robot_deg: list[float] | None = None
        self.last_command_deg: list[float] | None = None
        self.last_published_deg: list[float] | None = None
        self.last_move_goal_deg: list[float] | None = None
        self.smoothed_target_deg: list[float] | None = None
        self.robot_synced = False
        self.calibration_done = not self.startup_calibration
        self.calibration_settle_ns: int | None = None
        self.hold_active = False
        self.move_in_flight = False
        self.input_count = 0
        self.command_count = 0
        self.logged_names = False
        self.warned_no_input = False
        self.warned_no_sync = False
        self.start_ns = self.get_clock().now().nanoseconds
        self.last_log_ns = 0
        self.log_period_ns = int(1e9 / debug_hz) if debug_hz > 0.0 else 0

        if self.use_dual_input_qos:
            self.create_subscription(
                JointState, self.input_topic, self._on_isaac, 10)
            self.create_subscription(
                JointState, self.input_topic, self._on_isaac,
                qos_profile_sensor_data)
        else:
            self.create_subscription(
                JointState, self.input_topic, self._on_isaac, 10)

        self.create_subscription(
            JointState, self.robot_feedback_topic, self._on_robot, 10)

        self.servoj_pub = None
        self.servoj_rt_pub = None
        self.move_joint_client = None
        self.output_desc = ''

        if self.motion_mode == MOTION_SERVOJ_RT:
            self.servoj_rt_pub = self.create_publisher(
                ServojRtStream, self.servoj_rt_topic, 10)
            self.output_desc = f'servoj_rt -> {self.servoj_rt_topic}'
        elif self.motion_mode == MOTION_SERVOJ:
            self.servoj_pub = self.create_publisher(
                ServojStream, self.servoj_topic, 10)
            self.output_desc = f'servoj -> {self.servoj_topic}'
        else:
            self.move_joint_client = self.create_client(
                MoveJoint, self.move_joint_service)
            self.output_desc = f'move_joint -> {self.move_joint_service}'

        self.create_timer(1.0 / self.max_publish_hz, self._on_timer)
        if self.input_timeout_sec > 0.0:
            self.create_timer(1.0, self._watchdog_input)

        self.get_logger().info(
            f'motion_mode={self.motion_mode} | {self.output_desc} '
            f'at {self.max_publish_hz:.1f} Hz'
        )
        if self.motion_mode == MOTION_SERVOJ_RT:
            self.get_logger().info(
                'servoj_rt streams joint targets (low Hz can shake other axes). '
                'For stable digital twin use motion_mode:=move_joint.'
            )
        elif self.motion_mode == MOTION_MOVE_JOINT:
            self.get_logger().info(
                'move_joint uses planner motion (safer, not real-time streaming).'
            )
        self.get_logger().info(
            f'Isaac: {self.input_topic} | feedback: {self.robot_feedback_topic}'
        )
        if not self.enable_motion:
            self.get_logger().warn('enable_motion:=false')

    def _on_robot(self, msg: JointState) -> None:
        positions = self._map_positions(msg, self.joint_names)
        if positions is None:
            return
        self.latest_robot_deg = self._to_deg(positions)
        if self.robot_synced:
            return
        self.last_command_deg = list(self.latest_robot_deg)
        self.robot_synced = True
        self.get_logger().info(
            f'Ramp start (robot deg): {self._fmt(self.latest_robot_deg)}'
        )

    def _on_isaac(self, msg: JointState) -> None:
        if not self.logged_names and msg.name:
            self.get_logger().info(f'Isaac joints: {list(msg.name)}')
            self.logged_names = True
        positions = self._map_positions(msg, self.lookup_joint_names)
        if positions is None:
            return
        self.latest_positions_rad = positions
        self.input_count += 1

    def _on_timer(self) -> None:
        if self.latest_positions_rad is None:
            return

        raw_deg = self._clamp(self._to_deg(self.latest_positions_rad))
        calibrating = self.startup_calibration and not self.calibration_done
        target_deg = self._smooth(raw_deg, calibrating)

        if self.is_streaming:
            self._timer_streaming(target_deg, calibrating)
        else:
            self._timer_move_joint(target_deg, calibrating)

    def _timer_streaming(
        self,
        target_deg: list[float],
        calibrating: bool,
    ) -> None:
        robot_err = self._robot_err(target_deg)
        step = (
            self.calibration_step_deg
            if calibrating
            else self._tracking_step(robot_err)
        )
        cmd_deg = self._ramp(target_deg, step)
        now = self.get_clock().now().nanoseconds

        if calibrating:
            self._update_calibration(cmd_deg, target_deg, now)

        self._maybe_log(now, target_deg, cmd_deg, calibrating)

        if not self.enable_motion or not self.robot_synced:
            self._warn_wait_sync()
            return

        use_hold = self.motion_mode == MOTION_SERVOJ
        if use_hold and self._should_hold(cmd_deg, target_deg, calibrating):
            return
        if not self._should_publish(cmd_deg):
            return
        self._publish_stream(cmd_deg, calibrating)

    def _timer_move_joint(
        self,
        target_deg: list[float],
        calibrating: bool,
    ) -> None:
        now = self.get_clock().now().nanoseconds
        cmd_deg = list(target_deg)

        if calibrating:
            if self.latest_robot_deg is None:
                return
            step_target = self._ramp(target_deg, self.calibration_step_deg)
            cmd_deg = step_target
            self._update_calibration(cmd_deg, target_deg, now)
            self._maybe_log(now, target_deg, cmd_deg, calibrating)
            if not self.enable_motion or not self.robot_synced:
                self._warn_wait_sync()
                return
            if self.move_in_flight:
                return
            if self._max_err(cmd_deg, self.latest_robot_deg) < 0.05:
                return
            self._send_move_joint(cmd_deg, cal=True)
            return

        self._maybe_log(now, target_deg, cmd_deg, False)

        if not self.enable_motion or not self.robot_synced:
            self._warn_wait_sync()
            return
        if self.move_in_flight:
            return
        if self._should_hold_move(target_deg):
            return
        if not self._should_send_move(target_deg):
            return
        self._send_move_joint(cmd_deg, cal=False)

    def _send_move_joint(self, goal_deg: Sequence[float], cal: bool) -> None:
        if self.move_joint_client is None:
            return
        if not self.move_joint_client.service_is_ready():
            self.get_logger().warn(
                f'{self.move_joint_service} not ready',
                throttle_duration_sec=2.0,
            )
            return

        req = MoveJoint.Request()
        req.pos = list(goal_deg)
        req.vel = (
            self.calibration_velocity_deg_s
            if cal
            else self.velocity_deg_s
        )
        req.acc = (
            self.calibration_acceleration_deg_s2
            if cal
            else self.acceleration_deg_s2
        )
        req.time = 0.0
        req.radius = 0.0
        req.mode = 0
        req.blend_type = 0
        req.sync_type = self.move_joint_sync_type

        self.move_in_flight = True
        future = self.move_joint_client.call_async(req)
        future.add_done_callback(
            lambda f, g=list(goal_deg): self._on_move_done(f, g)
        )
        self.last_move_goal_deg = list(goal_deg)
        self.command_count += 1

    def _on_move_done(self, future, goal_deg: list[float]) -> None:
        self.move_in_flight = False
        try:
            response = future.result()
            if response.success:
                self.get_logger().debug(
                    f'move_joint ok -> {self._fmt(goal_deg)}'
                )
            else:
                self.get_logger().warn(
                    f'move_joint failed for {self._fmt(goal_deg)}'
                )
        except Exception as exc:
            self.get_logger().error(f'move_joint error: {exc}')

    def _should_hold_move(self, target_deg: Sequence[float]) -> bool:
        if self.hold_enter_deg <= 0.0:
            return False
        thr = self.hold_exit_deg if self.hold_active else self.hold_enter_deg
        robot_err = self._robot_err(target_deg)
        if robot_err >= thr:
            self.hold_active = False
            return False
        if robot_err < thr:
            if not self.hold_active:
                self.hold_active = True
                self.get_logger().info('move_joint hold: at Isaac pose.')
            return True
        self.hold_active = False
        return False

    def _should_send_move(self, target_deg: Sequence[float]) -> bool:
        if self.last_move_goal_deg is None:
            return True
        return (
            self._max_err(target_deg, self.last_move_goal_deg)
            >= self.move_joint_min_delta_deg
        )

    def _publish_stream(
        self,
        cmd_deg: Sequence[float],
        calibrating: bool,
    ) -> None:
        t = self.servo_time if self.servo_time > 0.0 else 1.0 / self.max_publish_hz
        if calibrating:
            vel, acc = self.calibration_velocity_deg_s, self.calibration_acceleration_deg_s2
        else:
            vel, acc = self.velocity_deg_s, self.acceleration_deg_s2

        if self.servoj_rt_pub is not None:
            msg = ServojRtStream()
            msg.pos = list(cmd_deg)
            msg.vel = [vel] * 6
            msg.acc = [acc] * 6
            msg.time = t
            self.servoj_rt_pub.publish(msg)
        elif self.servoj_pub is not None:
            msg = ServojStream()
            msg.pos = list(cmd_deg)
            msg.vel = [vel] * 6
            msg.acc = [acc] * 6
            msg.time = t
            msg.mode = self.servoj_mode
            self.servoj_pub.publish(msg)
        else:
            return

        self.last_published_deg = list(cmd_deg)
        self.command_count += 1

    def _should_hold(
        self,
        cmd_deg: Sequence[float],
        target_deg: Sequence[float],
        calibrating: bool,
    ) -> bool:
        if calibrating or self.hold_enter_deg <= 0.0:
            self.hold_active = False
            return False
        thr = self.hold_exit_deg if self.hold_active else self.hold_enter_deg
        if self._robot_err(target_deg) >= thr:
            self.hold_active = False
            return False
        if (
            self._max_err(cmd_deg, target_deg) < thr
            and self._robot_err(target_deg) < thr
        ):
            if not self.hold_active:
                self.hold_active = True
                self.get_logger().info('servoj hold: at Isaac pose.')
            return True
        if self.hold_active:
            self.hold_active = False
            self.get_logger().info('Resume servoj.')
        return False

    def _should_publish(self, cmd_deg: Sequence[float]) -> bool:
        if self.min_publish_delta_deg <= 0.0 or self.last_published_deg is None:
            return True
        return (
            self._max_err(cmd_deg, self.last_published_deg)
            >= self.min_publish_delta_deg
        )

    def _update_calibration(
        self,
        cmd_deg: Sequence[float],
        target_deg: Sequence[float],
        now_ns: int,
    ) -> None:
        if self.latest_robot_deg is None:
            self.calibration_settle_ns = None
            return
        if self._max_err(cmd_deg, target_deg) > self.calibration_done_deg:
            self.calibration_settle_ns = None
            return
        if not self._robot_all_within(target_deg, self.calibration_robot_done_deg):
            self.calibration_settle_ns = None
            return
        if self.calibration_settle_ns is None:
            self.calibration_settle_ns = now_ns
            return
        if (now_ns - self.calibration_settle_ns) / 1e9 < self.calibration_settle_sec:
            return
        self.calibration_done = True
        self.calibration_settle_ns = None
        self.get_logger().info('Calibration complete.')

    def _tracking_step(self, robot_err_deg: float) -> float:
        if robot_err_deg <= self.tracking_step_deg:
            return self.tracking_step_deg
        scale = min(robot_err_deg / self.tracking_step_deg, 6.0)
        return min(self.tracking_step_deg * scale, self.tracking_step_max_deg)

    def _robot_all_within(
        self,
        target_deg: Sequence[float],
        threshold_deg: float,
    ) -> bool:
        if self.latest_robot_deg is None:
            return False
        return all(
            abs(r - t) < threshold_deg
            for r, t in zip(self.latest_robot_deg, target_deg)
        )

    def _smooth(self, target_deg: Sequence[float], calibrating: bool) -> list[float]:
        if calibrating or self.smoothing_alpha <= 0.0 or self.smoothing_alpha >= 1.0:
            self.smoothed_target_deg = list(target_deg)
            return list(target_deg)
        if (
            self.smoothed_target_deg is not None
            and self._max_err(target_deg, self.smoothed_target_deg)
            > self.smoothing_reset_delta_deg
        ):
            self.smoothed_target_deg = list(target_deg)
            self.hold_active = False
            return list(target_deg)
        a = min(max(self.smoothing_alpha, 0.01), 1.0)
        if self.smoothed_target_deg is None:
            self.smoothed_target_deg = list(target_deg)
            return list(self.smoothed_target_deg)
        out = [
            a * n + (1.0 - a) * o
            for n, o in zip(target_deg, self.smoothed_target_deg)
        ]
        self.smoothed_target_deg = out
        return list(out)

    def _ramp(self, target_deg: Sequence[float], max_step: float) -> list[float]:
        if self.last_command_deg is None:
            return list(target_deg)
        if max_step <= 0.0:
            self.last_command_deg = list(target_deg)
            return list(target_deg)
        out = []
        for prev, tgt in zip(self.last_command_deg, target_deg):
            d = tgt - prev
            if d > max_step:
                tgt = prev + max_step
            elif d < -max_step:
                tgt = prev - max_step
            out.append(tgt)
        self.last_command_deg = out
        return out

    def _maybe_log(
        self,
        now_ns: int,
        target_deg: Sequence[float],
        cmd_deg: Sequence[float],
        calibrating: bool,
    ) -> None:
        if self.log_period_ns <= 0 or now_ns - self.last_log_ns < self.log_period_ns:
            return
        self.last_log_ns = now_ns
        phase = (
            'hold' if self.hold_active
            else ('calibrate' if calibrating else 'track')
        )
        isaac = self._fmt(self._to_deg(self.latest_positions_rad))
        robot = self._fmt(self.latest_robot_deg) if self.latest_robot_deg else 'n/a'
        inflight = ' busy' if self.move_in_flight else ''
        self.get_logger().info(
            f'[{phase}{inflight}] mode={self.motion_mode} '
            f'in={self.input_count} cmd={self.command_count} '
            f'robot_err={self._robot_err(target_deg):.2f} | '
            f'Isaac {isaac} -> Goal {self._fmt(cmd_deg)} | Robot {robot}'
        )

    def _warn_wait_sync(self) -> None:
        if not self.robot_synced and not self.warned_no_sync:
            self.warned_no_sync = True
            self.get_logger().warn(
                f'Waiting for {self.robot_feedback_topic}…'
            )

    def _watchdog_input(self) -> None:
        if self.input_count > 0 or self.warned_no_input:
            return
        elapsed = (self.get_clock().now().nanoseconds - self.start_ns) / 1e9
        if elapsed < self.input_timeout_sec:
            return
        self.warned_no_input = True
        self.get_logger().error(
            f'No input on {self.input_topic} for {elapsed:.1f}s.'
        )

    def _map_positions(
        self,
        msg: JointState,
        names: Sequence[str],
    ) -> list[float] | None:
        if not msg.position:
            return None
        if msg.name:
            by_name = dict(zip(msg.name, msg.position))
            if any(n not in by_name for n in names):
                return None
            return [by_name[n] for n in names]
        if len(msg.position) < 6:
            return None
        return list(msg.position[:6])

    def _to_deg(self, rad: Sequence[float]) -> list[float]:
        if not self.input_in_radians:
            return list(rad)
        return [math.degrees(v) for v in rad]

    def _clamp(self, deg: Sequence[float]) -> list[float]:
        if not self.enforce_joint_limits:
            return list(deg)
        return [
            min(max(v, lo), hi)
            for v, lo, hi in zip(
                deg, self.min_joint_limits_deg, self.max_joint_limits_deg
            )
        ]

    def _robot_err(self, target_deg: Sequence[float]) -> float:
        if self.latest_robot_deg is None:
            return float('inf')
        return self._max_err(self.latest_robot_deg, target_deg)

    @staticmethod
    def _max_err(a: Sequence[float], b: Sequence[float]) -> float:
        return max(abs(x - y) for x, y in zip(a, b))

    @staticmethod
    def _fmt(values: Sequence[float] | None) -> str:
        if values is None:
            return 'n/a'
        return '[' + ', '.join(f'{v:.2f}' for v in values) + ']'

    def _param_str(self, name: str) -> str:
        return self.get_parameter(name).value

    def _param_str_list(self, name: str) -> list[str]:
        return list(self.get_parameter(name).value)

    def _param_float(self, name: str) -> float:
        return float(self.get_parameter(name).value)

    def _param_float_list(self, name: str) -> list[float]:
        return list(self.get_parameter(name).value)

    def _param_bool(self, name: str) -> bool:
        return bool(self.get_parameter(name).value)

    def _param_int(self, name: str) -> int:
        return int(self.get_parameter(name).value)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DoosanJointStateBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
