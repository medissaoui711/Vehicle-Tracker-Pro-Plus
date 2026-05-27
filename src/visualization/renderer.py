import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict
from enum import Enum


class ColorScheme(Enum):
    VEHICLE_NORMAL = (0, 255, 0)
    VEHICLE_FAST = (0, 165, 255)
    VEHICLE_VIOLATION = (0, 0, 255)
    VEHICLE_STOPPED = (255, 0, 255)

    GATE_LINE = (255, 255, 0)
    GATE_LABEL = (255, 255, 255)

    DASHBOARD_BG = (30, 30, 30)
    DASHBOARD_BORDER = (100, 100, 100)
    DASHBOARD_TEXT = (220, 220, 220)
    DASHBOARD_HEADER = (0, 255, 255)

    LOS_A = (0, 255, 0)
    LOS_B = (50, 205, 50)
    LOS_C = (255, 255, 0)
    LOS_D = (255, 165, 0)
    LOS_E = (255, 0, 0)
    LOS_F = (128, 0, 0)

    TEXT_SHADOW = (0, 0, 0)
    ROI_BORDER = (255, 0, 255)


class Renderer:

    def __init__(self, font_scale: float = 0.5, thickness: int = 2):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = font_scale
        self.thickness = thickness

    def draw_vehicle_box(self, frame: np.ndarray, bbox: Tuple[int, int, int, int],
                         track_id: int, class_name: str, speed_kmh: Optional[float],
                         direction: str, lane_id: Optional[int] = None,
                         is_violating: bool = False, is_stopped: bool = False):
        x1, y1, x2, y2 = bbox

        if is_stopped:
            color = ColorScheme.VEHICLE_STOPPED.value
        elif is_violating:
            color = ColorScheme.VEHICLE_VIOLATION.value
        elif speed_kmh and speed_kmh > 60:
            color = ColorScheme.VEHICLE_FAST.value
        else:
            color = ColorScheme.VEHICLE_NORMAL.value

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.thickness)

        speed_str = f"{speed_kmh:.0f}km/h" if speed_kmh else "N/A"
        lane_str = f" L{lane_id}" if lane_id is not None else ""
        label = f"[{track_id}] {class_name} | {speed_str} | {direction}{lane_str}"

        self._draw_text_with_shadow(frame, label, (x1, y1 - 10), color)

    def draw_gate(self, frame: np.ndarray, gate_id: str,
                  line_image: Tuple[Tuple[int, int], Tuple[int, int]],
                  crossing_count: int = 0):
        p1 = tuple(line_image[0])
        p2 = tuple(line_image[1])

        cv2.line(frame, p1, p2, ColorScheme.GATE_LINE.value, 2)

        label = f"{gate_id} [{crossing_count}]"
        cv2.putText(frame, label,
                   (p1[0], p1[1] - 10),
                   self.font, 0.5, ColorScheme.GATE_LABEL.value, 1)

    def draw_roi(self, frame: np.ndarray, src_points: np.ndarray):
        pts = src_points.reshape((-1, 1, 2)).astype(np.int32)
        cv2.polylines(frame, [pts], True, ColorScheme.ROI_BORDER.value, 2)

        for pt in src_points:
            cv2.circle(frame, tuple(pt.astype(int)), 5, ColorScheme.ROI_BORDER.value, -1)

    def draw_event_alert(self, frame: np.ndarray, event_type: str,
                         track_id: int, position: Tuple[int, int]):
        alert_text = f"\u26a0 {event_type.upper()} - ID:{track_id}"

        (tw, th), _ = cv2.getTextSize(alert_text, self.font, 0.7, 2)
        cv2.rectangle(frame,
                     (position[0] - 5, position[1] - th - 10),
                     (position[0] + tw + 5, position[1] + 5),
                     (0, 0, 255), -1)

        cv2.putText(frame, alert_text, position,
                   self.font, 0.7, (255, 255, 255), 2)

    def _draw_text_with_shadow(self, frame: np.ndarray, text: str,
                               position: Tuple[int, int], color: Tuple[int, int, int]):
        cv2.putText(frame, text,
                   (position[0] + 1, position[1] + 1),
                   self.font, self.font_scale,
                   ColorScheme.TEXT_SHADOW.value, self.thickness + 1)
        cv2.putText(frame, text, position,
                   self.font, self.font_scale, color, self.thickness)
