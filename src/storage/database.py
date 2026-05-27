import sqlite3
import json
import time
import queue
import threading
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class VehicleRecord:
    track_id: int
    class_name: str
    frame_idx: int
    timestamp: float
    world_x: Optional[float]
    world_y: Optional[float]
    speed_kmh: Optional[float]
    direction: Optional[str]
    lane_id: Optional[int]
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "frame_idx": self.frame_idx,
            "timestamp": self.timestamp,
            "world_x": round(self.world_x, 3) if self.world_x else None,
            "world_y": round(self.world_y, 3) if self.world_y else None,
            "speed_kmh": round(self.speed_kmh, 2) if self.speed_kmh else None,
            "direction": self.direction,
            "lane_id": self.lane_id,
            "is_active": self.is_active
        }


@dataclass
class EventRecord:
    event_type: str
    track_id: int
    severity: str
    frame_idx: int
    timestamp: float
    details_json: str
    vehicle_data_json: str
    snapshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "track_id": self.track_id,
            "severity": self.severity,
            "frame_idx": self.frame_idx,
            "timestamp": self.timestamp,
            "details": self.details_json,
            "vehicle_data": self.vehicle_data_json,
            "snapshot_path": self.snapshot_path
        }


@dataclass
class DensityRecord:
    frame_idx: int
    timestamp: float
    lane_id: int
    segment_id: int
    vehicle_count: int
    density_vpkpl: float
    avg_speed_kmh: float
    los_level: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_idx": self.frame_idx,
            "timestamp": self.timestamp,
            "lane_id": self.lane_id,
            "segment_id": self.segment_id,
            "vehicle_count": self.vehicle_count,
            "density_vpkpl": self.density_vpkpl,
            "avg_speed_kmh": self.avg_speed_kmh,
            "los_level": self.los_level
        }


