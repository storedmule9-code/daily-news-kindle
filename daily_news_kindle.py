#!/usr/bin/env python3
"""Fetch headlines from RSS feeds, build a PDF, and email it to your Kindle.

Runs unattended on GitHub Actions. Credentials come from environment variables.
"""

import datetime
import html
import os
import re
import smtplib
import sys
from email.message import EmailMessage

import feedparser
from fpdf import FPDF

# ---- Settings you may want to change -------------------------------------
FEEDS = {
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "The Guardian": "https://www.theguardian.com/world/rss",
}
ITEMS_PER_FEED = 10
SUMMARY_CHARS = 500
# --------------------------------------------------------------------------

# ---- Credentials (set as GitHub secrets) ----------------------------------
KINDLE_EMAIL = os.environ.get("KINDLE_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
# --------------------------------------------------------------------------


def clean(text: str) -> str:
    """Strip HTML and replace characters the built-in PDF font can't draw."""
    text = re.sub(r"<[^>]+>", "", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text.encode("latin-1", "replace").decode("latin-1")


def fetch_sections():
    """Return a list of (feed name, items). A failing feed is skipped, not fatal."""
    sections = []
    for name, url in FEEDS.items():
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # network or parser problems
            print(f"WARNING: could not read {name}: {exc}", file=sys.stderr)
            continue

        items = []
        for entry in parsed.entries[:ITEMS_PER_FEED]:
            items.append({
                "title": clean(entry.get("title", "Untitled")),
                "summary": clean(entry.get("summary", ""))[:SUMMARY_CHARS],
                "link": entry.get("link", ""),
            })

        if items:
            sections.append((name, items))
        else:
            print(f"WARNING: no items found for {name}", file=sys.stderr)
    return sections


def build_pdf(sections, today: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 14, clean(f"Daily News - {today}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for index, (section_name, items) in enumerate(sections):
        if index > 0:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, clean(section_name), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        for item in items:
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, item["title"], new_x="LMARGIN", new_y="NEXT")

            if item["summary"]:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 5, item["summary"], new_x="LMARGIN", new_y="NEXT")

            if item["link"]:
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 4, clean(item["link"]), new_x="LMARGIN", new_y="NEXT")

            pdf.ln(4)

    return bytes(pdf.output())


def send_to_kindle(pdf_bytes: bytes, today: str):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = KINDLE_EMAIL
    msg["Subject"] = f"Daily News {today}"
    msg.set_content("Your daily news digest is attached.")
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"Daily-News-{today}.pdf",
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)


def main():
    missing = [name for name, value in [
        ("KINDLE_EMAIL", KINDLE_EMAIL),
        ("SENDER_EMAIL", SENDER_EMAIL),
        ("SMTP_PASSWORD", SMTP_PASSWORD),
    ] if not value]
    if missing:
        sys.exit(f"Missing required settings: {', '.join(missing)}")

    today = datetime.date.today().strftime("%A, %B %d, %Y")
    sections = fetch_sections()
    if not sections:
        sys.exit("No headlines could be fetched from any feed. Nothing was sent.")

    pdf_bytes = build_pdf(sections, today)
    send_to_kindle(pdf_bytes, today)
    print(f"Sent daily news for {today} to {KINDLE_EMAIL}")


if __name__ == "__main__":
    main()
