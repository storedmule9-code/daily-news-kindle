#!/usr/bin/env python3
"""The Daily Digest: a newspaper-style PDF emailed to your Kindle each morning.

Sections: France, Latin America, Middle East, Gangs, then Other Headlines.
Within each section, recent Guardian stories come first (standfirst and opening
paragraph), followed by short headlines from BBC, NPR and The Guardian RSS feeds.
"""

import datetime
import html
import json
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage

import feedparser
from fpdf import FPDF

# ---- Settings you may want to change -------------------------------------
RSS_FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NPR World": "https://feeds.npr.org/1004/rss.xml",
    "Guardian World": "https://www.theguardian.com/world/rss",
}
RSS_ITEMS_PER_FEED = 25     # headlines read from each feed
MAX_BRIEFS_PER_SECTION = 8  # short headlines shown per section
SUMMARY_CHARS = 350         # length of RSS excerpts
OPENING_CHARS = 700         # length of Guardian opening paragraph shown

# Stories are routed by "priority" (lowest first). A story goes into the first
# section whose pattern matches its headline or excerpt. Sections print in the
# order listed here.
SECTIONS = [
    {
        "name": "France",
        "priority": 1,
        "pattern": r"\b(france|french|paris|macron)",
        "guardian_query": "France",
        "guardian_section": "world",
        "guardian_stories": 2,
    },
    {
        "name": "Latin America",
        "priority": 2,
        # Any mention of Latin America or a Latin American country places a story here,
        # even if it also covers the US.
        "pattern": r"\b(latin america|latin american|latam|south america|central america|mexic|guatemal|belize|hondura|el salvador|salvadoran|salvadorean|nicaragu|costa rica|panam|cuba|dominican republic|haiti|colombia|venezuela|guyanese|ecuador|peru|bolivia|brazil|paraguay|uruguay|argentin|chile)",
        "guardian_query": '"Latin America" OR Mexico OR Guatemala OR Belize OR Honduras OR "El Salvador" OR Nicaragua OR "Costa Rica" OR Panama OR Cuba OR "Dominican Republic" OR Haiti OR Colombia OR Venezuela OR Ecuador OR Peru OR Bolivia OR Brazil OR Paraguay OR Uruguay OR Argentina OR Chile',
        "guardian_section": "world",
        "guardian_stories": 3,
    },
    {
        "name": "Middle East",
        "priority": 3,
        "pattern": r"\b(middle east|israel|gaza|palestin|iran|iraq|syria|lebanon|yemen|saudi|egypt|jordan|hezbollah|hamas|houthi)",
        "guardian_query": '"Middle East" OR Israel OR Gaza OR Iran',
        "guardian_section": "world",
        "guardian_stories": 2,
    },
    {
        "name": "Gangs",
        "priority": 0,   # checked first, so gang stories land here before regional sections
        "pattern": r"\b(street gangs?|gang violence|gang members?|gang leaders?|gang crime|gang wars?|gang-related|drug gangs?|drug cartels?|cartel violence|cartel (?:members?|leaders?|gunmen|killings?|bosses?)|ms-13|mara salvatrucha|tren de aragua|mafia)",
        "guardian_query": '"street gang" OR "gang violence" OR "gang members" OR "drug cartel" OR "cartel violence" OR "Tren de Aragua" OR MS-13',
        "guardian_section": None,
        "guardian_stories": 2,
    },
]
# --------------------------------------------------------------------------

