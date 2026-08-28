import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS = {
    # Saved tuning values
    "acceleration": 1100.0,
    "thrust_mod": 1.0,

    # Physics
    "gravity": 1800.0,
    "bike_radius": 20,
    "wheel_offset_x": 34.0,
    "wheel_offset_y": 18.0,
    "head_offset_x": 8.0,
    "head_offset_y": -56.0,
    "suspension_travel": 16.0,
    "suspension_rebound": 90.0,
    "left_right_angular_accel": 5.5 * 60 * 0.05,
    "jerk_strength": 0.3,
    "autobalancing": False,
    "auto_balance_strength": 12.0,
    "auto_balance_damping": 0.92,
    "brake_force": 200.0,
    "brake_pitch_response": 0.015,
    "brake_single_wheel_pitch_bonus": 4.0,
    "max_bike_speed": 760.0,
    "ramp_launch_response": 22.0,
    "max_ramp_lift_vy": 700.0,
    "air_impact_tangent_loss": 0.28,
    "air_impact_spin_loss": 0.5,
    "wall_bounce_restitution": 0.55,
    "wall_bounce_tangent_keep": 0.25,
    "suspension_spring": 400.0,
    "suspension_damper": 20.0,
    "weight_transfer_rate": 1.8,
    "air_drag_coeff": 0.00018,
    "air_angular_damping": 0.9988,
    "bike_center_of_mass_x": 2.0,
    "bike_center_of_mass_y": -28.0,
    "bike_angular_inertia": 3200.0,
    "air_gravity_torque_scale": 0.35,
    "ground_gravity_torque_scale": 1.2,
    "single_wheel_gravity_bonus": 1.25,
    "max_gravity_angular_accel": 16.0,
    "hard_landing_crash_vy": 900.0,
    "min_airborne_frames": 3,
    "gravel_spawn_rate": 120.0,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for key, value in DEFAULTS.items():
            if key not in data:
                data[key] = value
        return data
    save_config(DEFAULTS)
    return DEFAULTS.copy()


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, indent=4), encoding="utf-8")
