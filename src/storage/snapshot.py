import cv2
import os
import time
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SnapshotCapture:

    def __init__(self, snapshots_dir: str = "data/snapshots"):
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, frame, event_type: str, track_id: int,
                frame_idx: int) -> Optional[str]:
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{event_type}_track{track_id}_frame{frame_idx}_{timestamp}.jpg"
            filepath = self.snapshots_dir / filename

            cv2.imwrite(str(filepath), frame)
            logger.debug(f"تم حفظ لقطة: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"فشل حفظ اللقطة: {e}")
            return None