# ---- Credentials (set as GitHub secrets) ----------------------------------
KINDLE_EMAIL = os.environ.get("KINDLE_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
# --------------------------------------------------------------------------

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_FILES = {
    ("Serif", ""): "DejaVuSerif.ttf",
    ("Serif", "B"): "DejaVuSerif-Bold.ttf",
    ("Sans", ""): "DejaVuSans.ttf",
    ("Sans", "B"): "DejaVuSans-Bold.ttf",
}


def clean(text: str) -> str:
    """Strip HTML tags, decode entities, and collapse whitespace."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int) -> str:
    """Shorten text at a word boundary."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


# ---- Content gathering -----------------------------------------------------

def fetch_guardian(query, section, count):
    """Return recent Guardian stories matching the query. Empty list if no key or on error."""
    if not GUARDIAN_API_KEY:
        return []

    params = {
        "q": query,
        "order-by": "newest",
        "page-size": str(count),
        "show-fields": "headline,trailText,bodyText,byline",
        "api-key": GUARDIAN_API_KEY,
    }
    if section:
        params["section"] = section
    url = "https://content.guardianapis.com/search?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:
        print(f"WARNING: Guardian request failed for '{query}': {exc}", file=sys.stderr)
        return []

    stories = []
    for result in data.get("response", {}).get("results", []):
        fields = result.get("fields", {})
        paragraphs = [clean(p) for p in fields.get("bodyText", "").split("\n") if p.strip()]
        stories.append({
            "title": clean(fields.get("headline") or result.get("webTitle", "Untitled")),
            "byline": clean(fields.get("byline", "")),
            "standfirst": clean(fields.get("trailText", "")),
            "opening": truncate(paragraphs[0], OPENING_CHARS) if paragraphs else "",
            "link": result.get("webUrl", ""),
        })
    return stories


def fetch_rss_items():
    items = []
    for name, url in RSS_FEEDS.items():
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            print(f"WARNING: could not read {name}: {exc}", file=sys.stderr)
            continue
        for entry in parsed.entries[:RSS_ITEMS_PER_FEED]:
            items.append({
                "title": clean(entry.get("title", "Untitled")),
                "summary": truncate(clean(entry.get("summary", "")), SUMMARY_CHARS),
                "link": entry.get("link", ""),
                "source": name,
            })
    return items


def matches(spec, text):
    """True if text matches the section's pattern and not its exclusion pattern."""
    if not re.search(spec["pattern"], text):
        return False
    exclude = spec.get("exclude")
    if not exclude or re.search(spec.get("keep_if", "(?!)"), text):
        return True
    return not re.search(exclude, text)


def build_digest():
    """Return the sections to print, in order."""
    seen = set()
    layout = {spec["name"]: {"name": spec["name"], "pattern": spec["pattern"], "stories": [], "briefs": []}
              for spec in SECTIONS}
    by_priority = sorted(SECTIONS, key=lambda s: s["priority"])

    # Guardian stories: fetch in priority order, keep only stories whose headline,
    # standfirst or opening paragraph actually matches the section.
    for spec in by_priority:
        for story in fetch_guardian(spec["guardian_query"], spec["guardian_section"], spec["guardian_stories"]):
            if not story["link"] or story["link"] in seen:
                continue
            text = " ".join([story["title"], story["standfirst"], story["opening"]]).lower()
            if not matches(spec, text):
                continue
            seen.add(story["link"])
            layout[spec["name"]]["stories"].append(story)

    # RSS headlines: route by priority, anything unmatched goes to Other Headlines.
    other = {"name": "Other Headlines", "pattern": None, "stories": [], "briefs": []}
    for item in fetch_rss_items():
        if not item["link"] or item["link"] in seen:
            continue
        text = (item["title"] + " " + item["summary"]).lower()

        target = other
        for spec in by_priority:
            if matches(spec, text):
                target = layout[spec["name"]]
                break

        if len(target["briefs"]) >= MAX_BRIEFS_PER_SECTION:
            continue
        seen.add(item["link"])
        target["briefs"].append(item)

    # Print in the order listed in SECTIONS.
    ordered = [layout[spec["name"]] for spec in SECTIONS] + [other]
    return [s for s in ordered if s["stories"] or s["briefs"]]


# ---- PDF layout -----------------------------------------------------------

class Digest(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Sans", "", 7.5)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"- {self.page_no()} -", align="C")
        self.set_text_color(0, 0, 0)


def register_fonts(pdf):
    for (family, style), filename in FONT_FILES.items():
        path = os.path.join(FONT_DIR, filename)
        if not os.path.exists(path):
            sys.exit(f"Font not found: {path}. Install it with: sudo apt-get install fonts-dejavu-core")
        pdf.add_font(family, style, path)


def rule(pdf, weight, gap):
    y = pdf.get_y()
    pdf.set_line_width(weight)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_line_width(0.2)
    pdf.set_y(y + gap)


def masthead(pdf, today):
    pdf.set_font("Serif", "B", 28)
    pdf.cell(0, 13, "THE DAILY DIGEST", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 7.5)
    pdf.cell(0, 5, f"{today}   |   MORNING EDITION", align="C", new_x="LMARGIN", new_y="NEXT")
    rule(pdf, 1.2, 1.2)
    rule(pdf, 0.3, 4)


def section_banner(pdf, name):
    pdf.ln(3)
    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 9, name.upper(), new_x="LMARGIN", new_y="NEXT")
    rule(pdf, 0.8, 3)


def guardian_story(pdf, story):
    pdf.set_font("Serif", "B", 13.5)
    pdf.multi_cell(0, 6.2, story["title"], new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Sans", "", 7.5)
    pdf.set_text_color(90, 90, 90)
    credit = "The Guardian" + (f"   |   By {story['byline']}" if story["byline"] else "")
    pdf.multi_cell(0, 4.5, credit, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)

    if story["standfirst"]:
        pdf.set_font("Serif", "B", 10.5)
        pdf.multi_cell(0, 5.3, story["standfirst"], align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    if story["opening"]:
        pdf.set_font("Serif", "", 10.5)
        pdf.multi_cell(0, 5.3, story["opening"], align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    pdf.set_font("Sans", "", 6.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 3.8, f"Read the full story: {story['link']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    rule(pdf, 0.2, 4)


def brief_item(pdf, item):
    pdf.set_font("Serif", "B", 11)
    pdf.multi_cell(0, 5.2, item["title"], new_x="LMARGIN", new_y="NEXT")
    if item["summary"]:
        pdf.set_font("Serif", "", 9.5)
        pdf.multi_cell(0, 4.8, item["summary"], align="J", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 6.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 3.6, f"{item['source']}   |   {item['link']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def build_pdf(sections, today: str) -> bytes:
    # A 6 x 9 inch page suits the Kindle screen better than standard A4.
    pdf = Digest(format=(152, 229))
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=16)
    register_fonts(pdf)
    pdf.add_page()

    masthead(pdf, today)

    for section in sections:
        section_banner(pdf, section["name"])
        for story in section["stories"]:
            guardian_story(pdf, story)
        for item in section["briefs"]:
            brief_item(pdf, item)

    return bytes(pdf.output())


# ---- Delivery ---------------------------------------------------------------

def send_to_kindle(pdf_bytes: bytes, today: str):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = KINDLE_EMAIL
    msg["Subject"] = f"The Daily Digest {today}"
    msg.set_content("Your morning edition is attached.")
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"Daily-Digest-{today}.pdf",
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

    if not GUARDIAN_API_KEY:
        print("Note: GUARDIAN_API_KEY not set. Sending headlines only, without Guardian stories.")

    today = datetime.date.today().strftime("%A, %B %d, %Y")
    sections = build_digest()
    if not sections:
        sys.exit("No stories could be fetched. Nothing was sent.")

    pdf_bytes = build_pdf(sections, today)
    send_to_kindle(pdf_bytes, today)
    count = sum(len(s["stories"]) + len(s["briefs"]) for s in sections)
    print(f"Sent The Daily Digest for {today} ({count} stories) to {KINDLE_EMAIL}")


if __name__ == "__main__":
    main()
