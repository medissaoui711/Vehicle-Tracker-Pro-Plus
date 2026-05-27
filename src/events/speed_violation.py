from typing import Optional, Dict, Any
from .base_event import BaseEventDetector, TrafficEvent, EventSeverity


class SpeedViolationDetector(BaseEventDetector):

    def __init__(self, speed_limit_kmh: float = 60.0,
                 tolerance_percent: float = 5.0,
                 min_consistent_frames: int = 3):
        super().__init__("speed_violation", EventSeverity.WARNING)
        self.speed_limit = speed_limit_kmh
        self.tolerance = 1.0 + (tolerance_percent / 100.0)
        self.min_consistent_frames = min_consistent_frames

        self._violation_frames: Dict[int, int] = {}
        self._notified_vehicles: set = set()

    def check(self, vehicle, **context) -> Optional[TrafficEvent]:
        if vehicle.speed_kmh is None:
            return None

        track_id = vehicle.id

        if vehicle.speed_kmh > self.speed_limit * self.tolerance:
            self._violation_frames[track_id] = self._violation_frames.get(track_id, 0) + 1

            if (self._violation_frames[track_id] >= self.min_consistent_frames
                and track_id not in self._notified_vehicles):

                self._notified_vehicles.add(track_id)

                excess_percent = ((vehicle.speed_kmh - self.speed_limit) / self.speed_limit) * 100

                if excess_percent > 50:
                    severity = EventSeverity.CRITICAL
                elif excess_percent > 30:
                    severity = EventSeverity.WARNING
                else:
                    severity = EventSeverity.INFO

                self.severity = severity

                return self.create_event(
                    track_id=track_id,
                    frame_idx=context.get('frame_idx', 0),
                    vehicle_data=vehicle.to_dict(),
                    details={
                        "speed_kmh": round(vehicle.speed_kmh, 2),
                        "speed_limit": self.speed_limit,
                        "excess_percent": round(excess_percent, 1),
                        "direction": vehicle.direction,
                        "lane_id": vehicle.lane_id
                    }
                )
        else:
            if track_id in self._violation_frames:
                del self._violation_frames[track_id]
            self._notified_vehicles.discard(track_id)

        return None

    def reset_vehicle(self, track_id: int):
        self._violation_frames.pop(track_id, None)
        self._notified_vehicles.discard(track_id)
