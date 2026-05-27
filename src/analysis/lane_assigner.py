import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

from ..calibration.bev_transformer import BEVTransformer

logger = logging.getLogger(__name__)


class Lane:

    def __init__(self, lane_id: int, name: str, direction: str,
                 boundary_left_world: np.ndarray,
                 boundary_right_world: np.ndarray,
                 length_m: float = 50.0):
        self.id = lane_id
        self.name = name
        self.direction = direction
        self.length_m = length_m

        self.boundary_left = np.array(boundary_left_world)
        self.boundary_right = np.array(boundary_right_world)

        self.centerline = (self.boundary_left + self.boundary_right) / 2.0

        self.width_m = self._calculate_width()

        self.vehicle_count: int = 0
        self.avg_speed: float = 0.0

    def _calculate_width(self) -> float:
        widths = []
        for i in range(min(len(self.boundary_left), len(self.boundary_right))):
            width = np.linalg.norm(self.boundary_right[i] - self.boundary_left[i])
            widths.append(width)
        return np.mean(widths) if widths else 3.5

    def contains_point(self, x: float, y: float, margin: float = 0.5) -> bool:
        point = np.array([x, y])

        min_dist = float('inf')
        for i in range(len(self.centerline) - 1):
            seg_start = self.centerline[i]
            seg_end = self.centerline[i + 1]

            dist = self._point_to_segment_distance(point, seg_start, seg_end)
            min_dist = min(min_dist, dist)

        return min_dist <= (self.width_m / 2.0 + margin)

    def _point_to_segment_distance(self, point: np.ndarray,
                                    seg_start: np.ndarray,
                                    seg_end: np.ndarray) -> float:
        seg_vec = seg_end - seg_start
        seg_len_sq = np.dot(seg_vec, seg_vec)

        if seg_len_sq == 0:
            return np.linalg.norm(point - seg_start)

        t = np.dot(point - seg_start, seg_vec) / seg_len_sq
        t = max(0.0, min(1.0, t))

        closest = seg_start + t * seg_vec
        return np.linalg.norm(point - closest)

    def update_statistics(self, vehicles: List):
        lane_vehicles = [v for v in vehicles if v.lane_id == self.id and v.is_active]
        self.vehicle_count = len(lane_vehicles)

        speeds = [v.speed_kmh for v in lane_vehicles if v.speed_kmh is not None]
        self.avg_speed = np.mean(speeds) if speeds else 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction,
            "width_m": round(self.width_m, 2),
            "length_m": self.length_m,
            "vehicle_count": self.vehicle_count,
            "avg_speed_kmh": round(self.avg_speed, 1)
        }

    def __repr__(self):
        return f"Lane({self.id}, '{self.name}', {self.direction}, width={self.width_m:.1f}m)"


class LaneAssigner:

    def __init__(self, bev_transformer: BEVTransformer, config_path: str = "config/lanes.json"):
        self.bev = bev_transformer
        self.lanes: Dict[int, Lane] = {}
        self.lanes_count: int = 0

        self._vehicle_lane_history: Dict[int, int] = {}
        self._lane_stability_frames: Dict[int, int] = {}
        self._stability_threshold: int = 5

        self.load_from_config(config_path)

    def load_from_config(self, config_path: str) -> int:
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"ملف الحارات غير موجود: {config_path}")
            return 0

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.lanes_count = config.get('lanes_count', 0)
        lanes_config = config.get('lanes', [])

        for lc in lanes_config:
            lane_id = lc['id']

            left_world = []
            for pt in lc['boundary_left']:
                wx, wy = self.bev.image_to_world(pt[0], pt[1])
                left_world.append([wx, wy])

            right_world = []
            for pt in lc['boundary_right']:
                wx, wy = self.bev.image_to_world(pt[0], pt[1])
                right_world.append([wx, wy])

            lane = Lane(
                lane_id=lane_id,
                name=lc.get('name', f'Lane_{lane_id}'),
                direction=lc.get('direction', 'Away'),
                boundary_left_world=left_world,
                boundary_right_world=right_world,
                length_m=lc.get('length_m', 50.0)
            )

            self.lanes[lane_id] = lane
            logger.info(f"تم تحميل الحارة: {lane}")

        logger.info(f"تم تحميل {len(self.lanes)} حارة")
        return len(self.lanes)

    def assign_lane(self, track_id: int, world_x: float, world_y: float) -> Optional[int]:
        best_lane = None
        min_distance = float('inf')

        for lane_id, lane in self.lanes.items():
            if lane.contains_point(world_x, world_y):
                center = lane.centerline[len(lane.centerline) // 2]
                dist = np.hypot(world_x - center[0], world_y - center[1])
                if dist < min_distance:
                    min_distance = dist
                    best_lane = lane_id

        if best_lane is not None:
            previous_lane = self._vehicle_lane_history.get(track_id)

            if previous_lane == best_lane:
                self._lane_stability_frames[track_id] = self._lane_stability_frames.get(track_id, 0) + 1
            else:
                self._lane_stability_frames[track_id] = 1

            if self._lane_stability_frames.get(track_id, 0) >= self._stability_threshold:
                self._vehicle_lane_history[track_id] = best_lane

            return self._vehicle_lane_history.get(track_id, best_lane)
        else:
            self._lane_stability_frames.pop(track_id, None)
            return self._vehicle_lane_history.get(track_id)

    def get_lane(self, lane_id: int) -> Optional[Lane]:
        return self.lanes.get(lane_id)

    def get_all_lanes(self) -> Dict[int, Lane]:
        return self.lanes.copy()

    def update_lane_statistics(self, active_vehicles: List):
        for lane in self.lanes.values():
            lane.update_statistics(active_vehicles)

    def remove_vehicle(self, track_id: int):
        self._vehicle_lane_history.pop(track_id, None)
        self._lane_stability_frames.pop(track_id, None)

    def get_statistics(self) -> dict:
        return {
            "lanes_count": self.lanes_count,
            "lanes": {lid: lane.to_dict() for lid, lane in self.lanes.items()}
        }
