import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class FrameStats:
    frame_idx: int
    timestamp: float
    active_vehicles: int
    total_detected: int
    avg_speed_kmh: float
    max_speed_kmh: float
    min_speed_kmh: float
    vehicles_per_class: Dict[str, int]
    events_triggered: int


class StatisticsCollector:

    def __init__(self, report_interval_frames: int = 300):
        self.report_interval = report_interval_frames

        self._frame_stats: List[FrameStats] = []
        self._max_history = 10000

        self.session_start_time = time.time()
        self.total_frames_processed = 0
        self.total_vehicles_detected = 0
        self.total_events = 0

        self._class_counts: Dict[str, int] = defaultdict(int)
        self._class_speeds: Dict[str, List[float]] = defaultdict(list)

        self.max_recorded_speed = 0.0
        self.max_speed_vehicle_id = None

    def collect_frame(self, frame_idx: int, active_vehicles: List,
                      total_detected: int, events_count: int = 0) -> FrameStats:
        speeds = [v.speed_kmh for v in active_vehicles if v.speed_kmh is not None]

        class_count = defaultdict(int)
        for v in active_vehicles:
            class_count[v.cls] += 1
            self._class_counts[v.cls] += 1
            if v.speed_kmh is not None:
                self._class_speeds[v.cls].append(v.speed_kmh)

                if v.speed_kmh > self.max_recorded_speed:
                    self.max_recorded_speed = v.speed_kmh
                    self.max_speed_vehicle_id = v.id

        stats = FrameStats(
            frame_idx=frame_idx,
            timestamp=time.time(),
            active_vehicles=len(active_vehicles),
            total_detected=total_detected,
            avg_speed_kmh=round(np.mean(speeds), 1) if speeds else 0.0,
            max_speed_kmh=round(max(speeds), 1) if speeds else 0.0,
            min_speed_kmh=round(min(speeds), 1) if speeds else 0.0,
            vehicles_per_class=dict(class_count),
            events_triggered=events_count
        )

        self._frame_stats.append(stats)
        if len(self._frame_stats) > self._max_history:
            self._frame_stats = self._frame_stats[-self._max_history:]

        self.total_frames_processed += 1
        self.total_vehicles_detected = total_detected
        self.total_events += events_count

        return stats

    def should_generate_report(self, frame_idx: int) -> bool:
        return frame_idx % self.report_interval == 0 and frame_idx > 0

    def generate_report(self) -> Dict[str, Any]:
        elapsed_time = time.time() - self.session_start_time

        class_stats = {}
        for cls_name, counts in self._class_counts.items():
            speeds = self._class_speeds.get(cls_name, [])
            class_stats[cls_name] = {
                "total_count": counts,
                "avg_speed": round(np.mean(speeds), 1) if speeds else 0.0,
                "max_speed": round(max(speeds), 1) if speeds else 0.0
            }

        return {
            "session_duration_s": round(elapsed_time, 1),
            "total_frames": self.total_frames_processed,
            "total_vehicles": self.total_vehicles_detected,
            "total_events": self.total_events,
            "max_recorded_speed": round(self.max_recorded_speed, 1),
            "max_speed_vehicle_id": self.max_speed_vehicle_id,
            "class_statistics": class_stats,
            "recent_avg_speed": self._get_recent_average(100),
            "processing_fps": round(self.total_frames_processed / elapsed_time, 1) if elapsed_time > 0 else 0
        }

    def _get_recent_average(self, window: int = 100) -> float:
        recent = self._frame_stats[-window:]
        if not recent:
            return 0.0
        avg_speeds = [s.avg_speed_kmh for s in recent if s.avg_speed_kmh > 0]
        return round(np.mean(avg_speeds), 1) if avg_speeds else 0.0

    def get_current_stats(self) -> Optional[FrameStats]:
        return self._frame_stats[-1] if self._frame_stats else None

    def reset(self):
        self._frame_stats.clear()
        self.session_start_time = time.time()
        self.total_frames_processed = 0
        self.total_vehicles_detected = 0
        self.total_events = 0
        self._class_counts.clear()
        self._class_speeds.clear()
        self.max_recorded_speed = 0.0
