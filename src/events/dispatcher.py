from src.events.base_event import BaseEvent
from src.events.speed_violation import SpeedViolation
from src.events.wrong_way import WrongWay
from src.events.tailgating import Tailgating
from src.events.stopped_vehicle import StoppedVehicle
from src.storage.database import DatabaseLogger


class EventDispatcher:
    def __init__(self, config: dict, db: DatabaseLogger | None = None):
        self.db = db
        self.detectors: list[BaseEvent] = []
        self._detected_events: list[dict] = []

        if config.get("speed", {}).get("enabled", True):
            self.register_detector(SpeedViolation(config.get("speed", {})))
        if config.get("wrong_way", {}).get("enabled", True):
            self.register_detector(WrongWay(config.get("wrong_way", {})))
        if config.get("tailgating", {}).get("enabled", True):
            self.register_detector(Tailgating(config.get("tailgating", {})))
        if config.get("stopped_vehicle", {}).get("enabled", True):
            self.register_detector(StoppedVehicle(config.get("stopped_vehicle", {})))

    def register_detector(self, detector: BaseEvent):
        self.detectors.append(detector)

    def dispatch(self, vehicle, all_vehicles: list, frame_id: int, fps: float) -> list[dict]:
        frame_events = []
        for detector in self.detectors:
            result = detector.check(vehicle, all_vehicles, frame_id, fps)
            if result is not None:
                event_data = detector.to_dict(result)
                frame_events.append(event_data)
                self._detected_events.append(event_data)
                if self.db:
                    self.db.log_event(
                        event_data["type"],
                        event_data["vehicle_id"],
                        event_data["details"],
                    )
        return frame_events

    def log_all(self, db: DatabaseLogger):
        for event in self._detected_events:
            db.log_event(event["type"], event["vehicle_id"], event["details"])

    def get_recent(self, limit: int = 10) -> list[dict]:
        return self._detected_events[-limit:]

    def clear(self):
        self._detected_events.clear()
