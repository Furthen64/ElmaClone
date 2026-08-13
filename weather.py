import math
import random

import pygame

from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    DAY_CYCLE_DURATION,
    WEATHER_CHANGE_INTERVAL,
    WIND_FORCE_STRENGTH,
    FOG_VISIBILITY_RADIUS,
    HEADLIGHT_RANGE,
    NIGHT_DARKNESS_ALPHA,
    STAR_COUNT,
    RAIN_PARTICLE_COUNT,
    SNOW_PARTICLE_COUNT,
    TRACTION_MODIFIERS,
    BRAKING_MODIFIERS,
    AIR_CONTROL_MODIFIERS,
)


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0))) if edge1 != edge0 else 0.0
    return t * t * (3 - 2 * t)


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life


class WeatherSystem:
    """Manages day/night cycle and weather conditions."""

    CONDITIONS = ["clear", "rain", "fog", "wind", "snow"]

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self.condition: str = "clear"
        self._change_timer: float = random.uniform(20.0, 60.0)
        self.particles: list[_Particle] = []
        self.wind_x: float = 0.0
        self.wind_target: float = 0.0
        self._star_positions: list[tuple[float, float]] = [
            (random.uniform(0, SCREEN_WIDTH), random.uniform(0, SCREEN_HEIGHT * 0.6))
            for _ in range(STAR_COUNT)
        ]

    # --- Time-of-day helpers ---

    @property
    def day_phase(self) -> float:
        return (self.elapsed % DAY_CYCLE_DURATION) / DAY_CYCLE_DURATION

    @property
    def darkness(self) -> float:
        phase = self.day_phase
        if 0.2 <= phase <= 0.8:
            return 0.0
        if phase < 0.2:
            t = phase / 0.2
            return _smoothstep(1.0, 0.0, t)
        else:
            t = (phase - 0.8) / 0.2
            return _smoothstep(0.0, 1.0, t)

    @property
    def is_night(self) -> bool:
        return self.darkness > 0.3

    @property
    def sun_y(self) -> float:
        phase = self.day_phase
        peak = 0.5
        dist = abs(phase - peak) * 2.0
        return SCREEN_HEIGHT * 0.1 + (1.0 - max(0.0, 1.0 - dist)) * SCREEN_HEIGHT * 0.45

    # --- Weather transitions ---

    def _pick_condition(self) -> str:
        weights = [0.40, 0.25, 0.15, 0.10, 0.10]
        r = random.random()
        cumulative = 0.0
        for cond, w in zip(self.CONDITIONS, weights):
            cumulative += w
            if r < cumulative:
                return cond
        return "clear"

    # --- Update ---

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self._change_timer -= dt

        if self._change_timer <= 0:
            self.condition = self._pick_condition()
            self._change_timer = random.uniform(
                WEATHER_CHANGE_INTERVAL * 0.7,
                WEATHER_CHANGE_INTERVAL * 1.3,
            )
            self.wind_target = random.uniform(-WIND_FORCE_STRENGTH, WIND_FORCE_STRENGTH)

        self.wind_x += (self.wind_target - self.wind_x) * min(dt * 2.0, 1.0)
        self._update_particles(dt)

    def _spawn_weather_particle(self, cam_x: float) -> None:
        left = cam_x - SCREEN_WIDTH // 2 - 50
        right = cam_x + SCREEN_WIDTH // 2 + 50

        if self.condition == "rain":
            count = RAIN_PARTICLE_COUNT
            while len([p for p in self.particles]) < count:
                self.particles.append(_Particle(
                    random.uniform(left, right),
                    random.uniform(-50, -10),
                    random.uniform(-40, 40),
                    random.uniform(600, 900),
                    random.uniform(0.5, 1.5),
                ))
        elif self.condition == "snow":
            count = SNOW_PARTICLE_COUNT
            while len([p for p in self.particles]) < count:
                self.particles.append(_Particle(
                    random.uniform(left, right),
                    random.uniform(-50, -10),
                    random.uniform(-30, 30),
                    random.uniform(60, 150),
                    random.uniform(1.0, 3.0),
                ))

    def _update_particles(self, dt: float) -> None:
        cam_x = 0.0
        if hasattr(self, "_cam_x"):
            cam_x = self._cam_x

        self._spawn_weather_particle(cam_x)

        surviving: list[_Particle] = []
        for p in self.particles:
            p.x += p.vx * dt + (self.wind_x if self.condition in ("wind", "rain", "snow") else 0.0) * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0 and p.y < SCREEN_HEIGHT + 50:
                surviving.append(p)
        self.particles = surviving

    # --- Physics modifiers ---

    def get_traction_modifier(self) -> float:
        return TRACTION_MODIFIERS.get(self.condition, 1.0)

    def get_braking_modifier(self) -> float:
        return BRAKING_MODIFIERS.get(self.condition, 1.0)

    def get_air_control_modifier(self) -> float:
        return AIR_CONTROL_MODIFIERS.get(self.condition, 1.0)

    def get_wind_force(self) -> tuple[float, float]:
        return (self.wind_x, 0.0)

    # --- Rendering helpers (called from render.py) ---

    def set_camera_x(self, cam_x: float) -> None:
        self._cam_x = cam_x

    def draw_particles(self, surface: pygame.Surface) -> None:
        if not self.particles:
            return
        color = (160, 180, 220) if self.condition == "rain" else (230, 235, 245)
        radius = 1 if self.condition == "rain" else 3
        for p in self.particles:
            sx = int(p.x) % (SCREEN_WIDTH + 100) - 50
            sy = int(p.y)
            if 0 <= sx < SCREEN_WIDTH and 0 <= sy < SCREEN_HEIGHT:
                pygame.draw.circle(surface, color, (sx, sy), radius)

    def draw_stars(self, surface: pygame.Surface, alpha: float) -> None:
        if alpha <= 0:
            return
        star_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        a = int(alpha * 255)
        for sx, sy in self._star_positions:
            twinkle = 0.7 + 0.3 * math.sin(self.elapsed * 3.0 + sx)
            ca = int(a * twinkle)
            pygame.draw.circle(star_surf, (255, 255, 240, ca), (int(sx), int(sy)), 1)
        surface.blit(star_surf, (0, 0))

    def draw_night_overlay(self, surface: pygame.Surface) -> None:
        alpha = int(self.darkness * NIGHT_DARKNESS_ALPHA)
        if alpha <= 0:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 40, alpha))
        surface.blit(overlay, (0, 0))

    def draw_fog_overlay(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        if self.condition != "fog":
            return
        fog_color = (180, 190, 200, 160)
        for radius_step in range(FOG_VISIBILITY_RADIUS, SCREEN_WIDTH // 2 + 100, 60):
            a = int(160 * (1.0 - FOG_VISIBILITY_RADIUS / radius_step))
            if a > 200:
                a = 200
            ring = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            pygame.draw.circle(ring, (*fog_color[:3], min(a, 200)), center, radius_step, max(radius_step - 40, 1))
            surface.blit(ring, (0, 0))

    def draw_headlight(self, surface: pygame.Surface, bike_screen_x: float, bike_screen_y: float, facing_right: bool) -> None:
        if not self.is_night:
            return
        alpha = int(self.darkness * 140)
        if alpha < 10:
            return
        light_surf = pygame.Surface((HEADLIGHT_RANGE * 2, HEADLIGHT_RANGE), pygame.SRCALPHA)
        cx = HEADLIGHT_RANGE
        cy = HEADLIGHT_RANGE // 2
        for r in range(HEADLIGHT_RANGE, 0, -4):
            a = int(alpha * (r / HEADLIGHT_RANGE) ** 2)
            if a < 2:
                break
            pygame.draw.circle(light_surf, (255, 245, 200, a), (cx, cy), r)
        sx = int(bike_screen_x - HEADLIGHT_RANGE) + (HEADLIGHT_RANGE if facing_right else -HEADLIGHT_RANGE)
        sy = int(bike_screen_y - HEADLIGHT_RANGE // 2)
        if not facing_right:
            light_surf = pygame.transform.flip(light_surf, True, False)
        surface.blit(light_surf, (sx, sy))

    def get_sky_colors(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        phase = self.day_phase
        night_top = (15, 20, 60)
        night_bot = (25, 30, 70)
        day_top = (100, 170, 235)
        day_bot = (180, 215, 245)
        sunset_top = (90, 60, 120)
        sunset_bot = (235, 140, 80)

        darkness = self.darkness
        if 0.2 <= phase < 0.3:
            t = (phase - 0.2) / 0.1
            top = tuple(int(night_top[i] * (1 - t) + sunset_top[i] * t) for i in range(3))
            bot = tuple(int(night_bot[i] * (1 - t) + sunset_bot[i] * t) for i in range(3))
        elif 0.3 <= phase < 0.5:
            t = (phase - 0.3) / 0.2
            top = tuple(int(sunset_top[i] * (1 - t) + day_top[i] * t) for i in range(3))
            bot = tuple(int(sunset_bot[i] * (1 - t) + day_bot[i] * t) for i in range(3))
        elif 0.5 <= phase < 0.7:
            top = day_top
            bot = day_bot
        elif 0.7 <= phase < 0.8:
            t = (phase - 0.7) / 0.1
            top = tuple(int(day_top[i] * (1 - t) + sunset_top[i] * t) for i in range(3))
            bot = tuple(int(day_bot[i] * (1 - t) + sunset_bot[i] * t) for i in range(3))
        elif 0.8 <= phase < 0.9:
            t = (phase - 0.8) / 0.1
            top = tuple(int(sunset_top[i] * (1 - t) + night_top[i] * t) for i in range(3))
            bot = tuple(int(sunset_bot[i] * (1 - t) + night_bot[i] * t) for i in range(3))
        else:
            top = night_top
            bot = night_bot

        return top, bot

    def get_condition_label(self) -> str:
        labels = {"clear": "Clear", "rain": "Rain", "fog": "Fog", "wind": "Wind", "snow": "Snow"}
        return labels.get(self.condition, self.condition)
