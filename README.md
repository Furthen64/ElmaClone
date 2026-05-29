# ElmaClone

2d dirtbike game with simple graphics in pygame, inspired by elastomania / across.

## First playable version (v1.1)

This repository now includes a first playable prototype with simple level data:

- terrain loaded from a JSON level file
- bike movement, jump, and in-air tilt controls
- coin collection (must collect all before finish)
- checkpoints with crash respawn
- finish line with win state

## Run

```bash
python -m pip install -r requirements.txt
python game.py
```

## Controls

- Left / Right: move
- Up / Down: tilt bike
- Space: flip bike direction
- R: full level restart

## Level format

Level file path: `levels/first_level.json`

```json
{
  "start_x": 140,
  "finish_x": 6000,
  "terrain": [[x, y], ...],
  "coins": [[x, y], ...],
  "checkpoints": [x, ...]
}
```
