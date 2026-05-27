import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
import time

@dataclass
class GateCrossingEvent:
    gate_id: str
    track_id: int
    crossing_time: float
    crossing_frame: int
    world_position: Tuple[float, float]
    direction: str
    speed_kmh: Optional[float] = None


class VirtualGate:

    def __init__(self, gate_id: str, line_world: Tuple[Tuple[float, float], Tuple[float, float]],
                 direction: int = 0, lane_id: Optional[int] = None):
        self.id = gate_id
        self.line_world = line_world
        self.direction = direction
        self.lane_id = lane_id

        self.crossings: Dict[int, GateCrossingEvent] = {}

        p1, p2 = self.line_world
        self.line_vector = np.array([p2[0] - p1[0], p2[1] - p1[1]])
        self.line_length = np.linalg.norm(self.line_vector)

        if self.line_length > 0:
            self.line_unit = self.line_vector / self.line_length
            self.normal = np.array([-self.line_unit[1], self.line_unit[0]])
        else:
            self.line_unit = np.array([0.0, 0.0])
            self.normal = np.array([0.0, 0.0])

        self.p1 = np.array(p1)
        self.p2 = np.array(p2)

    def check_crossing(self, track_id: int, current_pos: Tuple[float, float],
                       previous_pos: Optional[Tuple[float, float]] = None) -> Optional[GateCrossingEvent]:
        if track_id in self.crossings:
            return None

        curr = np.array(current_pos)

        distance = self._point_to_line_distance(curr)
        if distance > 1.0:
            return None

        if previous_pos is not None:
            prev = np.array(previous_pos)
            if not self._did_cross_line(prev, curr):
                return None
        else:
            if distance > 0.3:
                return None

        if self.direction != 0 and previous_pos is not None:
            prev = np.array(previous_pos)
            crossing_direction = np.sign(curr[1] - prev[1])
            if crossing_direction != self.direction:
                return None

        event = GateCrossingEvent(
            gate_id=self.id,
            track_id=track_id,
            crossing_time=time.time(),
            crossing_frame=0,
            world_position=(float(curr[0]), float(curr[1])),
            direction="Towards" if (curr[1] - (previous_pos[1] if previous_pos else curr[1])) < 0 else "Away"
        )

        self.crossings[track_id] = event

        return event

    def _point_to_line_distance(self, point: np.ndarray) -> float:
        v = point - self.p1
        t = np.dot(v, self.line_vector) / (self.line_length ** 2) if self.line_length > 0 else 0
        t = max(0.0, min(1.0, t))
        closest = self.p1 + t * self.line_vector
        return np.linalg.norm(point - closest)

    def _did_cross_line(self, prev: np.ndarray, curr: np.ndarray) -> bool:
        v1 = prev - self.p1
        v2 = curr - self.p1

        cross1 = np.cross(self.line_vector, v1)
        cross2 = np.cross(self.line_vector, v2)

        return cross1 * cross2 <= 0

    def get_crossing(self, track_id: int) -> Optional[GateCrossingEvent]:
        return self.crossings.get(track_id)

    def get_all_crossings(self) -> Dict[int, GateCrossingEvent]:
        return self.crossings.copy()

    def reset_crossing(self, track_id: int):
        self.crossings.pop(track_id, None)

    def reset_all(self):
        self.crossings.clear()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "line_world": [
                [float(self.p1[0]), float(self.p1[1])],
                [float(self.p2[0]), float(self.p2[1])]
            ],
            "direction": self.direction,
            "lane_id": self.lane_id,
            "active_crossings": len(self.crossings)
        }

    def __repr__(self):
        return f"VirtualGate({self.id}, dir={self.direction}, lane={self.lane_id})"
