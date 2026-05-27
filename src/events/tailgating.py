from typing import Optional, Dict, Any, List, Tuple
from .base_event import BaseEventDetector, TrafficEvent, EventSeverity
import numpy as np


class TailgatingDetector(BaseEventDetector):

    def __init__(self, min_time_gap_s: float = 2.0,
                 min_distance_m: float = 5.0,
                 same_lane_only: bool = True):
        super().__init__("tailgating", EventSeverity.WARNING)
        self.min_time_gap_s = min_time_gap_s
        self.min_distance_m = min_distance_m
        self.same_lane_only = same_lane_only

        self._notified_pairs: set = set()

    def check(self, vehicle, **context) -> Optional[TrafficEvent]:
        active_vehicles: List = context.get('active_vehicles', [])
        if len(active_vehicles) < 2:
            return None

        track_id = vehicle.id
        current_pos = vehicle.get_current_world_position()
        current_speed = vehicle.speed_kmh

        if not current_pos or current_speed is None or current_speed < 1.0:
            return None

        nearest_ahead = self._find_nearest_vehicle_ahead(
            vehicle, active_vehicles, same_lane=self.same_lane_only
        )

        if nearest_ahead is None:
            return None

        ahead_vehicle, distance_m = nearest_ahead

        time_gap = distance_m / (current_speed / 3.6) if current_speed > 0 else float('inf')

        if distance_m < self.min_distance_m or time_gap < self.min_time_gap_s:
            pair_key = (min(track_id, ahead_vehicle.id), max(track_id, ahead_vehicle.id))

            if pair_key not in self._notified_pairs:
                self._notified_pairs.add(pair_key)

                severity = EventSeverity.CRITICAL if time_gap < 1.0 else EventSeverity.WARNING
                self.severity = severity

                return self.create_event(
                    track_id=track_id,
                    frame_idx=context.get('frame_idx', 0),
                    vehicle_data=vehicle.to_dict(),
                    details={
                        "ahead_vehicle_id": ahead_vehicle.id,
                        "distance_m": round(distance_m, 2),
                        "time_gap_s": round(time_gap, 2),
                        "my_speed_kmh": round(current_speed, 1),
                        "ahead_speed_kmh": round(ahead_vehicle.speed_kmh, 1) if ahead_vehicle.speed_kmh else None,
                        "lane_id": vehicle.lane_id
                    }
                )
        else:
            pair_key = (min(track_id, ahead_vehicle.id), max(track_id, ahead_vehicle.id))
            self._notified_pairs.discard(pair_key)

        return None

    def _find_nearest_vehicle_ahead(self, vehicle, all_vehicles: List,
                                     same_lane: bool = True) -> Optional[Tuple[Any, float]]:
        current_pos = vehicle.get_current_world_position()
        if not current_pos:
            return None

        current_x, current_y = current_pos
        vehicle_direction = vehicle.direction

        nearest = None
        min_distance = float('inf')

        for other in all_vehicles:
            if other.id == vehicle.id or not other.is_active:
                continue

            other_pos = other.get_current_world_position()
            if not other_pos:
                continue

            other_x, other_y = other_pos

            if same_lane and vehicle.lane_id is not None and other.lane_id is not None:
                if vehicle.lane_id != other.lane_id:
                    continue

            is_ahead = False
            if vehicle_direction == "Away":
                if other_y > current_y:
                    is_ahead = True
            elif vehicle_direction == "Towards":
                if other_y < current_y:
                    is_ahead = True
            else:
                is_ahead = True

            if not is_ahead:
                continue

            distance = np.hypot(other_x - current_x, other_y - current_y)

            if distance < min_distance:
                min_distance = distance
                nearest = (other, distance)

        return nearest

    def reset_vehicle(self, track_id: int):
        to_remove = []
        for pair in self._notified_pairs:
            if track_id in pair:
                to_remove.append(pair)
        for pair in to_remove:
            self._notified_pairs.discard(pair)
