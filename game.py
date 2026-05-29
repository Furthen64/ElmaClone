import pygame

from bike import Bike
from level import clamp, load_level_entry
from render import (
    draw_collectibles,
    draw_design_screen,
    draw_menu_screen,
    draw_sky,
    draw_terrain,
    draw_trees,
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
)


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

    bike = Bike(
        terrain,
        finish_x,
        level["start_x"],
        BIKE_COLOR_OPTIONS[selected_color_index][1],
        DAMPENING_OPTIONS[selected_dampening_index][1],
    )
    checkpoint_spawn_x = level["start_x"]
    crash_timer = 0.0
    race_start_ms = pygame.time.get_ticks()
    finish_elapsed_ms: int | None = None
    game_state = "menu"

    def apply_selected_setup() -> None:
        bike.apply_setup(
            BIKE_COLOR_OPTIONS[selected_color_index][1],
            DAMPENING_OPTIONS[selected_dampening_index][1],
        )

    def reset_level_state() -> None:
        nonlocal checkpoint_spawn_x, crash_timer, race_start_ms, finish_elapsed_ms
        checkpoint_spawn_x = level["start_x"]
        for coin in coins:
            coin["collected"] = False
        for checkpoint in checkpoints:
            checkpoint["active"] = False
        bike.reset(level["start_x"])
        crash_timer = 0.0
        race_start_ms = pygame.time.get_ticks()
        finish_elapsed_ms = None

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game_state == "menu":
                    if event.key == pygame.K_RETURN:
                        apply_selected_setup()
                        reset_level_state()
                        game_state = "play"
                    elif event.key == pygame.K_l:
                        selected_level_index = (selected_level_index + 1) % len(LEVEL_FILES)
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
                        )
                        checkpoint_spawn_x = level["start_x"]
                        crash_timer = 0.0
                        race_start_ms = pygame.time.get_ticks()
                        finish_elapsed_ms = None
                    elif event.key == pygame.K_d:
                        game_state = "design"
                    elif event.key == pygame.K_ESCAPE:
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
                elif game_state == "play":
                    if event.key == pygame.K_r:
                        reset_level_state()
                    elif event.key == pygame.K_SPACE:
                        bike.toggle_direction()
                    elif event.key == pygame.K_ESCAPE:
                        game_state = "menu"
                        bike.reset(level["start_x"])
                        crash_timer = 0.0

        if game_state == "play":
            keys = pygame.key.get_pressed()
            bike.update(dt, keys)

            if bike.crashed:
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

                for coin in coins:
                    if coin["collected"]:
                        continue
                    dx = bike.x - coin["x"]
                    dy = bike.y - coin["y"]
                    if dx * dx + dy * dy <= (BIKE_RADIUS + COIN_RADIUS) ** 2:
                        coin["collected"] = True

            collected = sum(1 for coin in coins if coin["collected"])
            total_coins = len(coins)

            if not bike.crashed and bike.x >= finish_x - 30 and collected == total_coins:
                if not bike.win:
                    finish_elapsed_ms = pygame.time.get_ticks() - race_start_ms
                bike.win = True

            camera_x = clamp(bike.x - SCREEN_WIDTH * 0.35, 0.0, max(finish_x - SCREEN_WIDTH, 0.0))

            draw_sky(screen, pygame.time.get_ticks() / 1000.0)
            draw_terrain(screen, terrain, camera_x)
            draw_trees(screen, terrain, camera_x)
            draw_collectibles(screen, coins, checkpoints, terrain, camera_x)
            bike.draw(screen, camera_x)

            finish_screen_x = int(finish_x - camera_x)
            pygame.draw.line(screen, (255, 255, 255), (finish_screen_x, 0), (finish_screen_x, SCREEN_HEIGHT), 3)

            speed_text = font.render(f"Speed: {abs(int(bike.vx))}", True, (14, 26, 50))
            coins_text = font.render(f"Apples: {collected}/{total_coins}", True, (14, 26, 50))
            setup_text = small_font.render(
                f"Bike: {BIKE_COLOR_OPTIONS[selected_color_index][0]} | Dampening: {DAMPENING_OPTIONS[selected_dampening_index][0]}",
                True,
                (20, 20, 30),
            )
            screen.blit(speed_text, (20, 16))
            screen.blit(coins_text, (20, 48))
            screen.blit(setup_text, (20, 80))

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

            if bike.crashed:
                crash = font.render("CRASHED - Respawning from checkpoint...", True, (200, 20, 20))
                screen.blit(crash, (SCREEN_WIDTH // 2 - crash.get_width() // 2, 140))
            elif bike.win:
                win = font.render("FINISH! All coins collected - Press R to replay", True, (10, 120, 10))
                screen.blit(win, (SCREEN_WIDTH // 2 - win.get_width() // 2, 140))
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
        else:
            draw_menu_screen(screen, title_font, small_font, selected_level_name)

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
