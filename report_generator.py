"""PDF Report Generator using fpdf2.

Generates styled PDF reports from SQL-aggregated data and JSON catalogs.
Artifacts are stored on disk; the database keeps only the file path.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fpdf import FPDF

import db

# Directory where report PDFs are stored
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportPDF(FPDF):
    """Styled PDF with header, footer, and helper methods for sections."""

    def __init__(self, title: str = "Report"):
        super().__init__()
        self._report_title = title
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, self._report_title, ln=True, align="C")
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generated {datetime.now().isoformat()} | Page {self.page_no()}", align="C")

    def section_title(self, text: str):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, text, ln=True)
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def table_row(self, cols: List[str], widths: List[int], bold: bool = False):
        self.set_font("Helvetica", "B" if bold else "", 10)
        self.set_text_color(50, 50, 50)
        for col, w in zip(cols, widths):
            self.cell(w, 8, str(col), border=1 if bold else "B", align="L")
        self.ln()


def _build_task_summary_pdf(report_id: int) -> str:
    """Generate a Task Summary PDF with SQL-aggregated statistics."""
    stats = db.get_stats()
    tasks = db.list_tasks()

    # Aggregate priority and category from existing task analysis data if any
    # For now, we'll do basic SQL-based stats and list all tasks
    pdf = ReportPDF(title="Task Summary Report")
    pdf.add_page()

    pdf.section_title("Overview")
    pdf.body_text(
        f"This report summarizes the current state of all tasks in the system.\n\n"
        f"Total tasks: {stats['total']}\n"
        f"Completed: {stats['done']}\n"
        f"Open: {stats['open']}"
    )

    pdf.section_title("Completion Rate")
    completion_pct = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
    pdf.body_text(f"{completion_pct:.1f}% of tasks are completed.")

    pdf.section_title("Task List")
    widths = [15, 120, 30]
    pdf.table_row(["ID", "Title", "Status"], widths, bold=True)
    for t in tasks:
        status = "Done" if t["done"] else "Open"
        pdf.table_row([str(t["id"]), t["title"], status], widths)

    file_path = REPORTS_DIR / f"task_summary_{report_id}.pdf"
    pdf.output(str(file_path))
    return str(file_path)


def _build_book_catalog_pdf(report_id: int) -> str:
    """Generate a Book Catalog PDF from the scraped books.json catalog."""
    books_path = Path("books.json")
    if not books_path.exists():
        raise FileNotFoundError("books.json not found. Run `python scraper.py` first.")

    with open(books_path, "r", encoding="utf-8") as f:
        books: List[Dict] = json.load(f)

    total = len(books)
    if total == 0:
        raise ValueError("books.json is empty.")

    # Compute aggregates
    prices = [b["price"] for b in books]
    ratings = [b["rating"] for b in books]
    avg_price = sum(prices) / total
    avg_rating = sum(ratings) / total
    min_price = min(prices)
    max_price = max(prices)

    # Rating distribution
    rating_counts: Dict[int, int] = {}
    for r in ratings:
        rating_counts[r] = rating_counts.get(r, 0) + 1

    pdf = ReportPDF(title="Book Catalog Report")
    pdf.add_page()

    pdf.section_title("Catalog Overview")
    pdf.body_text(
        f"Total books in catalog: {total}\n"
        f"Average price: £{avg_price:.2f}\n"
        f"Price range: £{min_price:.2f} – £{max_price:.2f}\n"
        f"Average rating: {avg_rating:.1f} / 5"
    )

    pdf.section_title("Rating Distribution")
    for star in range(1, 6):
        count = rating_counts.get(star, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 2)
        pdf.body_text(f"{star} star{'s' if star != 1 else ''}: {count:3d} ({pct:5.1f}%) {bar}")

    pdf.section_title("Top 15 Books")
    top_books = sorted(books, key=lambda b: b["rating"], reverse=True)[:15]
    widths = [70, 30, 25, 25, 35]
    pdf.table_row(["Title", "Price", "Rating", "Avail.", "Category"], widths, bold=True)
    for b in top_books:
        title = b["title"][:35] + "..." if len(b["title"]) > 35 else b["title"]
        avail = "In stock" if "in stock" in b["availability"].lower() else "Out"
        pdf.table_row(
            [title, f"£{b['price']:.2f}", str(b["rating"]), avail, b.get("category", "—")],
            widths,
        )

    file_path = REPORTS_DIR / f"book_catalog_{report_id}.pdf"
    pdf.output(str(file_path))
    return str(file_path)


REPORT_BUILDERS = {
    "task_summary": _build_task_summary_pdf,
    "book_catalog": _build_book_catalog_pdf,
}


def generate_report(report_id: int, report_type: str) -> str:
    """Generate a PDF report and return the file path.

    Args:
        report_id: The database report ID (used in filename).
        report_type: One of the keys in REPORT_BUILDERS.

    Returns:
        Absolute path to the generated PDF.

    Raises:
        ValueError: If report_type is unknown.
    """
    builder = REPORT_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unknown report type: {report_type}. Supported: {list(REPORT_BUILDERS.keys())}")
    return builder(report_id)
