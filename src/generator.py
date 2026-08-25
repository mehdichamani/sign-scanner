"""PDF Signature Sheets Generator Module."""
import os
import tempfile
from pathlib import Path
import pandas as pd
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.config import (
    PAGE_WIDTH,
    PAGE_HEIGHT,
    GRID_COLS,
    GRID_ROWS,
    MARGIN_X,
    MARGIN_Y,
    CELL_WIDTH,
    CELL_HEIGHT,
    BOX_WIDTH,
    BOX_HEIGHT,
    QR_SIZE,
    FONT_CANDIDATES,
    DEFAULT_CSV_PATH,
    DEFAULT_PDF_PATH,
)
from src.utils import fix_persian_text


def generate_qr(emp_code: str) -> str:
    """Generate a temporary QR code image for the given employee code."""
    qr = qrcode.QRCode(
        version=1,
        box_size=3,
        border=1,
    )
    qr.add_data(str(emp_code))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    img.save(temp_path)
    return temp_path


def get_persian_font(font_path: str = None) -> str:
    """Register and return available Persian font name."""
    candidates = [font_path] if font_path else []
    candidates.extend(FONT_CANDIDATES)

    for path in candidates:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("PersianFont", path))
                return "PersianFont"
            except Exception:
                continue

    return "Helvetica-Bold"


def generate_pdf(
    csv_path=DEFAULT_CSV_PATH,
    pdf_output=DEFAULT_PDF_PATH,
    font_path: str = None,
) -> str:
    """Generate PDF signature sheets from employee CSV file."""
    csv_path = Path(csv_path)
    pdf_output = Path(pdf_output)
    pdf_output.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    font_name = get_persian_font(font_path)

    c = canvas.Canvas(str(pdf_output), pagesize=A4)
    grouped = df.groupby("واحد", sort=False)

    current_row = 0
    current_col = 0
    total_boxes = 0

    for department_name, dept_df in grouped:
        if current_col != 0:
            current_col = 0
            current_row += 1

        if current_row >= GRID_ROWS:
            c.showPage()
            current_row = 0
            current_col = 0

        for _, item in dept_df.iterrows():
            emp_code = str(item.get("کد پرسنلی", ""))
            emp_name = str(item.get("نام کامل", ""))
            dept_str = str(department_name)

            cell_x = MARGIN_X + current_col * CELL_WIDTH
            cell_y = PAGE_HEIGHT - MARGIN_Y - (current_row + 1) * CELL_HEIGHT

            # 1. Dashed Border for cut lines
            c.setLineWidth(0.5)
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setDash(2, 2)
            c.rect(cell_x, cell_y, CELL_WIDTH, CELL_HEIGHT)
            c.setDash()

            # 2. QR Code
            qr_path = generate_qr(emp_code)
            try:
                c.drawImage(
                    qr_path,
                    cell_x + 2 * mm,
                    cell_y + CELL_HEIGHT - QR_SIZE - 1.5 * mm,
                    width=QR_SIZE,
                    height=QR_SIZE,
                )
            finally:
                if os.path.exists(qr_path):
                    os.remove(qr_path)

            # 3. Employee Info
            c.setFont(font_name, 7.5)
            c.setFillColorRGB(0.1, 0.1, 0.1)

            info_y = cell_y + CELL_HEIGHT - 4 * mm
            p_dept = fix_persian_text(f"واحد: {dept_str}")
            p_name = fix_persian_text(f"نام: {emp_name}")
            p_code = fix_persian_text(f"کد: {emp_code}")

            c.drawRightString(cell_x + CELL_WIDTH - 2 * mm, info_y, p_dept)
            c.drawRightString(cell_x + CELL_WIDTH - 2 * mm, info_y - 3.8 * mm, p_name)
            c.drawRightString(cell_x + CELL_WIDTH - 2 * mm, info_y - 7.6 * mm, p_code)

            # 4. Solid Signature Box
            box_x = cell_x + (CELL_WIDTH - BOX_WIDTH) / 2
            box_y = cell_y + 1.5 * mm

            c.setLineWidth(1.2)
            c.setStrokeColorRGB(0.1, 0.1, 0.1)
            c.rect(box_x, box_y, BOX_WIDTH, BOX_HEIGHT)

            total_boxes += 1
            current_col += 1
            if current_col >= GRID_COLS:
                current_col = 0
                current_row += 1

                if current_row >= GRID_ROWS:
                    c.showPage()
                    current_row = 0

    c.save()
    print(f"✅ برگه امضا با موفقیت تولید شد: {pdf_output} ({total_boxes} کادر)")
    return str(pdf_output)
