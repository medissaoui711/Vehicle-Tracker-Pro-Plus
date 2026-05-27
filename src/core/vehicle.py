import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple

@dataclass
class Vehicle:
    id: int
    cls: str
    first_seen_frame: int
    last_seen_frame: int = 0

    world_positions: deque = field(default_factory=lambda: deque(maxlen=30))

    speed_kmh: Optional[float] = None

    direction: str = "Unknown"

    lane_id: Optional[int] = None

    is_active: bool = True
    lost_frames: int = 0
    max_lost_frames: int = 30

    def update(self, world_x: float, world_y: float, frame_idx: int):
        self.world_positions.append((world_x, world_y, frame_idx))
        self.last_seen_frame = frame_idx
        self.lost_frames = 0
        self.is_active = True

    def mark_lost(self):
        self.lost_frames += 1
        if self.lost_frames > self.max_lost_frames:
            self.is_active = False

    def calculate_speed_and_direction(self, fps: float, min_frames: int = 5, smoothing_window: int = 5):
        if len(self.world_positions) < 2:
            return None, "Unknown"

        positions = list(self.world_positions)
        if len(positions) > smoothing_window:
            recent = positions[-smoothing_window:]
        else:
            recent = positions

        if len(recent) < 2:
            return self.speed_kmh, self.direction

        old_x, old_y, old_frame = recent[0]
        new_x, new_y, new_frame = recent[-1]

        frame_diff = new_frame - old_frame
        if frame_diff < min_frames or fps <= 0:
            return self.speed_kmh, self.direction

        time_sec = frame_diff / fps

        distance_m = np.hypot(new_x - old_x, new_y - old_y)

        if time_sec > 0.01:
            self.speed_kmh = (distance_m / time_sec) * 3.6

        y_diff = new_y - old_y
        if abs(y_diff) < 0.1:
            self.direction = "Stationary"
        elif y_diff > 0:
            self.direction = "Away"
        else:
            self.direction = "Towards"

        return self.speed_kmh, self.direction

    def get_current_world_position(self) -> Optional[Tuple[float, float]]:
        if self.world_positions:
            x, y, _ = self.world_positions[-1]
            return (x, y)
        return None

    def to_dict(self) -> dict:
        pos = self.get_current_world_position()
        return {
            "id": self.id,
            "class": self.cls,
            "speed_kmh": round(self.speed_kmh, 2) if self.speed_kmh else None,
            "direction": self.direction,
            "world_x": round(pos[0], 3) if pos else None,
            "world_y": round(pos[1], 3) if pos else None,
            "lane_id": self.lane_id,
            "is_active": self.is_active
        }

    def __repr__(self):
        speed_str = f"{self.speed_kmh:.1f}" if self.speed_kmh else "N/A"
        return f"Vehicle({self.id}, {self.cls}, {speed_str}km/h, {self.direction})"
