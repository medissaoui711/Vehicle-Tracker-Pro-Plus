
#!/usr/bin/env python3

import cv2
import json
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.tracker import YOLOTracker
from src.core.vehicle_manager import VehicleManager
from src.core.vehicle import Vehicle
from src.calibration.bev_transformer import BEVTransformer
from src.gates.gate_manager import GateManager
from src.events.event_dispatcher import EventDispatcher
from src.events.base_event import TrafficEvent
from src.analysis.lane_assigner import LaneAssigner
from src.analysis.density import DensityAnalyzer
from src.analysis.statistics import StatisticsCollector
from src.storage.database import (DatabaseManager, AsyncDatabaseWriter,
                                   VehicleRecord, EventRecord, DensityRecord)
from src.storage.csv_writer import CSVWriter
from src.storage.snapshot import SnapshotCapture
from src.visualization.renderer import Renderer
from src.visualization.dashboard import Dashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/tracker.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("ProPlusTracker")


class ProPlusTracker:

    def __init__(self, config_path: str = "config.json"):
        logger.info("="*60)
        logger.info("بدء تهيئة Vehicle Tracker Pro++")
        logger.info("="*60)

        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = json.load(f)

        logger.info("تهيئة محول المنظور (BEV)...")
        self.bev = BEVTransformer(
            src_points=self.cfg['calibration']['src_points'],
            dst_meters=self.cfg['calibration']['dst_meters']
        )

        logger.info("تحميل نموذج YOLO...")
        self.tracker = YOLOTracker(
            model_path=self.cfg.get('model_path', 'yolov8n.pt'),
            tracker_config=self.cfg.get('tracker', 'bytetrack.yaml'),
            confidence=self.cfg.get('confidence', 0.3),
            iou=self.cfg.get('iou', 0.45)
        )

        self.vehicle_manager = VehicleManager(max_lost_frames=30)

        speed_cfg = self.cfg.get('speed', {})
        self.speed_min_frames = speed_cfg.get('min_frames', 5)
        self.speed_smoothing = speed_cfg.get('smoothing_window', 5)

        logger.info("تحميل البوابات الافتراضية...")
        self.gate_manager = GateManager(self.bev)
        gates_config = self.cfg.get('gates_config', 'config/gates.json')
        self.gate_manager.load_from_config(gates_config)

        logger.info("تهيئة كاشفات الأحداث...")
        self.event_dispatcher = EventDispatcher()
        self.event_dispatcher.register_default_detectors(self.cfg)

        logger.info("تحميل تعريفات الحارات...")
        self.lane_assigner = LaneAssigner(
            self.bev,
            config_path=self.cfg.get('lanes_config', 'config/lanes.json')
        )

        self.density_analyzer = DensityAnalyzer(
            self.lane_assigner,
            total_length_m=self.cfg.get('density', {}).get('total_length_m', 40.0),
            segments_count=self.cfg.get('density', {}).get('segments_count', 4)
        )

        self.statistics_collector = StatisticsCollector(
            report_interval_frames=self.cfg.get('statistics', {}).get('report_interval', 300)
        )

        storage_cfg = self.cfg.get('storage', {})

        logger.info("تهيئة قاعدة البيانات...")
        self.db_manager = DatabaseManager(
            db_path=storage_cfg.get('database_path', 'data/traffic.db')
        )

        self.session_id = self.db_manager.start_session(
            source=self.cfg.get('source', 'unknown'),
            notes="Pro++ tracking session"
        )

        self.async_writer: Optional[AsyncDatabaseWriter] = None
        async_cfg = storage_cfg.get('async_writer', {})
        if async_cfg.get('enabled', True):
            logger.info("بدء الكاتب غير المتزامن...")
            self.async_writer = AsyncDatabaseWriter(
                self.db_manager,
                self.session_id,
                batch_size=async_cfg.get('batch_size', 50),
                flush_interval_s=async_cfg.get('flush_interval_s', 2.0)
            )
            self.async_writer.start()

        self.csv_writer = CSVWriter(
            csv_dir=storage_cfg.get('csv_dir', 'data/reports')
        )
        self.csv_writer.open_file(
            "daily_stats",
            ["timestamp", "frame", "track_id", "class", "speed_kmh", "direction", "lane", "event"]
        )

        self.snapshot_capture = SnapshotCapture(
            snapshots_dir=storage_cfg.get('snapshots_dir', 'data/snapshots')
        )

        self.log_vehicles_every = storage_cfg.get('log_vehicles_every_n_frames', 30)
        self.log_density_every = storage_cfg.get('log_density_every_n_frames', 30)
        self.capture_severities = storage_cfg.get('capture_snapshots_for_severities',
                                                   ['critical', 'emergency'])

        viz_cfg = self.cfg.get('visualization', {})

        self.renderer = Renderer(
            font_scale=viz_cfg.get('font_scale', 0.5),
            thickness=viz_cfg.get('thickness', 2)
        )

        self.dashboard = Dashboard(
            position=tuple(viz_cfg.get('dashboard_position', [10, 10])),
            width=viz_cfg.get('dashboard_width', 320)
        )

        self.show_display = viz_cfg.get('show_display', True)
        self.output_video_path = self.cfg.get('output_video')
        self.show_dashboard = viz_cfg.get('show_dashboard', True)
        self.show_gates = viz_cfg.get('show_gates', True)

        self.video_writer: Optional[cv2.VideoWriter] = None

        logger.info("="*60)
        logger.info("اكتملت تهيئة جميع الطبقات بنجاح")
        logger.info("="*60)

    def process_video(self):
        source = self.cfg.get('source', 'video.mp4')

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"فشل فتح المصدر: {source}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"المصدر: {source} | الدقة: {width}x{height} | FPS: {fps:.1f}")

        if self.output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                self.output_video_path, fourcc, fps, (width, height)
            )
            logger.info(f"حفظ الفيديو إلى: {self.output_video_path}")

        frame_idx = 0
        start_time = time.time()

        self._should_stop = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("بدء معالجة الفيديو...")

        while not self._should_stop:
            ret, frame = cap.read()
            if not ret:
                logger.info("انتهى الفيديو أو انقطع البث")
                break

            frame_idx += 1

            self.vehicle_manager.mark_all_lost()
            detections = self.tracker.detect_and_track(frame, persist=True, verbose=False)

            frame_events = []

            for det in detections:
                vehicle = self.vehicle_manager.get_or_create(
                    track_id=det['track_id'],
                    class_name=det['class_name'],
                    frame_idx=frame_idx
                )

                cx, cy = det['center_bottom']

                if self.bev.is_point_in_roi(cx, cy):
                    world_x, world_y = self.bev.image_to_world(cx, cy)

                    vehicle.update(world_x, world_y, frame_idx)

                    vehicle.calculate_speed_and_direction(
                        fps=fps,
                        min_frames=self.speed_min_frames,
                        smoothing_window=self.speed_smoothing
                    )

                    lane_id = self.lane_assigner.assign_lane(vehicle.id, world_x, world_y)
                    vehicle.lane_id = lane_id

                    prev_pos = None
                    if len(vehicle.world_positions) >= 2:
                        px, py, _ = vehicle.world_positions[-2]
                        prev_pos = (px, py)

                    crossings = self.gate_manager.check_all_gates(
                        track_id=vehicle.id,
                        current_pos=(world_x, world_y),
                        previous_pos=prev_pos,
                        frame_idx=frame_idx
                    )

                    for crossing in crossings:
                        crossing.speed_kmh = vehicle.speed_kmh
                        logger.info(f"\U0001f6a6 عبور: {crossing.gate_id} - مركبة {vehicle.id}")

            removed = self.vehicle_manager.remove_inactive()
            for v in removed:
                self.event_dispatcher.notify_vehicle_removed(v.id)
                self.lane_assigner.remove_vehicle(v.id)

            active_vehicles = self.vehicle_manager.get_active_vehicles()

            for vehicle in active_vehicles:
                events = self.event_dispatcher.check_all(
                    vehicle,
                    frame_idx=frame_idx,
                    active_vehicles=active_vehicles
                )

                for event in events:
                    frame_events.append(event)

                    if event.severity.value in self.capture_severities:
                        snapshot_path = self.snapshot_capture.capture(
                            frame, event.event_type, event.track_id, frame_idx
                        )
                        event.snapshot_path = snapshot_path

                    if self.async_writer:
                        event_record = EventRecord(
                            event_type=event.event_type,
                            track_id=event.track_id,
                            severity=event.severity.value,
                            frame_idx=event.frame_idx,
                            timestamp=event.timestamp,
                            details_json=json.dumps(event.details, ensure_ascii=False),
                            vehicle_data_json=json.dumps(event.vehicle_data, ensure_ascii=False),
                            snapshot_path=event.snapshot_path
                        )
                        self.async_writer.enqueue_event(event_record)

            if frame_idx % self.log_density_every == 0:
                density_stats = self.density_analyzer.get_statistics(active_vehicles)

                if self.async_writer:
                    for lane_id, segments in density_stats.get('lanes', {}).items():
                        for seg in segments:
                            density_record = DensityRecord(
                                frame_idx=frame_idx,
                                timestamp=time.time(),
                                lane_id=lane_id,
                                segment_id=seg['segment_id'],
                                vehicle_count=seg['vehicle_count'],
                                density_vpkpl=seg['density_vpkpl'],
                                avg_speed_kmh=seg['avg_speed_kmh'],
                                los_level=seg['los']
                            )
                            self.async_writer.enqueue_density(density_record)

            frame_stats = self.statistics_collector.collect_frame(
                frame_idx=frame_idx,
                active_vehicles=active_vehicles,
                total_detected=len(self.vehicle_manager.vehicles),
                events_count=len(frame_events)
            )

            if self.statistics_collector.should_generate_report(frame_idx):
                report = self.statistics_collector.generate_report()
                logger.info(f"\U0001f4ca تقرير دوري (إطار {frame_idx}): "
                           f"مركبات={report['total_vehicles']}, "
                           f"أحداث={report['total_events']}, "
                           f"FPS={report['processing_fps']:.1f}")

            if frame_idx % self.log_vehicles_every == 0 and self.async_writer:
                vehicle_records = []
                for v in active_vehicles:
                    pos = v.get_current_world_position()
                    record = VehicleRecord(
                        track_id=v.id,
                        class_name=v.cls,
                        frame_idx=frame_idx,
                        timestamp=time.time(),
                        world_x=pos[0] if pos else None,
                        world_y=pos[1] if pos else None,
                        speed_kmh=v.speed_kmh,
                        direction=v.direction,
                        lane_id=v.lane_id
                    )
                    vehicle_records.append(record)

                    self.csv_writer.write_row("daily_stats", [
                        time.strftime("%Y-%m-%d %H:%M:%S"),
                        frame_idx, v.id, v.cls,
                        round(v.speed_kmh, 2) if v.speed_kmh else "",
                        v.direction, v.lane_id, ""
                    ])

                if vehicle_records:
                    self.async_writer.enqueue_vehicles_batch(vehicle_records)

            annotated = frame.copy()

            if hasattr(self.bev, 'src_points'):
                self.renderer.draw_roi(annotated, self.bev.src_points)

            if self.show_gates:
                for gate_id, gate in self.gate_manager.gates.items():
                    p1_img = self.bev.world_to_image(
                        gate.line_world[0][0], gate.line_world[0][1]
                    )
                    p2_img = self.bev.world_to_image(
                        gate.line_world[1][0], gate.line_world[1][1]
                    )
                    self.renderer.draw_gate(
                        annotated, gate_id, (p1_img, p2_img),
                        len(gate.crossings)
                    )

            for det in detections:
                vehicle = self.vehicle_manager.get_vehicle(det['track_id'])
                if vehicle:
                    is_violating = any(e.track_id == vehicle.id for e in frame_events)
                    is_stopped = vehicle.direction == "Stationary"

                    self.renderer.draw_vehicle_box(
                        annotated,
                        det['bbox'],
                        vehicle.id,
                        vehicle.cls,
                        vehicle.speed_kmh,
                        vehicle.direction,
                        vehicle.lane_id,
                        is_violating=is_violating,
                        is_stopped=is_stopped
                    )

            y_offset = 100
            for event in frame_events[-5:]:
                self.renderer.draw_event_alert(
                    annotated, event.event_type, event.track_id,
                    (annotated.shape[1] - 400, y_offset)
                )
                y_offset += 35

            if self.show_dashboard:
                lanes_los = {}
                if hasattr(self.density_analyzer, '_last_results'):
                    for lid, segs in self.density_analyzer._last_results.items():
                        if segs:
                            worst = max(segs, key=lambda s:
                                       ["A","B","C","D","E","F"].index(s.los_level))
                            lanes_los[lid] = worst.los_level

                db_stats = self.async_writer.get_stats() if self.async_writer else None

                annotated = self.dashboard.draw(
                    annotated,
                    frame_idx=frame_idx,
                    active_vehicles_count=len(active_vehicles),
                    total_detected=len(self.vehicle_manager.vehicles),
                    avg_speed=frame_stats.avg_speed_kmh,
                    events=[e.to_dict() for e in frame_events],
                    lanes_los=lanes_los,
                    db_stats=db_stats
                )

            if self.show_display:
                cv2.imshow("Vehicle Tracker Pro++", annotated)

            if self.video_writer:
                self.video_writer.write(annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                logger.info("تم إيقاف المعالجة يدوياً")
                break

        self._cleanup(cap, frame_idx, start_time)

    def _cleanup(self, cap, frame_idx, start_time):
        elapsed = time.time() - start_time
        logger.info("="*60)
        logger.info("جاري إنهاء الجلسة...")

        report = self.statistics_collector.generate_report()
        logger.info(f"إطارات معالجة: {frame_idx}")
        logger.info(f"الوقت المنقضي: {elapsed:.1f}s")
        logger.info(f"متوسط FPS: {report['processing_fps']:.1f}")
        logger.info(f"إجمالي المركبات: {report['total_vehicles']}")
        logger.info(f"إجمالي الأحداث: {report['total_events']}")
        logger.info(f"أقصى سرعة مسجلة: {report['max_recorded_speed']:.1f} km/h")

        if self.async_writer:
            self.async_writer.stop()

        self.db_manager.end_session(
            self.session_id,
            total_frames=frame_idx,
            total_vehicles=report['total_vehicles'],
            total_events=report['total_events'],
            max_speed=report['max_recorded_speed']
        )

        self.csv_writer.close_all()
        self.db_manager.close()

        cap.release()
        if self.video_writer:
            self.video_writer.release()
        cv2.destroyAllWindows()

        logger.info("تم إنهاء جميع الموارد بنجاح")
        logger.info("="*60)

    def _signal_handler(self, signum, frame):
        logger.info(f"استقبلت إشارة {signum}، جاري الإنهاء الآمن...")
        self._should_stop = True

    def run_headless(self):
        self.show_display = False
        self.show_dashboard = False
        self.process_video()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vehicle Tracker Pro++")
    parser.add_argument("--config", "-c", default="config.json",
                       help="مسار ملف الإعدادات")
    parser.add_argument("--headless", action="store_true",
                       help="تشغيل بدون عرض مرئي")
    parser.add_argument("--output", "-o",
                       help="مسار حفظ الفيديو الناتج")

    args = parser.parse_args()

    tracker = ProPlusTracker(config_path=args.config)

    if args.output:
        tracker.output_video_path = args.output

    if args.headless:
        tracker.run_headless()
    else:
        tracker.process_video()
