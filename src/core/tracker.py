from ultralytics import YOLO
from typing import List, Tuple, Optional, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)

SUPPORTED_CLASSES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

class YOLOTracker:

    def __init__(self, model_path: str = "yolov8n.pt",
                 tracker_config: str = "bytetrack.yaml",
                 confidence: float = 0.3,
                 iou: float = 0.45,
                 device: Optional[str] = None):
        self.confidence = confidence
        self.iou = iou
        self.tracker_config = tracker_config

        logger.info(f"تحميل النموذج من: {model_path}")
        self.model = YOLO(model_path)

        if device:
            self.model.to(device)

    def detect_and_track(self, frame: np.ndarray, persist: bool = True, verbose: bool = False) -> List[Dict]:
        results = self.model.track(
            frame,
            persist=persist,
            conf=self.confidence,
            iou=self.iou,
            tracker=self.tracker_config,
            verbose=verbose
        )

        detections = []

        if results[0].boxes is None or results[0].boxes.id is None:
            return detections

        boxes = results[0].boxes.xyxy.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy().astype(int)
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        confidences = results[0].boxes.conf.cpu().numpy() if results[0].boxes.conf is not None else np.ones(len(track_ids))

        for box, cls_id, track_id, conf in zip(boxes, classes, track_ids, confidences):
            if cls_id not in SUPPORTED_CLASSES:
                continue

            x1, y1, x2, y2 = map(float, box)

            cx = (x1 + x2) / 2.0
            cy = y2

            detection = {
                'track_id': int(track_id),
                'class_id': int(cls_id),
                'class_name': SUPPORTED_CLASSES[cls_id],
                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                'center_bottom': (cx, cy),
                'confidence': float(conf)
            }

            detections.append(detection)

        return detections
