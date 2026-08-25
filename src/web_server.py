"""Lightweight Web Server for Sign Scanner Interactive Web Application."""
import os
import sys
import json
import base64
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import pandas as pd
import cv2
import numpy as np

from src.config import (
    BASE_DIR,
    DATA_DIR,
    SCANS_DIR,
    OUTPUT_DIR,
    SIGNATURES_OUTPUT_DIR,
    DEFAULT_CSV_PATH,
    DEFAULT_PDF_PATH,
)
from src.extractor import extract_qr_codes, find_signature_boxes, remove_background
from src.generator import generate_pdf

WEB_STATIC_DIR = Path(__file__).parent / "web"


class SignScannerHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_STATIC_DIR), **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/scans":
            valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
            files = []
            if SCANS_DIR.exists():
                for f in sorted(os.listdir(SCANS_DIR)):
                    if f.lower().endswith(valid_exts):
                        fp = SCANS_DIR / f
                        files.append({
                            "name": f,
                            "size": fp.stat().st_size,
                            "modified": fp.stat().st_mtime
                        })
            self._send_json({"scans": files, "scansDir": str(SCANS_DIR.resolve())})
            return

        elif path == "/api/signatures":
            sig_files = []
            if SIGNATURES_OUTPUT_DIR.exists():
                for f in sorted(SIGNATURES_OUTPUT_DIR.glob("*.png")):
                    sig_files.append({
                        "name": f.name,
                        "empCode": f.stem,
                        "size": f.stat().st_size
                    })
            self._send_json({"signatures": sig_files, "outputDir": str(SIGNATURES_OUTPUT_DIR.resolve())})
            return

        elif path == "/api/scan-image":
            filename = params.get("file", [""])[0]
            if not filename:
                self.send_error(400, "Missing filename")
                return
            safe_path = (SCANS_DIR / filename).resolve()
            if not str(safe_path).startswith(str(SCANS_DIR.resolve())) or not safe_path.exists():
                self.send_error(404, "File not found")
                return
            
            ext = safe_path.suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            with open(safe_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/api/signature-image":
            filename = params.get("file", [""])[0]
            if not filename:
                self.send_error(400, "Missing filename")
                return
            safe_path = (SIGNATURES_OUTPUT_DIR / filename).resolve()
            if not str(safe_path).startswith(str(SIGNATURES_OUTPUT_DIR.resolve())) or not safe_path.exists():
                self.send_error(404, "File not found")
                return
            with open(safe_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/api/employees-data":
            # Load default CSV or custom
            csv_file = DATA_DIR / "employees.sample.csv"
            records = []
            columns = ["کد پرسنلی", "نام کامل", "واحد"]
            if csv_file.exists():
                try:
                    df = pd.read_csv(csv_file)
                    # Normalize columns if missing
                    for col in ["کد پرسنلی", "نام کامل", "واحد"]:
                        if col not in df.columns:
                            df[col] = ""
                    for _, row in df.iterrows():
                        records.append({
                            "empCode": str(row.get("کد پرسنلی", "")).strip(),
                            "name": str(row.get("نام کامل", "")).strip(),
                            "dept": str(row.get("واحد", "")).strip(),
                        })
                except Exception as e:
                    self._send_json({"error": f"خطا در خواندن فایل CSV: {str(e)}"}, 500)
                    return

            self._send_json({
                "employees": records,
                "csvPath": str(csv_file.resolve()),
                "total": len(records)
            })
            return

        elif path == "/api/download-pdf":
            pdf_path = DEFAULT_PDF_PATH
            if not pdf_path.exists():
                self.send_error(404, "PDF file not generated yet")
                return
            with open(pdf_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", 'inline; filename="signature_sheets.pdf"')
            self.end_headers()
            self.wfile.write(content)
            return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            req_json = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            req_json = {}

        if path == "/api/detect":
            filename = req_json.get("filename")
            if not filename:
                self._send_json({"error": "نام فایل اسکن مشخص نشده است"}, 400)
                return

            img_path = SCANS_DIR / filename
            if not img_path.exists():
                self._send_json({"error": f"فایل {filename} یافت نشد"}, 404)
                return

            img = cv2.imread(str(img_path))
            if img is None:
                self._send_json({"error": "عدم امکان باز کردن فایل تصویر"}, 500)
                return

            h_img, w_img = img.shape[:2]

            # Detect QR codes
            qr_list = extract_qr_codes(img)
            # Detect contours
            boxes = find_signature_boxes(img)

            items = []
            assigned_boxes = set()

            # Match QR codes to nearest box or geometry
            for idx, q in enumerate(qr_list):
                code = q["code"]
                qx, qy, qw, qh = q["qr_rect"]

                best_box = None
                min_dist = float("inf")

                for b_idx, (bx, by, bw, bh) in enumerate(boxes):
                    if b_idx in assigned_boxes:
                        continue
                    dx = abs((bx + bw / 2) - (qx + qw * 2.5))
                    dy = by - (qy + qh)
                    if -30 <= dy <= qh * 4 and abs(bx - qx) < qw * 5:
                        dist = abs(dx) + abs(dy)
                        if dist < min_dist:
                            min_dist = dist
                            best_box = (bx, by, bw, bh)
                            best_b_idx = b_idx

                if best_box is not None:
                    assigned_boxes.add(best_b_idx)
                    bx, by, bw, bh = best_box
                    matched_type = "box_contour"
                else:
                    matched_type = "geometry_fallback"
                    bx = max(0, qx + int(qw * 0.1))
                    by = int(qy + qh * 1.35)
                    bw = int(qw * 4.8)
                    bh = int(qh * 4.3)
                    bw = min(bw, w_img - bx)
                    bh = min(bh, h_img - by)

                items.append({
                    "id": f"item_{idx + 1}",
                    "empCode": code,
                    "qrRect": {"x": qx, "y": qy, "w": qw, "h": qh},
                    "cropRect": {"x": bx, "y": by, "w": bw, "h": bh},
                    "matchedType": matched_type,
                    "threshold": 200,
                    "padding": 6,
                    "confirmed": True
                })

            # Check remaining unassigned boxes
            unassigned_count = 0
            for b_idx, (bx, by, bw, bh) in enumerate(boxes):
                if b_idx not in assigned_boxes:
                    unassigned_count += 1
                    items.append({
                        "id": f"extra_{unassigned_count}",
                        "empCode": f"UNKNOWN_{unassigned_count}",
                        "qrRect": None,
                        "cropRect": {"x": bx, "y": by, "w": bw, "h": bh},
                        "matchedType": "unassigned_box",
                        "threshold": 200,
                        "padding": 6,
                        "confirmed": False
                    })

            self._send_json({
                "filename": filename,
                "imageWidth": w_img,
                "imageHeight": h_img,
                "items": items,
                "totalQrFound": len(qr_list),
                "totalBoxesFound": len(boxes)
            })
            return

        elif path == "/api/preview-crop":
            filename = req_json.get("filename")
            rect = req_json.get("rect", {})
            thresh_val = int(req_json.get("threshold", 200))
            pad = int(req_json.get("padding", 6))

            if not filename or not rect:
                self._send_json({"error": "پارامترهای درخواست ناقص است"}, 400)
                return

            img_path = SCANS_DIR / filename
            if not img_path.exists():
                self._send_json({"error": "فایل اسکن پیدا نشد"}, 404)
                return

            img = cv2.imread(str(img_path))
            if img is None:
                self._send_json({"error": "خطا در بارگذاری تصویر"}, 500)
                return

            h_img, w_img = img.shape[:2]
            x = int(rect.get("x", 0))
            y = int(rect.get("y", 0))
            w = int(rect.get("w", 50))
            h = int(rect.get("h", 50))

            crop_x1 = max(0, x + pad)
            crop_y1 = max(0, y + pad)
            crop_x2 = min(w_img, x + w - pad)
            crop_y2 = min(h_img, y + h - pad)

            if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
                self._send_json({"error": "اندازه کادر نامعتبر است"}, 400)
                return

            raw_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
            transparent = remove_background(raw_crop, thresh_val=thresh_val)

            # Encode both raw and transparent to base64
            _, raw_buf = cv2.imencode(".jpg", raw_crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
            raw_b64 = base64.b64encode(raw_buf).decode("utf-8")

            _, trans_buf = cv2.imencode(".png", transparent)
            trans_b64 = base64.b64encode(trans_buf).decode("utf-8")

            self._send_json({
                "rawImage": f"data:image/jpeg;base64,{raw_b64}",
                "transparentImage": f"data:image/png;base64,{trans_b64}",
                "dimensions": {
                    "width": crop_x2 - crop_x1,
                    "height": crop_y2 - crop_y1
                }
            })
            return

        elif path == "/api/save-signatures":
            filename = req_json.get("filename")
            items = req_json.get("items", [])

            if not filename or not items:
                self._send_json({"error": "لیست امضاها یا نام فایل خالی است"}, 400)
                return

            img_path = SCANS_DIR / filename
            if not img_path.exists():
                self._send_json({"error": "فایل اسکن یافت نشد"}, 404)
                return

            img = cv2.imread(str(img_path))
            if img is None:
                self._send_json({"error": "خطا در خواندن فایل تصویر"}, 500)
                return

            h_img, w_img = img.shape[:2]
            out_dir = SIGNATURES_OUTPUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)

            saved_results = []
            for item in items:
                emp_code = str(item.get("empCode", "")).strip()
                if not emp_code:
                    continue

                rect = item.get("cropRect", {})
                pad = int(item.get("padding", 6))
                thresh_val = int(item.get("threshold", 200))

                x = int(rect.get("x", 0))
                y = int(rect.get("y", 0))
                w = int(rect.get("w", 0))
                h = int(rect.get("h", 0))

                crop_x1 = max(0, x + pad)
                crop_y1 = max(0, y + pad)
                crop_x2 = min(w_img, x + w - pad)
                crop_y2 = min(h_img, y + h - pad)

                if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
                    continue

                sig_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
                transparent_sig = remove_background(sig_crop, thresh_val=thresh_val)

                # Clean filename
                safe_code = "".join(c for c in emp_code if c.isalnum() or c in ("-", "_")).strip()
                if not safe_code:
                    safe_code = "signature"

                out_file = out_dir / f"{safe_code}.png"
                cv2.imwrite(str(out_file), transparent_sig)

                saved_results.append({
                    "empCode": safe_code,
                    "filename": f"{safe_code}.png",
                    "path": str(out_file)
                })

            self._send_json({
                "success": True,
                "savedCount": len(saved_results),
                "savedSignatures": saved_results,
                "outputDir": str(out_dir.resolve())
            })
            return

        elif path == "/api/generate-pdf":
            employees = req_json.get("employees", None)
            
            try:
                # If custom employee list was sent from the web UI, write to a temporary CSV or overwrite
                if employees and isinstance(employees, list) and len(employees) > 0:
                    df = pd.DataFrame([
                        {
                            "کد پرسنلی": str(e.get("empCode", "")).strip(),
                            "نام کامل": str(e.get("name", "")).strip(),
                            "واحد": str(e.get("dept", "")).strip(),
                        }
                        for e in employees
                        if str(e.get("empCode", "")).strip()
                    ])
                    temp_csv = DATA_DIR / "web_generated_employees.csv"
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    df.to_csv(temp_csv, index=False, encoding="utf-8-sig")
                    out = generate_pdf(csv_path=temp_csv)
                else:
                    out = generate_pdf()
                
                self._send_json({
                    "success": True,
                    "outputPdf": str(out),
                    "downloadUrl": "/api/download-pdf"
                })
            except Exception as e:
                self._send_json({"error": f"خطا در تولید PDF: {str(e)}"}, 500)
            return

        elif path == "/api/upload-csv":
            content = req_json.get("content", "")
            if not content:
                self._send_json({"error": "محتوای فایل CSV خالی است"}, 400)
                return

            try:
                import io
                df = pd.read_csv(io.StringIO(content))
                records = []
                for _, row in df.iterrows():
                    emp_code = ""
                    for col in ["کد پرسنلی", "کد", "code", "empCode", "employee_id"]:
                        if col in df.columns:
                            emp_code = str(row[col]).strip()
                            break
                    if not emp_code and len(row) > 0:
                        emp_code = str(row.iloc[0]).strip()

                    emp_name = ""
                    for col in ["نام کامل", "نام", "name", "full_name"]:
                        if col in df.columns:
                            emp_name = str(row[col]).strip()
                            break
                    if not emp_name and len(row) > 1:
                        emp_name = str(row.iloc[1]).strip()

                    dept = ""
                    for col in ["واحد", "بخش", "دپارتمان", "department", "dept"]:
                        if col in df.columns:
                            dept = str(row[col]).strip()
                            break
                    if not dept and len(row) > 2:
                        dept = str(row.iloc[2]).strip()

                    if emp_code:
                        records.append({
                            "empCode": emp_code,
                            "name": emp_name,
                            "dept": dept or "عمومی"
                        })

                self._send_json({
                    "success": True,
                    "employees": records,
                    "total": len(records)
                })
            except Exception as e:
                self._send_json({"error": f"خطا در پردازش فایل CSV: {str(e)}"}, 400)
            return

        self.send_error(404, "Endpoint not found")


def start_server(port=8080, open_browser=True):
    """Start the Sign Scanner Web Application Server."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, SignScannerHTTPHandler)
    url = f"http://localhost:{port}"
    print("=" * 60)
    print(f"🚀 سامانه هوشمند Sign Scanner آماده به کار است")
    print(f"🔗 آدرس پنل وب: {url}")
    print(f"برای خروج از برنامه، کلید Ctrl+C را فشار دهید.")
    print("=" * 60 + "\n")

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nوب‌سرور با موفقیت متوقف شد.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_server(port=port)
