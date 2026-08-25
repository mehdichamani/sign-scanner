"""Configuration and constants for the Sign Scanner application."""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# Project Root Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data & Output Directories
DATA_DIR = BASE_DIR / "data"
SCANS_DIR = BASE_DIR / "scans"
OUTPUT_DIR = BASE_DIR / "output"
SIGNATURES_OUTPUT_DIR = OUTPUT_DIR / "signatures"

DEFAULT_CSV_PATH = DATA_DIR / "employees.sample.csv"
DEFAULT_PDF_PATH = OUTPUT_DIR / "signature_sheets.pdf"

# PDF Sheet Layout Settings
PAGE_WIDTH, PAGE_HEIGHT = A4
GRID_COLS = 3
GRID_ROWS = 4

MARGIN_X = 6 * mm
MARGIN_Y = 8 * mm

CELL_WIDTH = (PAGE_WIDTH - 2 * MARGIN_X) / GRID_COLS
CELL_HEIGHT = (PAGE_HEIGHT - 2 * MARGIN_Y) / GRID_ROWS

HEADER_HEIGHT = 15 * mm
BOX_WIDTH = CELL_WIDTH - 8 * mm
BOX_HEIGHT = CELL_HEIGHT - HEADER_HEIGHT - 4 * mm
QR_SIZE = 13 * mm

# Font Settings
FONT_CANDIDATES = [
    "Vazirmatn-Regular.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "C:\\Windows\\Fonts\\arial.ttf"
]
