from typing import Dict, Optional, List
from .vehicle import Vehicle
import logging

logger = logging.getLogger(__name__)

class VehicleManager:

    def __init__(self, max_lost_frames: int = 30):
        self.vehicles: Dict[int, Vehicle] = {}
        self.max_lost_frames = max_lost_frames

    def get_or_create(self, track_id: int, class_name: str, frame_idx: int) -> Vehicle:
        if track_id in self.vehicles:
            vehicle = self.vehicles[track_id]
            vehicle.last_seen_frame = frame_idx
            vehicle.lost_frames = 0
            vehicle.is_active = True
            return vehicle

        vehicle = Vehicle(
            id=track_id,
            cls=class_name,
            first_seen_frame=frame_idx,
            last_seen_frame=frame_idx
        )
        vehicle.max_lost_frames = self.max_lost_frames
        self.vehicles[track_id] = vehicle

        logger.debug(f"مركبة جديدة: {vehicle}")
        return vehicle

    def mark_all_lost(self):
        for vehicle in self.vehicles.values():
            vehicle.mark_lost()

    def remove_inactive(self) -> List[Vehicle]:
        inactive = []
        to_remove = []

        for track_id, vehicle in self.vehicles.items():
            if not vehicle.is_active:
                inactive.append(vehicle)
                to_remove.append(track_id)
                logger.debug(f"إزالة مركبة غير نشطة: {vehicle}")

        for track_id in to_remove:
            del self.vehicles[track_id]

        return inactive

    def get_active_vehicles(self) -> List[Vehicle]:
        return [v for v in self.vehicles.values() if v.is_active]

    def get_vehicle(self, track_id: int) -> Optional[Vehicle]:
        return self.vehicles.get(track_id)

    def get_statistics(self) -> dict:
        active = self.get_active_vehicles()
        total_detected = len(self.vehicles)

        speeds = [v.speed_kmh for v in active if v.speed_kmh is not None]

        return {
            "total_detected": total_detected,
            "active_count": len(active),
            "avg_speed": sum(speeds) / len(speeds) if speeds else 0,
            "max_speed": max(speeds) if speeds else 0,
            "min_speed": min(speeds) if speeds else 0
        }
