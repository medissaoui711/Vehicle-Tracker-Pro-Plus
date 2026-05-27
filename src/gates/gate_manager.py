import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

from .virtual_gate import VirtualGate, GateCrossingEvent
from ..calibration.bev_transformer import BEVTransformer

logger = logging.getLogger(__name__)

class GateManager:

    def __init__(self, bev_transformer: BEVTransformer):
        self.bev = bev_transformer
        self.gates: Dict[str, VirtualGate] = {}
        self.crossing_history: List[GateCrossingEvent] = []

    def load_from_config(self, config_path: str) -> int:
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"ملف البوابات غير موجود: {config_path}. سيتم استخدام قائمة فارغة.")
            return 0

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gates_config = config.get('gates', [])

        for gc in gates_config:
            gate_id = gc['id']

            line_image = gc['line_image']
            p1_world = self.bev.image_to_world(line_image[0][0], line_image[0][1])
            p2_world = self.bev.image_to_world(line_image[1][0], line_image[1][1])
            line_world = (p1_world, p2_world)

            direction = gc.get('direction', 0)
            lane_id = gc.get('lane_id', None)

            gate = VirtualGate(
                gate_id=gate_id,
                line_world=line_world,
                direction=direction,
                lane_id=lane_id
            )

            self.gates[gate_id] = gate
            logger.info(f"تم تحميل البوابة: {gate}")

        logger.info(f"تم تحميل {len(self.gates)} بوابات")
        return len(self.gates)

    def add_gate(self, gate_id: str, line_image: Tuple[Tuple[int, int], Tuple[int, int]],
                 direction: int = 0, lane_id: Optional[int] = None) -> VirtualGate:
        p1_world = self.bev.image_to_world(line_image[0][0], line_image[0][1])
        p2_world = self.bev.image_to_world(line_image[1][0], line_image[1][1])
        line_world = (p1_world, p2_world)

        gate = VirtualGate(
            gate_id=gate_id,
            line_world=line_world,
            direction=direction,
            lane_id=lane_id
        )

        self.gates[gate_id] = gate
        return gate

    def check_all_gates(self, track_id: int, current_pos: Tuple[float, float],
                        previous_pos: Optional[Tuple[float, float]] = None,
                        frame_idx: int = 0) -> List[GateCrossingEvent]:
        new_crossings = []

        for gate in self.gates.values():
            event = gate.check_crossing(track_id, current_pos, previous_pos)
            if event:
                event.crossing_frame = frame_idx
                new_crossings.append(event)
                self.crossing_history.append(event)
                logger.info(f"عبور جديد: {track_id} عبر {gate.id} (الإطار {frame_idx})")

        return new_crossings

    def get_trap_speed(self, track_id: int, gate_id_1: str, gate_id_2: str) -> Optional[float]:
        gate1 = self.gates.get(gate_id_1)
        gate2 = self.gates.get(gate_id_2)

        if not gate1 or not gate2:
            return None

        crossing1 = gate1.get_crossing(track_id)
        crossing2 = gate2.get_crossing(track_id)

        if not crossing1 or not crossing2:
            return None

        p1 = np.array(crossing1.world_position)
        p2 = np.array(crossing2.world_position)
        distance_m = np.linalg.norm(p2 - p1)

        time_diff = crossing2.crossing_time - crossing1.crossing_time

        if time_diff > 0:
            speed_kmh = (distance_m / time_diff) * 3.6
            return speed_kmh

        return None

    def reset_gate_for_vehicle(self, gate_id: str, track_id: int):
        gate = self.gates.get(gate_id)
        if gate:
            gate.reset_crossing(track_id)

    def reset_all_gates(self):
        for gate in self.gates.values():
            gate.reset_all()
        self.crossing_history.clear()

    def get_gate(self, gate_id: str) -> Optional[VirtualGate]:
        return self.gates.get(gate_id)

    def get_all_gates(self) -> Dict[str, VirtualGate]:
        return self.gates.copy()

    def get_statistics(self) -> dict:
        total_crossings = len(self.crossing_history)

        stats = {
            "total_gates": len(self.gates),
            "total_crossings": total_crossings,
            "gates_detail": {}
        }

        for gate_id, gate in self.gates.items():
            gate_crossings = [c for c in self.crossing_history if c.gate_id == gate_id]
            stats["gates_detail"][gate_id] = {
                "crossings_count": len(gate_crossings),
                "active_vehicles": len(gate.crossings)
            }

        return stats
