from typing import Optional, Dict, Any
from .base_event import BaseEventDetector, TrafficEvent, EventSeverity
import time


class StoppedVehicleDetector(BaseEventDetector):

    def __init__(self, timeout_s: float = 10.0,
                 speed_threshold_kmh: float = 2.0,
                 min_tracking_frames: int = 30):
        super().__init__("stopped_vehicle", EventSeverity.EMERGENCY)
        self.timeout_s = timeout_s
        self.speed_threshold = speed_threshold_kmh
        self.min_tracking_frames = min_tracking_frames

        self._stopped_since: Dict[int, float] = {}
        self._notified_vehicles: set = set()

    def check(self, vehicle, **context) -> Optional[TrafficEvent]:
        track_id = vehicle.id
        frame_idx = context.get('frame_idx', 0)

        frames_tracked = frame_idx - vehicle.first_seen_frame
        if frames_tracked < self.min_tracking_frames:
            return None

        is_stopped = (vehicle.speed_kmh is not None and
                      vehicle.speed_kmh < self.speed_threshold and
                      vehicle.direction == "Stationary")

        current_time = time.time()

        if is_stopped:
            if track_id not in self._stopped_since:
                self._stopped_since[track_id] = current_time

            stopped_duration = current_time - self._stopped_since[track_id]

            if stopped_duration >= self.timeout_s and track_id not in self._notified_vehicles:
                self._notified_vehicles.add(track_id)

                return self.create_event(
                    track_id=track_id,
                    frame_idx=frame_idx,
                    vehicle_data=vehicle.to_dict(),
                    details={
                        "stopped_duration_s": round(stopped_duration, 1),
                        "position": vehicle.get_current_world_position(),
                        "lane_id": vehicle.lane_id,
                        "first_seen_frame": vehicle.first_seen_frame
                    }
                )
        else:
            if track_id in self._stopped_since:
                del self._stopped_since[track_id]
            self._notified_vehicles.discard(track_id)

        return None

    def reset_vehicle(self, track_id: int):
        self._stopped_since.pop(track_id, None)
        self._notified_vehicles.discard(track_id)
