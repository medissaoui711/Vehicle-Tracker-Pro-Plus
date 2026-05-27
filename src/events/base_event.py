from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
import time
from enum import Enum


class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class TrafficEvent:
    event_type: str
    track_id: int
    timestamp: float = field(default_factory=time.time)
    frame_idx: int = 0
    severity: EventSeverity = EventSeverity.INFO

    vehicle_data: Dict[str, Any] = field(default_factory=dict)

    details: Dict[str, Any] = field(default_factory=dict)

    snapshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "track_id": self.track_id,
            "timestamp": self.timestamp,
            "frame_idx": self.frame_idx,
            "severity": self.severity.value,
            "vehicle_data": self.vehicle_data,
            "details": self.details,
            "snapshot_path": self.snapshot_path
        }

    def __repr__(self):
        return (f"TrafficEvent({self.event_type}, track={self.track_id}, "
                f"severity={self.severity.value}, frame={self.frame_idx})")


EventListener = Callable[[TrafficEvent], None]


class BaseEventDetector(ABC):

    def __init__(self, event_type: str, severity: EventSeverity = EventSeverity.WARNING):
        self.event_type = event_type
        self.severity = severity

        self._listeners: List[EventListener] = []

        self.detection_count: int = 0
        self.last_detection_time: Optional[float] = None

    def subscribe(self, listener: EventListener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def notify(self, event: TrafficEvent):
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"خطأ في مستمع الأحداث: {e}")

    def create_event(self, track_id: int, frame_idx: int = 0,
                     vehicle_data: Optional[Dict[str, Any]] = None,
                     details: Optional[Dict[str, Any]] = None) -> TrafficEvent:
        event = TrafficEvent(
            event_type=self.event_type,
            track_id=track_id,
            frame_idx=frame_idx,
            severity=self.severity,
            vehicle_data=vehicle_data or {},
            details=details or {}
        )

        self.detection_count += 1
        self.last_detection_time = time.time()

        self.notify(event)

        return event

    @abstractmethod
    def check(self, vehicle, **context) -> Optional[TrafficEvent]:
        pass

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "detection_count": self.detection_count,
            "last_detection_time": self.last_detection_time
        }

    def reset_statistics(self):
        self.detection_count = 0
        self.last_detection_time = None
