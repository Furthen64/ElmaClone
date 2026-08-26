import math
import random

import pygame

from level import clamp, terrain_height_at, terrain_slope_at
from render import draw_bike_visual
from settings import SCREEN_HEIGHT, SCREEN_WIDTH


class Bike:
    def __init__(
        self,
        terrain: list[tuple[float, float]],
        level_length: float,
        start_x: float,
        frame_color: tuple[int, int, int],
        dampening: float,
        cfg: dict,
    ) -> None:
        self.terrain = terrain
        self.level_length = level_length
        self.default_start_x = start_x
        self.frame_color = frame_color
        self.dampening = dampening
        self.cfg = cfg
        self.reset(start_x)

    def reset(self, spawn_x: float | None = None) -> None:
        spawn = self.default_start_x if spawn_x is None else spawn_x
        self.x = clamp(spawn, 0.0, self.level_length)
        self.y = terrain_height_at(self.terrain, self.x) - self.cfg["bike_radius"]
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.angular_velocity = 0.0
        self.on_ground = True
        self.front_compression = 0.0
        self.rear_compression = 0.0
        self.prev_rear_compression = 0.0
        self.prev_front_compression = 0.0
        self.crashed = False
        self.win = False
        self.drive_direction = 1
        self.thrust_mod = 1.0
        self.left_jerk_timer = 0.0
        self.right_jerk_timer = 0.0
        self.prev_left = False
        self.prev_right = False
        self.flip_target = 1.0
        self.flip_visual = 1.0
        self.rear_contact = True
        self.front_contact = True
        self.rear_wheel_x = 0.0
        self.rear_wheel_y = 0.0
        self.front_wheel_x = 0.0
        self.front_wheel_y = 0.0
        self.airborne_frames = 0
        self.gravel_particles: list[dict[str, float | tuple[int, int, int]]] = []

    def apply_setup(self, frame_color: tuple[int, int, int], dampening: float) -> None:
        self.frame_color = frame_color
        self.dampening = dampening

    def _world_from_local(self, off_x: float, off_y: float) -> tuple[float, float]:
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        rx = off_x * cos_a - off_y * sin_a
        ry = off_x * sin_a + off_y * cos_a
        return self.x + rx, self.y + ry

    def _rotated_offset(self, off_x: float, off_y: float) -> tuple[float, float]:
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        return (
            off_x * cos_a - off_y * sin_a,
            off_x * sin_a + off_y * cos_a,
        )

    def _surface_normal_at(self, x: float) -> tuple[float, float]:
        slope = terrain_slope_at(self.terrain, clamp(x, 0.0, self.level_length))
        nx = slope
        ny = -1.0
        length = math.hypot(nx, ny)
        if length <= 1e-6:
            return 0.0, -1.0
        return nx / length, ny / length

    def _apply_airborne_impact(self, contact_x: float) -> None:
        nx, ny = self._surface_normal_at(contact_x)
        normal_speed = self.vx * nx + self.vy * ny
        if normal_speed >= 0.0:
            return
        if normal_speed < -self.cfg["hard_landing_crash_vy"]:
            self.crashed = True
            return

        tangent_x = -ny
        tangent_y = nx
        tangential_speed = self.vx * tangent_x + self.vy * tangent_y
        speed = math.hypot(self.vx, self.vy)
        impact_ratio = clamp(-normal_speed / max(1.0, speed), 0.0, 1.0)
        tangential_speed *= max(0.0, 1.0 - self.cfg["air_impact_tangent_loss"] * impact_ratio)

        self.vx = tangent_x * tangential_speed
        self.vy = tangent_y * tangential_speed
        self.angular_velocity *= max(0.35, 1.0 - self.cfg["air_impact_spin_loss"] * impact_ratio)

    def _gravity_angular_accel(
        self,
        pivot: tuple[float, float] | None = None,
        scale: float = 1.0,
    ) -> float:
        com_local_x = self.cfg["bike_center_of_mass_x"] * self.drive_direction
        com_x, _ = self._world_from_local(com_local_x, self.cfg["bike_center_of_mass_y"])
        if pivot is None:
            lever_x, _ = self._rotated_offset(com_local_x, self.cfg["bike_center_of_mass_y"])
        else:
            lever_x = com_x - pivot[0]
        angular_accel = lever_x * self.cfg["gravity"] * scale / self.cfg["bike_angular_inertia"]
        return clamp(angular_accel, -self.cfg["max_gravity_angular_accel"], self.cfg["max_gravity_angular_accel"])

    def toggle_direction(self) -> None:
        self.drive_direction *= -1
        self.flip_target = float(self.drive_direction)

    def update(
        self,
        dt: float,
        keys: pygame.key.ScancodeWrapper,
        traction_mod: float = 1.0,
        braking_mod: float = 1.0,
        air_control_mod: float = 1.0,
        wind_force_x: float = 0.0,
    ) -> None:
        if self.crashed or self.win:
            return

        drive_contact = self.rear_contact if self.drive_direction > 0 else self.front_contact

        if keys[pygame.K_UP] and drive_contact:
            slope = terrain_slope_at(self.terrain, clamp(self.x, 0.0, self.level_length))
            t_len = math.hypot(1.0, slope)
            thrust = self.acceleration * dt * self.drive_direction * traction_mod * self.thrust_mod
            self.vx += thrust / t_len
            self.vy += thrust * slope / t_len

        brake_delta = 0.0
        if keys[pygame.K_DOWN] and (self.rear_contact or self.front_contact):
            prev_vx = self.vx
            brake = self.cfg["brake_force"] * dt * braking_mod
            if self.vx > 0.0:
                self.vx = max(0.0, self.vx - brake)
            elif self.vx < 0.0:
                self.vx = min(0.0, self.vx + brake)
            brake_delta = prev_vx - self.vx

        if self.on_ground:
            if keys[pygame.K_UP] and drive_contact:
                self.angular_velocity -= self.cfg["weight_transfer_rate"] * dt * self.drive_direction
            if brake_delta != 0.0:
                brake_pitch = brake_delta * self.cfg["brake_pitch_response"]
                if self.rear_contact ^ self.front_contact:
                    brake_pitch *= self.cfg["brake_single_wheel_pitch_bonus"]
                self.angular_velocity += brake_pitch

        left_pressed = keys[pygame.K_LEFT]
        right_pressed = keys[pygame.K_RIGHT]

        if left_pressed and not self.prev_left:
            mod = air_control_mod if not self.on_ground else 1.0
            self.angular_velocity -= self.cfg["left_right_angular_accel"] * self.cfg["jerk_strength"] * mod
            self.left_jerk_timer = 0.0
        elif left_pressed:
            mod = air_control_mod if not self.on_ground else 1.0
            self.left_jerk_timer += dt
            if self.left_jerk_timer >= 1.0:
                self.left_jerk_timer = 0.0
                self.angular_velocity -= self.cfg["left_right_angular_accel"] * self.cfg["jerk_strength"] * mod

        if right_pressed and not self.prev_right:
            mod = air_control_mod if not self.on_ground else 1.0
            self.angular_velocity += self.cfg["left_right_angular_accel"] * self.cfg["jerk_strength"] * mod
            self.right_jerk_timer = 0.0
        elif right_pressed:
            mod = air_control_mod if not self.on_ground else 1.0
            self.right_jerk_timer += dt
            if self.right_jerk_timer >= 1.0:
                self.right_jerk_timer = 0.0
                self.angular_velocity += self.cfg["left_right_angular_accel"] * self.cfg["jerk_strength"] * mod

        self.prev_left = left_pressed
        self.prev_right = right_pressed

        coupling = 100.0 if self.on_ground else 30.0
        self.vx += self.angular_velocity * coupling * dt

        if self.on_ground:
            self.vx *= self.dampening
        self.vx = clamp(self.vx, -self.cfg["max_bike_speed"], self.cfg["max_bike_speed"])

        self.angular_velocity *= clamp(self.dampening - 0.005, 0.96, 0.995)
        self.angle += self.angular_velocity * dt

        if not self.on_ground:
            self.vy += self.cfg["gravity"] * dt
            self.angular_velocity += self._gravity_angular_accel(scale=self.cfg["air_gravity_torque_scale"]) * dt
            self.vx += wind_force_x * dt
            speed = math.hypot(self.vx, self.vy)
            drag = self.cfg["air_drag_coeff"] * speed * dt
            self.vx *= max(0.0, 1.0 - drag)
            self.vy *= max(0.0, 1.0 - drag)
            self.angular_velocity *= self.cfg["air_angular_damping"]

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = clamp(self.x, 0.0, self.level_length)

        prev_rear_comp = self.rear_compression
        prev_front_comp = self.front_compression
        self.front_compression = max(0.0, self.front_compression - self.cfg["suspension_rebound"] * dt)
        self.rear_compression = max(0.0, self.rear_compression - self.cfg["suspension_rebound"] * dt)

        for _ in range(2):
            rear_x, rear_y = self._world_from_local(-self.cfg["wheel_offset_x"], self.cfg["wheel_offset_y"] - self.rear_compression)
            front_x, front_y = self._world_from_local(self.cfg["wheel_offset_x"], self.cfg["wheel_offset_y"] - self.front_compression)
            rear_ground = terrain_height_at(self.terrain, clamp(rear_x, 0.0, self.level_length))
            front_ground = terrain_height_at(self.terrain, clamp(front_x, 0.0, self.level_length))
            rear_penetration = rear_y + self.cfg["bike_radius"] - rear_ground
            front_penetration = front_y + self.cfg["bike_radius"] - front_ground

            if rear_penetration > 0.0:
                if self.airborne_frames >= self.cfg["min_airborne_frames"]:
                    self._apply_airborne_impact(rear_x)
                rear_absorb = min(rear_penetration, self.cfg["suspension_travel"] - self.rear_compression)
                self.rear_compression += max(0.0, rear_absorb)
                rear_penetration -= max(0.0, rear_absorb)
                if rear_penetration > 0.0:
                    self.y -= rear_penetration
                    if self.vy > 0.0:
                        self.vy = 0.0

            if front_penetration > 0.0:
                if self.airborne_frames >= self.cfg["min_airborne_frames"]:
                    self._apply_airborne_impact(front_x)
                front_absorb = min(front_penetration, self.cfg["suspension_travel"] - self.front_compression)
                self.front_compression += max(0.0, front_absorb)
                front_penetration -= max(0.0, front_absorb)
                if front_penetration > 0.0:
                    self.y -= front_penetration
                    if self.vy > 0.0:
                        self.vy = 0.0

        if dt > 0.0 and (self.rear_compression > 0.0 or self.front_compression > 0.0):
            avg_comp = (self.rear_compression + self.front_compression) * 0.5
            comp_delta = ((self.rear_compression - prev_rear_comp) + (self.front_compression - prev_front_comp)) * 0.5
            comp_vel = clamp(comp_delta / dt, -200.0, 200.0)
            spring_up = self.cfg["suspension_spring"] * avg_comp
            damp = self.cfg["suspension_damper"] * comp_vel
            impulse = clamp((spring_up + damp) * dt, 0.0, 12.0)
            self.vy -= impulse

        rear_x, rear_y = self._world_from_local(-self.cfg["wheel_offset_x"], self.cfg["wheel_offset_y"] - self.rear_compression)
        front_x, front_y = self._world_from_local(self.cfg["wheel_offset_x"], self.cfg["wheel_offset_y"] - self.front_compression)
        self.rear_wheel_x = rear_x
        self.rear_wheel_y = rear_y
        self.front_wheel_x = front_x
        self.front_wheel_y = front_y
        rear_ground = terrain_height_at(self.terrain, clamp(rear_x, 0.0, self.level_length))
        front_ground = terrain_height_at(self.terrain, clamp(front_x, 0.0, self.level_length))
        rear_contact = rear_y + self.cfg["bike_radius"] >= rear_ground - 2.0
        front_contact = front_y + self.cfg["bike_radius"] >= front_ground - 2.0
        self.rear_contact = rear_contact
        self.front_contact = front_contact
        self.on_ground = rear_contact or front_contact
        if self.on_ground:
            self.airborne_frames = 0
        else:
            self.airborne_frames += 1

        if self.on_ground:
            self.angular_velocity *= clamp(self.dampening - 0.08, 0.82, 0.95)
            if rear_contact and front_contact:
                target_angle = math.atan2(front_ground - rear_ground, max(1.0, front_x - rear_x))
                ground_slope = (front_ground - rear_ground) / max(1.0, front_x - rear_x)
                support_pivot = ((rear_x + front_x) * 0.5, (rear_ground + front_ground) * 0.5)
            elif rear_contact:
                sample = 12.0
                y1 = terrain_height_at(self.terrain, clamp(rear_x - sample, 0.0, self.level_length))
                y2 = terrain_height_at(self.terrain, clamp(rear_x + sample, 0.0, self.level_length))
                target_angle = math.atan2(y2 - y1, 2.0 * sample)
                ground_slope = terrain_slope_at(self.terrain, rear_x)
                support_pivot = (rear_x, rear_ground)
            else:
                sample = 12.0
                y1 = terrain_height_at(self.terrain, clamp(front_x - sample, 0.0, self.level_length))
                y2 = terrain_height_at(self.terrain, clamp(front_x + sample, 0.0, self.level_length))
                target_angle = math.atan2(y2 - y1, 2.0 * sample)
                ground_slope = terrain_slope_at(self.terrain, front_x)
                support_pivot = (front_x, front_ground)

            gravity_scale = self.cfg["ground_gravity_torque_scale"]
            if rear_contact ^ front_contact:
                gravity_scale *= self.cfg["single_wheel_gravity_bonus"]
            self.angular_velocity += self._gravity_angular_accel(support_pivot, gravity_scale) * dt

            if self.cfg["autobalancing"]:
                balance_scale = clamp(abs(self.vx) / 280.0, 0.15, 1.0)
                self.angular_velocity += (target_angle - self.angle) * self.cfg["auto_balance_strength"] * balance_scale * dt
                self.angular_velocity *= self.cfg["auto_balance_damping"]

            ramp_lift_vy = clamp(self.vx * ground_slope, -self.cfg["max_ramp_lift_vy"], self.cfg["max_ramp_lift_vy"])
            lift_blend = clamp(dt * self.cfg["ramp_launch_response"], 0.0, 1.0)
            self.vy += (ramp_lift_vy - self.vy) * lift_blend

        if keys[pygame.K_UP] and drive_contact:
            drive_x, drive_y = (rear_x, rear_y) if self.drive_direction > 0 else (front_x, front_y)
            spawn_count = max(1, int(self.cfg["gravel_spawn_rate"] * dt))
            for _ in range(spawn_count):
                self.gravel_particles.append(
                    {
                        "x": drive_x - self.drive_direction * random.uniform(6.0, 14.0),
                        "y": drive_y + self.cfg["bike_radius"] - random.uniform(2.0, 8.0),
                        "vx": -self.drive_direction * random.uniform(140.0, 260.0) + self.vx * 0.2,
                        "vy": -random.uniform(120.0, 230.0),
                        "life": random.uniform(0.22, 0.38),
                        "size": random.uniform(1.5, 3.0),
                        "shade": random.choice(((116, 80, 52), (138, 96, 60), (170, 120, 74))),
                    }
                )

        next_particles: list[dict[str, float | tuple[int, int, int]]] = []
        for particle in self.gravel_particles:
            life = float(particle["life"]) - dt
            if life <= 0.0:
                continue
            particle["life"] = life
            particle["x"] = float(particle["x"]) + float(particle["vx"]) * dt
            particle["y"] = float(particle["y"]) + float(particle["vy"]) * dt
            particle["vy"] = float(particle["vy"]) + self.cfg["gravity"] * 0.45 * dt
            particle["vx"] = float(particle["vx"]) * 0.985
            ground_y = terrain_height_at(self.terrain, clamp(float(particle["x"]), 0.0, self.level_length))
            if float(particle["y"]) >= ground_y:
                particle["y"] = ground_y
                particle["vy"] = float(particle["vy"]) * -0.18
                particle["vx"] = float(particle["vx"]) * 0.6
            next_particles.append(particle)
        self.gravel_particles = next_particles

        flip_blend = clamp(dt * 9.0, 0.0, 1.0)
        self.flip_visual += (self.flip_target - self.flip_visual) * flip_blend

        head_x, head_y = self._world_from_local(self.cfg["head_offset_x"] * self.drive_direction, self.cfg["head_offset_y"])
        head_ground = terrain_height_at(self.terrain, clamp(head_x, 0.0, self.level_length))
        if head_y >= head_ground:
            self.crashed = True

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        for particle in self.gravel_particles:
            px = int(float(particle["x"]) - camera_x)
            py = int(float(particle["y"]))
            if -8 <= px <= SCREEN_WIDTH + 8 and -8 <= py <= SCREEN_HEIGHT + 8:
                pygame.draw.circle(
                    screen,
                    particle["shade"],
                    (px, py),
                    max(1, int(float(particle["size"]))),
                )
        center = (int(self.x - camera_x), int(self.y))
        draw_bike_visual(
            screen,
            center,
            self.angle,
            self.frame_color,
            front_compression=self.front_compression,
            rear_compression=self.rear_compression,
            scale=1.0,
            facing=self.flip_visual,
        )
