import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from .lane_assigner import Lane, LaneAssigner

logger = logging.getLogger(__name__)


class LevelOfService:

    THRESHOLDS = {
        "A": 7,
        "B": 11,
        "C": 16,
        "D": 22,
        "E": 28,
        "F": float('inf')
    }

    COLORS = {
        "A": (0, 255, 0),
        "B": (50, 205, 50),
        "C": (255, 255, 0),
        "D": (255, 165, 0),
        "E": (255, 0, 0),
        "F": (128, 0, 0)
    }

    @classmethod
    def from_density(cls, density_vpkpl: float) -> str:
        for level, threshold in cls.THRESHOLDS.items():
            if density_vpkpl <= threshold:
                return level
        return "F"

    @classmethod
    def get_color(cls, level: str) -> Tuple[int, int, int]:
        return cls.COLORS.get(level, (255, 255, 255))


@dataclass
class RoadSegment:
    id: int
    y_start_m: float
    y_end_m: float
    length_m: float

    vehicle_count: int = 0
    density_vpkpl: float = 0.0
    avg_speed_kmh: float = 0.0
    los_level: str = "A"


class DensityAnalyzer:

    def __init__(self, lane_assigner: LaneAssigner,
                 total_length_m: float = 40.0,
                 segments_count: int = 4):
        self.lane_assigner = lane_assigner
        self.total_length_m = total_length_m
        self.segments_count = segments_count

        self.segments: List[RoadSegment] = []
        self._create_segments()

    def _create_segments(self):
        segment_length = self.total_length_m / self.segments_count

        for i in range(self.segments_count):
            y_start = i * segment_length
            y_end = (i + 1) * segment_length

            segment = RoadSegment(
                id=i,
                y_start_m=y_start,
                y_end_m=y_end,
                length_m=segment_length
            )
            self.segments.append(segment)

        logger.info(f"تم إنشاء {self.segments_count} مقاطع طريق "
                   f"(طول المقطع: {segment_length:.1f}م)")

    def analyze(self, active_vehicles: List) -> Dict[int, List[RoadSegment]]:
        results = {}

        for lane_id, lane in self.lane_assigner.lanes.items():
            lane_segments = []

            for segment in self.segments:
                vehicles_in_segment = self._count_vehicles_in_segment(
                    active_vehicles, lane_id, segment.y_start_m, segment.y_end_m
                )

                segment_length_km = segment.length_m / 1000.0
                density = len(vehicles_in_segment) / segment_length_km if segment_length_km > 0 else 0

                speeds = [v.speed_kmh for v in vehicles_in_segment
                         if v.speed_kmh is not None]
                avg_speed = np.mean(speeds) if speeds else 0.0

                los = LevelOfService.from_density(density)

                seg_result = RoadSegment(
                    id=segment.id,
                    y_start_m=segment.y_start_m,
                    y_end_m=segment.y_end_m,
                    length_m=segment.length_m,
                    vehicle_count=len(vehicles_in_segment),
                    density_vpkpl=round(density, 1),
                    avg_speed_kmh=round(avg_speed, 1),
                    los_level=los
                )
                lane_segments.append(seg_result)

            results[lane_id] = lane_segments

        return results

    def _count_vehicles_in_segment(self, vehicles: List, lane_id: int,
                                   y_start: float, y_end: float) -> List:
        result = []
        for v in vehicles:
            if not v.is_active or v.lane_id != lane_id:
                continue

            pos = v.get_current_world_position()
            if pos is None:
                continue

            _, world_y = pos

            if y_start <= world_y <= y_end:
                result.append(v)

        return result

    def get_overall_los(self, lane_id: int = None) -> str:
        if not hasattr(self, '_last_results'):
            return "A"

        worst_los = "A"
        los_order = ["A", "B", "C", "D", "E", "F"]

        for lid, segments in self._last_results.items():
            if lane_id is not None and lid != lane_id:
                continue
            for seg in segments:
                if los_order.index(seg.los_level) > los_order.index(worst_los):
                    worst_los = seg.los_level

        return worst_los

    def get_statistics(self, active_vehicles: List) -> dict:
        self._last_results = self.analyze(active_vehicles)

        stats = {
            "segments_count": self.segments_count,
            "total_length_m": self.total_length_m,
            "overall_los": self.get_overall_los(),
            "lanes": {}
        }

        for lane_id, segments in self._last_results.items():
            lane_stats = []
            for seg in segments:
                lane_stats.append({
                    "segment_id": seg.id,
                    "range_m": f"{seg.y_start_m:.0f}-{seg.y_end_m:.0f}",
                    "vehicle_count": seg.vehicle_count,
                    "density_vpkpl": seg.density_vpkpl,
                    "avg_speed_kmh": seg.avg_speed_kmh,
                    "los": seg.los_level
                })
            stats["lanes"][lane_id] = lane_stats

        return stats
