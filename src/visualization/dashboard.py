import cv2
import numpy as np
import time
from typing import List, Dict, Optional, Tuple
from .renderer import ColorScheme


class Dashboard:

    def __init__(self, position: Tuple[int, int] = (10, 10),
                 width: int = 320, alpha: float = 0.7):
        self.position = position
        self.width = width
        self.alpha = alpha
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.line_height = 22
        self.padding = 8
        self.header_height = 30

        self._fps_history = []
        self._last_frame_time = time.time()

    def calculate_fps(self) -> float:
        now = time.time()
        self._fps_history.append(now - self._last_frame_time)
        self._last_frame_time = now

        if len(self._fps_history) > 30:
            self._fps_history.pop(0)

        avg_frame_time = np.mean(self._fps_history) if self._fps_history else 0.033
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0

    def draw(self, frame: np.ndarray,
             frame_idx: int,
             active_vehicles_count: int,
             total_detected: int,
             avg_speed: float,
             events: List[Dict],
             lanes_los: Dict[int, str],
             db_stats: Optional[Dict] = None):
        fps = self.calculate_fps()

        content_lines = 8
        content_lines += len(lanes_los)
        content_lines += min(len(events), 3)

        total_height = (self.header_height +
                       self.padding * 2 +
                       content_lines * self.line_height)

        x, y = self.position

        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (x, y),
                     (x + self.width, y + total_height),
                     ColorScheme.DASHBOARD_BG.value, -1)
        cv2.rectangle(overlay,
                     (x, y),
                     (x + self.width, y + total_height),
                     ColorScheme.DASHBOARD_BORDER.value, 1)
        frame = cv2.addWeighted(frame, 1 - self.alpha, overlay, self.alpha, 0)

        cv2.rectangle(frame,
                     (x, y),
                     (x + self.width, y + self.header_height),
                     ColorScheme.DASHBOARD_BORDER.value, -1)
        cv2.putText(frame, "Vehicle Tracker Pro++",
                   (x + 8, y + 22),
                   self.font, 0.6, ColorScheme.DASHBOARD_HEADER.value, 2)

        y_pos = y + self.header_height + self.padding

        lines = [
            f"Frame: {frame_idx}  |  FPS: {fps:.1f}",
            f"Vehicles: {active_vehicles_count} active / {total_detected} total",
            f"Avg Speed: {avg_speed:.1f} km/h",
        ]

        for line in lines:
            cv2.putText(frame, line, (x + 8, y_pos + 18),
                       self.font, 0.5, ColorScheme.DASHBOARD_TEXT.value, 1)
            y_pos += self.line_height

        y_pos += 5
        cv2.line(frame, (x + 8, y_pos), (x + self.width - 8, y_pos),
                ColorScheme.DASHBOARD_BORDER.value, 1)
        y_pos += 8

        cv2.putText(frame, "Level of Service:",
                   (x + 8, y_pos + 18),
                   self.font, 0.5, ColorScheme.DASHBOARD_HEADER.value, 1)
        y_pos += self.line_height

        for lane_id, los in sorted(lanes_los.items()):
            los_color = self._get_los_color(los)
            cv2.putText(frame, f"  Lane {lane_id}:",
                       (x + 8, y_pos + 18),
                       self.font, 0.5, ColorScheme.DASHBOARD_TEXT.value, 1)

            cv2.rectangle(frame,
                         (x + 140, y_pos + 5),
                         (x + 180, y_pos + 23),
                         los_color, -1)
            cv2.putText(frame, f" {los} ",
                       (x + 145, y_pos + 18),
                       self.font, 0.5, (0, 0, 0), 1)
            y_pos += self.line_height

        y_pos += 5
        cv2.line(frame, (x + 8, y_pos), (x + self.width - 8, y_pos),
                ColorScheme.DASHBOARD_BORDER.value, 1)
        y_pos += 8

        if events:
            cv2.putText(frame, "Recent Events:",
                       (x + 8, y_pos + 18),
                       self.font, 0.5, ColorScheme.DASHBOARD_HEADER.value, 1)
            y_pos += self.line_height

            for event in events[-3:]:
                event_text = f"  [{event.get('severity', '?')}] {event.get('event_type', '?')} ID:{event.get('track_id', '?')}"
                cv2.putText(frame, event_text[:40],
                           (x + 8, y_pos + 18),
                           self.font, 0.4,
                           (255, 200, 200), 1)
                y_pos += self.line_height

        if db_stats:
            y_pos += 5
            cv2.putText(frame,
                       f"DB: {db_stats.get('vehicles_written', 0)}v / {db_stats.get('events_written', 0)}e",
                       (x + 8, y_pos + 18),
                       self.font, 0.4, ColorScheme.DASHBOARD_TEXT.value, 1)

        return frame

    def _get_los_color(self, los: str) -> Tuple[int, int, int]:
        los_colors = {
            "A": ColorScheme.LOS_A.value,
            "B": ColorScheme.LOS_B.value,
            "C": ColorScheme.LOS_C.value,
            "D": ColorScheme.LOS_D.value,
            "E": ColorScheme.LOS_E.value,
            "F": ColorScheme.LOS_F.value,
        }
        return los_colors.get(los, (128, 128, 128))
