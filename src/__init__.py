"""Sign Scanner Core Package."""
from src.generator import generate_pdf
from src.extractor import extract_signatures
from src.web_server import start_server

__all__ = ["generate_pdf", "extract_signatures", "start_server"]