class DatabaseManager:

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "data/traffic.db"):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

        logger.info(f"قاعدة البيانات جاهزة: {self.db_path}")

    def _connect(self):
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                source TEXT,
                total_frames INTEGER DEFAULT 0,
                total_vehicles INTEGER DEFAULT 0,
                total_events INTEGER DEFAULT 0,
                max_speed_kmh REAL DEFAULT 0.0,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                track_id INTEGER NOT NULL,
                class_name TEXT NOT NULL,
                frame_idx INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                world_x REAL,
                world_y REAL,
                speed_kmh REAL,
                direction TEXT,
                lane_id INTEGER,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_vehicles_track_id
            ON vehicles(track_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_vehicles_frame
            ON vehicles(frame_idx)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_vehicles_session
            ON vehicles(session_id)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                event_type TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                frame_idx INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                details_json TEXT,
                vehicle_data_json TEXT,
                snapshot_path TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_severity
            ON events(severity)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS density (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                frame_idx INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                lane_id INTEGER NOT NULL,
                segment_id INTEGER NOT NULL,
                vehicle_count INTEGER DEFAULT 0,
                density_vpkpl REAL DEFAULT 0.0,
                avg_speed_kmh REAL DEFAULT 0.0,
                los_level TEXT DEFAULT 'A',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_density_lane_segment
            ON density(lane_id, segment_id)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                date TEXT NOT NULL,
                hour INTEGER,
                total_vehicles INTEGER DEFAULT 0,
                total_events INTEGER DEFAULT 0,
                avg_speed_kmh REAL DEFAULT 0.0,
                max_speed_kmh REAL DEFAULT 0.0,
                peak_los TEXT,
                cars_count INTEGER DEFAULT 0,
                trucks_count INTEGER DEFAULT 0,
                motorcycles_count INTEGER DEFAULT 0,
                buses_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_info (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now')),
                description TEXT
            )
        ''')

        cursor.execute(
            "INSERT OR IGNORE INTO schema_info (version, description) VALUES (?, ?)",
            (self.SCHEMA_VERSION, "Initial schema with vehicles, events, density, statistics")
        )

        self.conn.commit()
        logger.info("تم إنشاء/التحقق من جداول قاعدة البيانات")

    def start_session(self, source: str = "", notes: str = "") -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (start_time, source, notes) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), source, notes)
        )
        self.conn.commit()
        session_id = cursor.lastrowid
        logger.info(f"بدأت الجلسة #{session_id}")
        return session_id

    def end_session(self, session_id: int, total_frames: int = 0,
                    total_vehicles: int = 0, total_events: int = 0,
                    max_speed: float = 0.0):
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE sessions
               SET end_time = ?, total_frames = ?, total_vehicles = ?,
                   total_events = ?, max_speed_kmh = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), total_frames, total_vehicles,
             total_events, max_speed, session_id)
        )
        self.conn.commit()
        logger.info(f"أنهيت الجلسة #{session_id}")

    def insert_vehicle(self, session_id: int, record: VehicleRecord):
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO vehicles
               (session_id, track_id, class_name, frame_idx, timestamp,
                world_x, world_y, speed_kmh, direction, lane_id, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, record.track_id, record.class_name, record.frame_idx,
             record.timestamp, record.world_x, record.world_y,
             record.speed_kmh, record.direction, record.lane_id,
             1 if record.is_active else 0)
        )
        self.conn.commit()

    def insert_vehicles_batch(self, session_id: int, records: List[VehicleRecord]):
        cursor = self.conn.cursor()
        data = [
            (session_id, r.track_id, r.class_name, r.frame_idx, r.timestamp,
             r.world_x, r.world_y, r.speed_kmh, r.direction, r.lane_id,
             1 if r.is_active else 0)
            for r in records
        ]
        cursor.executemany(
            """INSERT INTO vehicles
               (session_id, track_id, class_name, frame_idx, timestamp,
                world_x, world_y, speed_kmh, direction, lane_id, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data
        )
        self.conn.commit()

    def insert_event(self, session_id: int, record: EventRecord):
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO events
               (session_id, event_type, track_id, severity, frame_idx,
                timestamp, details_json, vehicle_data_json, snapshot_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, record.event_type, record.track_id, record.severity,
             record.frame_idx, record.timestamp, record.details_json,
             record.vehicle_data_json, record.snapshot_path)
        )
        self.conn.commit()

    def insert_events_batch(self, session_id: int, records: List[EventRecord]):
        cursor = self.conn.cursor()
        data = [
            (session_id, r.event_type, r.track_id, r.severity, r.frame_idx,
             r.timestamp, r.details_json, r.vehicle_data_json, r.snapshot_path)
            for r in records
        ]
        cursor.executemany(
            """INSERT INTO events
               (session_id, event_type, track_id, severity, frame_idx,
                timestamp, details_json, vehicle_data_json, snapshot_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data
        )
        self.conn.commit()

    def insert_density(self, session_id: int, record: DensityRecord):
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO density
               (session_id, frame_idx, timestamp, lane_id, segment_id,
                vehicle_count, density_vpkpl, avg_speed_kmh, los_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, record.frame_idx, record.timestamp, record.lane_id,
             record.segment_id, record.vehicle_count, record.density_vpkpl,
             record.avg_speed_kmh, record.los_level)
        )
        self.conn.commit()

    def insert_density_batch(self, session_id: int, records: List[DensityRecord]):
        cursor = self.conn.cursor()
        data = [
            (session_id, r.frame_idx, r.timestamp, r.lane_id, r.segment_id,
             r.vehicle_count, r.density_vpkpl, r.avg_speed_kmh, r.los_level)
            for r in records
        ]
        cursor.executemany(
            """INSERT INTO density
               (session_id, frame_idx, timestamp, lane_id, segment_id,
                vehicle_count, density_vpkpl, avg_speed_kmh, los_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data
        )
        self.conn.commit()

    def query_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (event_type, limit)
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_vehicle_speeds(self, track_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT frame_idx, speed_kmh, direction FROM vehicles WHERE track_id = ? ORDER BY frame_idx",
            (track_id,)
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_density_history(self, lane_id: int = None, limit: int = 100) -> List[Dict]:
        cursor = self.conn.cursor()
        if lane_id is not None:
            cursor.execute(
                "SELECT * FROM density WHERE lane_id = ? ORDER BY timestamp DESC LIMIT ?",
                (lane_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM density ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_session_summary(self, session_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("تم إغلاق اتصال قاعدة البيانات")


DB_INSERT_VEHICLE = "insert_vehicle"
DB_INSERT_VEHICLES_BATCH = "insert_vehicles_batch"
DB_INSERT_EVENT = "insert_event"
DB_INSERT_EVENTS_BATCH = "insert_events_batch"
DB_INSERT_DENSITY = "insert_density"
DB_INSERT_DENSITY_BATCH = "insert_density_batch"
DB_FLUSH = "flush"
DB_STOP = "stop"


class AsyncDatabaseWriter:

    def __init__(self, db_manager: DatabaseManager, session_id: int,
                 batch_size: int = 50, flush_interval_s: float = 2.0):
        self.db = db_manager
        self.session_id = session_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval_s

        self._queue: queue.Queue = queue.Queue()

        self._vehicle_buffer: List[VehicleRecord] = []
        self._event_buffer: List[EventRecord] = []
        self._density_buffer: List[DensityRecord] = []

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_flush_time = time.time()

        self.vehicles_written = 0
        self.events_written = 0
        self.density_written = 0

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("بدأ خيط الكتابة غير المتزامن لقاعدة البيانات")

    def stop(self):
        if not self._running:
            return

        self._queue.put((DB_STOP, None))

        if self._thread:
            self._thread.join(timeout=5.0)

        self._running = False
        logger.info(f"توقف خيط الكتابة. تمت كتابة: "
                   f"{self.vehicles_written} مركبة, "
                   f"{self.events_written} حدث, "
                   f"{self.density_written} سجل كثافة")

    def enqueue_vehicle(self, record: VehicleRecord):
        self._queue.put((DB_INSERT_VEHICLE, record))

    def enqueue_event(self, record: EventRecord):
        self._queue.put((DB_INSERT_EVENT, record))

    def enqueue_density(self, record: DensityRecord):
        self._queue.put((DB_INSERT_DENSITY, record))

    def enqueue_vehicles_batch(self, records: List[VehicleRecord]):
        self._queue.put((DB_INSERT_VEHICLES_BATCH, records))

    def enqueue_events_batch(self, records: List[EventRecord]):
        self._queue.put((DB_INSERT_EVENTS_BATCH, records))

    def enqueue_density_batch(self, records: List[DensityRecord]):
        self._queue.put((DB_INSERT_DENSITY_BATCH, records))

    def flush(self):
        self._queue.put((DB_FLUSH, None))

    def _worker_loop(self):
        while self._running:
            try:
                try:
                    operation, data = self._queue.get(timeout=0.5)
                except queue.Empty:
                    self._check_auto_flush()
                    continue

                if operation == DB_STOP:
                    self._flush_all_buffers()
                    break

                if operation == DB_FLUSH:
                    self._flush_all_buffers()
                    continue

                self._process_operation(operation, data)

                total_buffered = (len(self._vehicle_buffer) +
                                 len(self._event_buffer) +
                                 len(self._density_buffer))
                if total_buffered >= self.batch_size:
                    self._flush_all_buffers()

            except Exception as e:
                logger.error(f"خطأ في خيط الكتابة: {e}")

    def _process_operation(self, operation: str, data):
        if operation == DB_INSERT_VEHICLE:
            self._vehicle_buffer.append(data)
        elif operation == DB_INSERT_VEHICLES_BATCH:
            self._vehicle_buffer.extend(data)
        elif operation == DB_INSERT_EVENT:
            self._event_buffer.append(data)
        elif operation == DB_INSERT_EVENTS_BATCH:
            self._event_buffer.extend(data)
        elif operation == DB_INSERT_DENSITY:
            self._density_buffer.append(data)
        elif operation == DB_INSERT_DENSITY_BATCH:
            self._density_buffer.extend(data)

    def _check_auto_flush(self):
        if time.time() - self._last_flush_time >= self.flush_interval:
            total_buffered = (len(self._vehicle_buffer) +
                             len(self._event_buffer) +
                             len(self._density_buffer))
            if total_buffered > 0:
                self._flush_all_buffers()

    def _flush_all_buffers(self):
        try:
            if self._vehicle_buffer:
                self.db.insert_vehicles_batch(self.session_id, self._vehicle_buffer)
                self.vehicles_written += len(self._vehicle_buffer)
                self._vehicle_buffer.clear()

            if self._event_buffer:
                self.db.insert_events_batch(self.session_id, self._event_buffer)
                self.events_written += len(self._event_buffer)
                self._event_buffer.clear()

            if self._density_buffer:
                self.db.insert_density_batch(self.session_id, self._density_buffer)
                self.density_written += len(self._density_buffer)
                self._density_buffer.clear()

            self._last_flush_time = time.time()

        except Exception as e:
            logger.error(f"خطأ في تفريغ المخازن: {e}")

    def get_stats(self) -> Dict[str, int]:
        return {
            "vehicles_written": self.vehicles_written,
            "events_written": self.events_written,
            "density_written": self.density_written,
            "buffered_vehicles": len(self._vehicle_buffer),
            "buffered_events": len(self._event_buffer),
            "buffered_density": len(self._density_buffer),
            "queue_size": self._queue.qsize()
        }
