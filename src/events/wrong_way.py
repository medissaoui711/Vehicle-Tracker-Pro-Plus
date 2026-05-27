from typing import Optional, Dict, Any
from .base_event import BaseEventDetector, TrafficEvent, EventSeverity
import numpy as np


class WrongWayDetector(BaseEventDetector):

    DIRECTION_TOWARDS = "Towards"
    DIRECTION_AWAY = "Away"

    def __init__(self, allowed_direction: str = "Away",
                 min_consistent_frames: int = 5,
                 min_distance_m: float = 3.0):
        super().__init__("wrong_way", EventSeverity.CRITICAL)
        self.allowed_direction = allowed_direction
        self.min_consistent_frames = min_consistent_frames
        self.min_distance_m = min_distance_m

        self._wrong_way_frames: Dict[int, int] = {}
        self._notified_vehicles: set = set()
        self._initial_positions: Dict[int, tuple] = {}

    def check(self, vehicle, **context) -> Optional[TrafficEvent]:
        if vehicle.direction == "Unknown" or vehicle.direction == "Stationary":
            return None

        track_id = vehicle.id

        if track_id not in self._initial_positions:
            pos = vehicle.get_current_world_position()
            if pos:
                self._initial_positions[track_id] = pos
            return None

        current_pos = vehicle.get_current_world_position()
        if not current_pos:
            return None

        initial_pos = self._initial_positions[track_id]
        distance_moved = np.hypot(
            current_pos[0] - initial_pos[0],
            current_pos[1] - initial_pos[1]
        )

        if distance_moved < self.min_distance_m:
            return None

        if vehicle.direction != self.allowed_direction:
            self._wrong_way_frames[track_id] = self._wrong_way_frames.get(track_id, 0) + 1

            if (self._wrong_way_frames[track_id] >= self.min_consistent_frames
                and track_id not in self._notified_vehicles):

                self._notified_vehicles.add(track_id)

                return self.create_event(
                    track_id=track_id,
                    frame_idx=context.get('frame_idx', 0),
                    vehicle_data=vehicle.to_dict(),
                    details={
                        "actual_direction": vehicle.direction,
                        "allowed_direction": self.allowed_direction,
                        "distance_moved_m": round(distance_moved, 2),
                        "lane_id": vehicle.lane_id
                    }
                )
        else:
            self._wrong_way_frames.pop(track_id, None)
            self._notified_vehicles.discard(track_id)

        return None

    def reset_vehicle(self, track_id: int):
        self._wrong_way_frames.pop(track_id, None)
        self._notified_vehicles.discard(track_id)
        self._initial_positions.pop(track_id, None)
