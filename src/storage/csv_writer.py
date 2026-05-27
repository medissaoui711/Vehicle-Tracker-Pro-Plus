import csv
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class CSVWriter:

    def __init__(self, csv_dir: str = "data/reports"):
        self.csv_dir = Path(csv_dir)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        self._files: Dict[str, tuple] = {}

    def open_file(self, name: str, headers: List[str], suffix: str = "") -> str:
        if suffix:
            filename = f"{name}_{suffix}.csv"
        else:
            date_str = time.strftime("%Y%m%d")
            filename = f"{name}_{date_str}.csv"

        filepath = self.csv_dir / filename

        f = open(filepath, 'a', newline='', encoding='utf-8')
        writer = csv.writer(f)

        if os.stat(filepath).st_size == 0:
            writer.writerow(headers)
            f.flush()

        self._files[name] = (f, writer)

        logger.info(f"فتح ملف CSV: {filepath}")
        return str(filepath)

    def write_row(self, name: str, row: List[Any]):
        if name not in self._files:
            logger.warning(f"ملف CSV غير مفتوح: {name}")
            return

        f, writer = self._files[name]
        writer.writerow(row)
        f.flush()

    def write_rows(self, name: str, rows: List[List[Any]]):
        if name not in self._files:
            logger.warning(f"ملف CSV غير مفتوح: {name}")
            return

        f, writer = self._files[name]
        writer.writerows(rows)
        f.flush()

    def close_file(self, name: str):
        if name in self._files:
            f, _ = self._files[name]
            f.close()
            del self._files[name]
            logger.info(f"إغلاق ملف CSV: {name}")

    def close_all(self):
        for name in list(self._files.keys()):
            self.close_file(name)
