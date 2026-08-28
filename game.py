import pygame

from bike import Bike
from config import load_config, save_config
from level import clamp, load_level_entry
from render import (
    draw_collectibles,
    draw_design_screen,
    draw_level_complete_screen,
    draw_menu_screen,
    draw_sky,
    draw_terrain,
    draw_trees,
    draw_weather_overlays,
    format_race_time,
)
from settings import (
    BIKE_COLOR_OPTIONS,
    BIKE_RADIUS,
    COIN_RADIUS,
    CRASH_RESPAWN_DELAY,
    DAMPENING_OPTIONS,
    FPS,
    LEVEL_FILES,
    MAX_RACE_TIME_SECONDS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WEATHER_ENABLED,
)
from weather import WeatherSystem


def main() -> int:
    pygame.init()
    pygame.display.set_caption("ElmaClone - v1.1")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 56, bold=True)
    font = pygame.font.SysFont("consolas", 24)
    small_font = pygame.font.SysFont("consolas", 20)

    selected_level_index = 0
    selected_level_name, level = load_level_entry(selected_level_index)
    terrain = level["terrain"]
    finish_x = level["finish_x"]
    coins = level["coins"]
    checkpoints = level["checkpoints"]
    selected_color_index = 0
    selected_dampening_index = 1

    game_config = load_config()
    bike = Bike(
        terrain,
        finish_x,
        level["start_x"],
        BIKE_COLOR_OPTIONS[selected_color_index][1],
        DAMPENING_OPTIONS[selected_dampening_index][1],
        game_config,
    )
    bike.acceleration = float(game_config["acceleration"])
    bike.thrust_mod = float(game_config["thrust_mod"])
    checkpoint_spawn_x = level["start_x"]
    crash_timer = 0.0
    weather = WeatherSystem() if WEATHER_ENABLED else None
    race_start_ms = pygame.time.get_ticks()
    finish_elapsed_ms: int | None = None
    death_count = 0
    completed_time_ms: int | None = None
    completed_apples = 0
    completed_total_apples = 0
    completed_deaths = 0
    game_state = "menu"
    debug_mode = False

    def apply_selected_setup() -> None:
        bike.apply_setup(
            BIKE_COLOR_OPTIONS[selected_color_index][1],
            DAMPENING_OPTIONS[selected_dampening_index][1],
        )

    def reset_level_state() -> None:
        nonlocal checkpoint_spawn_x, crash_timer, race_start_ms, finish_elapsed_ms, weather, death_count
        checkpoint_spawn_x = level["start_x"]
        for coin in coins:
            coin["collected"] = False
        for checkpoint in checkpoints:
            checkpoint["active"] = False
        bike.reset(level["start_x"])
        crash_timer = 0.0
        race_start_ms = pygame.time.get_ticks()
        finish_elapsed_ms = None
        death_count = 0
        if WEATHER_ENABLED:
            weather = WeatherSystem()

    def switch_level(new_index: int) -> None:
        nonlocal selected_level_index, selected_level_name, level, terrain, finish_x, coins, checkpoints, bike
        selected_level_index = new_index % len(LEVEL_FILES)
        selected_level_name, level = load_level_entry(selected_level_index)
        terrain = level["terrain"]
        finish_x = level["finish_x"]
        coins = level["coins"]
        checkpoints = level["checkpoints"]
        bike = Bike(
            terrain,
            finish_x,
            level["start_x"],
            BIKE_COLOR_OPTIONS[selected_color_index][1],
            DAMPENING_OPTIONS[selected_dampening_index][1],
            game_config,
        )
        bike.acceleration = float(game_config["acceleration"])
        bike.thrust_mod = float(game_config["thrust_mod"])
        reset_level_state()

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_config["acceleration"] = bike.acceleration
                game_config["thrust_mod"] = bike.thrust_mod
                save_config(game_config)
                running = False
            elif event.type == pygame.KEYDOWN:
                if pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT) and event.key == pygame.K_d:
                    debug_mode = not debug_mode
                elif game_state == "menu":
                    if event.key == pygame.K_RETURN:
                        apply_selected_setup()
                        reset_level_state()
                        game_state = "play"
                    elif event.key == pygame.K_l:
                        switch_level(selected_level_index + 1)
                    elif event.key == pygame.K_d:
                        game_state = "design"
                    elif event.key == pygame.K_ESCAPE:
                        game_config["acceleration"] = bike.acceleration
                        game_config["thrust_mod"] = bike.thrust_mod
                        save_config(game_config)
                        running = False
                elif game_state == "design":
                    if event.key == pygame.K_LEFT:
                        selected_color_index = (selected_color_index - 1) % len(BIKE_COLOR_OPTIONS)
                        apply_selected_setup()
                    elif event.key == pygame.K_RIGHT:
                        selected_color_index = (selected_color_index + 1) % len(BIKE_COLOR_OPTIONS)
                        apply_selected_setup()
                    elif event.key == pygame.K_UP:
                        selected_dampening_index = (selected_dampening_index - 1) % len(DAMPENING_OPTIONS)
                        apply_selected_setup()
                    elif event.key == pygame.K_DOWN:
                        selected_dampening_index = (selected_dampening_index + 1) % len(DAMPENING_OPTIONS)
                        apply_selected_setup()
                    elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        game_state = "menu"
                elif game_state == "level_complete":
                    if event.key == pygame.K_RETURN:
                        switch_level(selected_level_index + 1)
                        game_state = "play"
                    elif event.key == pygame.K_ESCAPE:
                        game_state = "menu"
                elif game_state == "play":
                    if debug_mode and event.key == pygame.K_EQUALS:
                        bike.acceleration += 50.0
                        game_config["acceleration"] = bike.acceleration
                        save_config(game_config)
                    elif debug_mode and event.key == pygame.K_MINUS:
                        bike.acceleration = max(100.0, bike.acceleration - 50.0)
                        game_config["acceleration"] = bike.acceleration
                        save_config(game_config)
                    elif debug_mode and event.key == pygame.K_j:
                        bike.thrust_mod += 0.1
                        game_config["thrust_mod"] = bike.thrust_mod
                        save_config(game_config)
                    elif debug_mode and event.key == pygame.K_k:
                        bike.thrust_mod = max(0.1, bike.thrust_mod - 0.1)
                        game_config["thrust_mod"] = bike.thrust_mod
                        save_config(game_config)
                    elif event.key == pygame.K_r:
                        reset_level_state()
                    elif event.key == pygame.K_SPACE:
                        bike.toggle_direction()
                    elif event.key == pygame.K_ESCAPE:
                        game_state = "menu"
                        bike.reset(level["start_x"])
                        crash_timer = 0.0

        if game_state == "play":
            keys = pygame.key.get_pressed()

            traction_mod = weather.get_traction_modifier() if weather else 1.0
            braking_mod = weather.get_braking_modifier() if weather else 1.0
            air_control_mod = weather.get_air_control_modifier() if weather else 1.0
            wind_fx, _ = weather.get_wind_force() if weather else (0.0, 0.0)
            bike.update(dt, keys, traction_mod, braking_mod, air_control_mod, wind_fx)

            if weather:
                weather.update(dt)

            if bike.crashed:
                if crash_timer == 0.0:
                    death_count += 1
                crash_timer += dt
                if crash_timer >= CRASH_RESPAWN_DELAY:
                    bike.reset(checkpoint_spawn_x)
                    crash_timer = 0.0
            else:
                crash_timer = 0.0

                for checkpoint in checkpoints:
                    if not checkpoint["active"] and bike.x >= checkpoint["x"]:
                        checkpoint["active"] = True
                        checkpoint_spawn_x = checkpoint["x"]

                collect_radius_sq = (BIKE_RADIUS + COIN_RADIUS) ** 2
                for coin in coins:
                    if coin["collected"]:
                        continue
                    for wx, wy in ((bike.rear_wheel_x, bike.rear_wheel_y),
                                   (bike.front_wheel_x, bike.front_wheel_y)):
                        dx = wx - coin["x"]
                        dy = wy - coin["y"]
                        if dx * dx + dy * dy <= collect_radius_sq:
                            coin["collected"] = True
                            break

            collected = sum(1 for coin in coins if coin["collected"])
            total_coins = len(coins)

            if not bike.crashed and bike.x >= finish_x - 30 and collected == total_coins:
                if not bike.win:
                    finish_elapsed_ms = pygame.time.get_ticks() - race_start_ms
                    completed_time_ms = finish_elapsed_ms
                    completed_apples = collected
                    completed_total_apples = total_coins
                    completed_deaths = death_count
                    bike.win = True
                    game_state = "level_complete"

            camera_x = clamp(bike.x - SCREEN_WIDTH * 0.35, 0.0, max(finish_x - SCREEN_WIDTH, 0.0))

            if weather:
                sky_top, sky_bot = weather.get_sky_colors()
            else:
                sky_top, sky_bot = None, None
            draw_sky(screen, pygame.time.get_ticks() / 1000.0, sky_top, sky_bot)
            draw_terrain(screen, terrain, camera_x)
            draw_trees(screen, terrain, camera_x)
            draw_collectibles(screen, coins, checkpoints, terrain, camera_x)
            bike.draw(screen, camera_x)

            if weather:
                facing_right = bike.drive_direction > 0
                draw_weather_overlays(
                    screen, weather, camera_x, 0.0,
                    bike.x - camera_x, bike.y, facing_right,
                )

            finish_screen_x = int(finish_x - camera_x)
            pygame.draw.line(screen, (255, 255, 255), (finish_screen_x, 0), (finish_screen_x, SCREEN_HEIGHT), 3)

            speed_text = font.render(f"Speed: {abs(int(bike.vx))}", True, (14, 26, 50))
            coins_text = font.render(f"Apples: {collected}/{total_coins}", True, (14, 26, 50))
            setup_text = small_font.render(
                f"Bike: {BIKE_COLOR_OPTIONS[selected_color_index][0]} | Dampening: {DAMPENING_OPTIONS[selected_dampening_index][0]}",
                True,
                (20, 20, 30),
            )
            weather_text = small_font.render(f"Weather: {weather.get_condition_label()}", True, (20, 20, 30)) if weather else None
            screen.blit(speed_text, (20, 16))
            screen.blit(coins_text, (20, 48))
            screen.blit(setup_text, (20, 80))
            if weather_text:
                screen.blit(weather_text, (20, 100))

            elapsed_ms = finish_elapsed_ms
            if elapsed_ms is None:
                elapsed_ms = pygame.time.get_ticks() - race_start_ms
            elapsed_ms = min(elapsed_ms, MAX_RACE_TIME_SECONDS * 1000)
            timer_text = font.render(format_race_time(elapsed_ms), True, (20, 45, 90))
            timer_bg = pygame.Surface((timer_text.get_width() + 22, timer_text.get_height() + 10), pygame.SRCALPHA)
            timer_bg.fill((225, 238, 255, 120))
            timer_x = SCREEN_WIDTH - timer_bg.get_width() - 20
            timer_y = 18
            screen.blit(timer_bg, (timer_x, timer_y))
            screen.blit(timer_text, (timer_x + 11, timer_y + 5))

            controls = small_font.render(
                "UP accelerate(traction)  LEFT/RIGHT rotate  SPACE flip bike  R restart  ESC menu",
                True,
                (20, 20, 30),
            )
            screen.blit(controls, (20, 108))

            if debug_mode:
                debug_lines = [
                    f"Accel: {bike.acceleration:.0f}",
                    f"Thrust mod: {bike.thrust_mod:.1f}",
                    f"Pos: ({bike.x:.1f}, {bike.y:.1f})",
                    f"Vel: ({bike.vx:.1f}, {bike.vy:.1f})",
                    f"Angle: {(bike.angle * 57.2958):.1f}",
                    f"AngVel: {bike.angular_velocity:.3f}",
                    f"Rear wheel: ({bike.rear_wheel_x:.1f}, {bike.rear_wheel_y:.1f})",
                    f"Front wheel: ({bike.front_wheel_x:.1f}, {bike.front_wheel_y:.1f})",
                    f"Ground: {bike.on_ground} | Rear: {bike.rear_contact} | Front: {bike.front_contact}",
                    f"Suspension R:{bike.rear_compression:.1f} F:{bike.front_compression:.1f}",
                    f"Crash: {bike.crash_reason or 'none'}",
                ]
                for i, line in enumerate(debug_lines):
                    t = small_font.render(line, True, (255, 255, 0))
                    screen.blit(t, (SCREEN_WIDTH - t.get_width() - 20, SCREEN_HEIGHT - (len(debug_lines) + i) * 22))

                # Draw wheel hitboxes
                for wx, wy in ((bike.rear_wheel_x, bike.rear_wheel_y),
                               (bike.front_wheel_x, bike.front_wheel_y)):
                    sx = int(wx - camera_x)
                    sy = int(wy)
                    pygame.draw.circle(screen, (255, 255, 0), (sx, sy), BIKE_RADIUS + COIN_RADIUS, 1)
                    pygame.draw.circle(screen, (255, 0, 0), (sx, sy), BIKE_RADIUS, 2)

            if bike.crashed:
                crash = font.render("CRASHED - Respawning from checkpoint...", True, (200, 20, 20))
                screen.blit(crash, (SCREEN_WIDTH // 2 - crash.get_width() // 2, 140))
                if bike.crash_reason:
                    cause = small_font.render(f"Cause: {bike.crash_reason}", True, (220, 130, 130))
                    screen.blit(cause, (SCREEN_WIDTH // 2 - cause.get_width() // 2, 170))
            elif bike.x >= finish_x - 30 and collected < total_coins:
                need = font.render("Collect all coins before finishing", True, (120, 70, 0))
                screen.blit(need, (SCREEN_WIDTH // 2 - need.get_width() // 2, 140))
        elif game_state == "design":
            draw_design_screen(
                screen,
                title_font,
                small_font,
                BIKE_COLOR_OPTIONS[selected_color_index][0],
                BIKE_COLOR_OPTIONS[selected_color_index][1],
                DAMPENING_OPTIONS[selected_dampening_index][0],
            )
        elif game_state == "level_complete":
            draw_level_complete_screen(
                screen,
                title_font,
                font,
                selected_level_name,
                max(0, completed_time_ms or 0),
                completed_apples,
                completed_total_apples,
                completed_deaths,
            )
        else:
            draw_menu_screen(screen, title_font, small_font, selected_level_name)

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
