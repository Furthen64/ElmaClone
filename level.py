import json
from pathlib import Path

from settings import LEVEL_FILES


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def load_level(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    terrain = [(float(x), float(y)) for x, y in data["terrain"]]
    terrain.sort(key=lambda point: point[0])

    finish_x = float(data["finish_x"])
    start_x = float(data.get("start_x", terrain[0][0]))

    coins = [
        {"x": float(x), "y": float(y), "collected": False}
        for x, y in data.get("coins", [])
    ]

    checkpoints = [
        {"x": float(x), "active": False}
        for x in sorted(data.get("checkpoints", []))
    ]

    return {
        "terrain": terrain,
        "finish_x": finish_x,
        "start_x": start_x,
        "coins": coins,
        "checkpoints": checkpoints,
    }


def load_level_entry(index: int) -> tuple[str, dict]:
    level_name, level_path = LEVEL_FILES[index % len(LEVEL_FILES)]
    return level_name, load_level(level_path)


def terrain_height_at(points: list[tuple[float, float]], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + (y2 - y1) * t

    return points[-1][1]


def terrain_slope_at(points: list[tuple[float, float]], x: float) -> float:
    if len(points) < 2:
        return 0.0
    if x <= points[0][0]:
        x1, y1 = points[0]
        x2, y2 = points[1]
    elif x >= points[-1][0]:
        x1, y1 = points[-2]
        x2, y2 = points[-1]
    else:
        x1 = y1 = x2 = y2 = 0.0
        for index in range(len(points) - 1):
            px1, py1 = points[index]
            px2, py2 = points[index + 1]
            if px1 <= x <= px2:
                x1, y1 = px1, py1
                x2, y2 = px2, py2
                break
    span = x2 - x1
    if abs(span) < 1e-6:
        return 0.0
    return (y2 - y1) / span
