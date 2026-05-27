from typing import List, Dict, Optional, Any
import logging
from .base_event import BaseEventDetector, TrafficEvent, EventListener
from .speed_violation import SpeedViolationDetector
from .wrong_way import WrongWayDetector
from .tailgating import TailgatingDetector
from .stopped_vehicle import StoppedVehicleDetector

logger = logging.getLogger(__name__)


class EventDispatcher:

    def __init__(self):
        self._detectors: Dict[str, BaseEventDetector] = {}

        self._global_listeners: List[EventListener] = []

        self._event_history: List[TrafficEvent] = []
        self._max_history = 1000

        self._total_events = 0

    def register_detector(self, detector: BaseEventDetector):
        self._detectors[detector.event_type] = detector

        for listener in self._global_listeners:
            detector.subscribe(listener)

        logger.info(f"تم تسجيل كاشف: {detector.event_type}")

    def register_default_detectors(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}

        events_config = config.get('events', {})

        speed_cfg = events_config.get('speed', {})
        if speed_cfg.get('enabled', True):
            detector = SpeedViolationDetector(
                speed_limit_kmh=speed_cfg.get('limit_kmh', 60.0),
                tolerance_percent=speed_cfg.get('tolerance_percent', 5.0),
                min_consistent_frames=speed_cfg.get('min_frames', 3)
            )
            self.register_detector(detector)

        wrong_way_cfg = events_config.get('wrong_way', {})
        if wrong_way_cfg.get('enabled', True):
            detector = WrongWayDetector(
                allowed_direction=wrong_way_cfg.get('allowed_direction', 'Away'),
                min_consistent_frames=wrong_way_cfg.get('min_frames', 5)
            )
            self.register_detector(detector)

        tailgating_cfg = events_config.get('tailgating', {})
        if tailgating_cfg.get('enabled', True):
            detector = TailgatingDetector(
                min_time_gap_s=tailgating_cfg.get('time_gap_s', 2.0),
                min_distance_m=tailgating_cfg.get('min_distance_m', 5.0),
                same_lane_only=tailgating_cfg.get('same_lane_only', True)
            )
            self.register_detector(detector)

        stopped_cfg = events_config.get('stopped_vehicle', {})
        if stopped_cfg.get('enabled', True):
            detector = StoppedVehicleDetector(
                timeout_s=stopped_cfg.get('timeout_s', 10.0),
                speed_threshold_kmh=stopped_cfg.get('speed_threshold', 2.0)
            )
            self.register_detector(detector)

        logger.info(f"تم تسجيل {len(self._detectors)} كاشفات أحداث")

    def subscribe_global(self, listener: EventListener):
        self._global_listeners.append(listener)

        for detector in self._detectors.values():
            detector.subscribe(listener)

    def unsubscribe_global(self, listener: EventListener):
        if listener in self._global_listeners:
            self._global_listeners.remove(listener)

        for detector in self._detectors.values():
            detector.unsubscribe(listener)

    def check_all(self, vehicle, **context) -> List[TrafficEvent]:
        detected_events = []

        for detector in self._detectors.values():
            try:
                event = detector.check(vehicle, **context)
                if event:
                    detected_events.append(event)
                    self._add_to_history(event)
            except Exception as e:
                logger.error(f"خطأ في كاشف {detector.event_type}: {e}")

        return detected_events

    def check_all_vehicles(self, vehicles: List, **context) -> List[TrafficEvent]:
        context['active_vehicles'] = vehicles

        all_events = []
        for vehicle in vehicles:
            events = self.check_all(vehicle, **context)
            all_events.extend(events)

        return all_events

    def notify_vehicle_removed(self, track_id: int):
        for detector in self._detectors.values():
            if hasattr(detector, 'reset_vehicle'):
                detector.reset_vehicle(track_id)

    def _add_to_history(self, event: TrafficEvent):
        self._event_history.append(event)
        self._total_events += 1

        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_recent_events(self, count: int = 10) -> List[TrafficEvent]:
        return self._event_history[-count:]

    def get_events_by_type(self, event_type: str) -> List[TrafficEvent]:
        return [e for e in self._event_history if e.event_type == event_type]

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_events": self._total_events,
            "detectors": {}
        }

        for name, detector in self._detectors.items():
            stats["detectors"][name] = detector.get_statistics()

        return stats

    def clear_history(self):
        self._event_history.clear()

    def reset_all(self):
        for detector in self._detectors.values():
            detector.reset_statistics()
        self._event_history.clear()
        self._total_events = 0
