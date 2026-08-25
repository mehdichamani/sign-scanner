"""Main Entrypoint for Sign Scanner (Web Application)."""
import sys
import argparse
from src.web_server import start_server


def main():
    parser = argparse.ArgumentParser(
        description="سامانه هوشمند تولید برگه و استخراج امضا (Sign Scanner Pro)"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="پورت وب‌سرور (پیش‌فرض: 8080)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="عدم باز کردن خودکار مرورگر"
    )

    args = parser.parse_args()

    try:
        start_server(port=args.port, open_browser=not args.no_browser)
    except (KeyboardInterrupt, EOFError):
        print("\nبرنامه پایان یافت.")
        sys.exit(0)


if __name__ == "__main__":
    main()
