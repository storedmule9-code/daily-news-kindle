#!/usr/bin/env python3
"""The Daily Digest: a newspaper-style PDF emailed to your Kindle each morning.

Layout: Top Stories first, then France, Latin America, Middle East and Gangs.
A story shown under Top Stories is not repeated in a topic section.

Sources are prioritized: AP News first, then The Guardian, then BBC and NPR.
Guardian stories pulled from the Guardian API show their standfirst and opening
paragraph; everything else shows a short excerpt with a link.

Each run also writes the same digest as a web page (docs/index.html) and can
email it to you (set HTML_EMAIL_TO).
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
    # AP's own RSS feeds were discontinued in 2024. This is AP's official Flipboard
    # top stories feed; each item links to the story on apnews.com.
    "AP News": "https://flipboard.com/@associatedpress/top-stories-u7govdf1z.rss",
}
RSS_ITEMS_PER_FEED = 25     # headlines read from each feed
MAX_BRIEFS_PER_SECTION = 8  # short headlines shown per section
SUMMARY_CHARS = 350         # length of RSS excerpts
OPENING_CHARS = 700         # length of Guardian opening paragraph shown
TOP_SUMMARY_CHARS = 500     # length of excerpts under Top Stories

# Source priority, highest first: AP News, then The Guardian, then the rest.
SOURCE_ORDER = ["AP News", "Guardian World", "BBC World", "NPR World"]

# How many lead stories each source can contribute to Top Stories, in priority order.
TOP_PER_SOURCE = {"AP News": 4, "Guardian World": 3, "BBC World": 2, "NPR World": 1}

# Show an "Other Headlines" section at the end for stories that fit no topic.
INCLUDE_OTHER_HEADLINES = False

DISPLAY_NAMES = {"AP News": "AP News", "Guardian World": "The Guardian",
                 "BBC World": "BBC News", "NPR World": "NPR"}

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
HTML_OUTPUT_PATH = os.environ.get("HTML_OUTPUT_PATH", "docs/index.html")
HTML_EMAIL_TO = os.environ.get("HTML_EMAIL_TO", "")   # optional: email the web edition here
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


STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "after", "over", "into", "amid",
    "says", "said", "say", "new", "will", "could", "would", "about", "been", "have", "has",
    "are", "was", "were", "but", "not", "its", "their", "than", "more", "most", "also",
    "out", "how", "why", "what", "who", "when", "year", "years", "week", "day", "news",
    "live", "update", "report", "reports",
}


def story_tokens(text):
    """Reduce a headline to a set of word stems, for spotting the same story across sources."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w[:5] for w in words if len(w) > 2 and w not in STOPWORDS}


def same_story(a, b):
    """True if two sets of headline stems are probably about the same story."""
    if not a or not b:
        return False
    shared = len(a & b)
    small = min(len(a), len(b))
    return (shared >= 3 and shared / small >= 0.5) or (shared >= 2 and shared / small >= 0.7)


def normalize_link(url):
    parts = urllib.parse.urlsplit((url or "").strip())
    return (parts.netloc + parts.path.rstrip("/")).lower()


def source_rank(name):
    return SOURCE_ORDER.index(name) if name in SOURCE_ORDER else len(SOURCE_ORDER)


def fetch_rss_by_source():
    """Return {source name: [items in the feed's own order]}, highest-priority source first."""
    feeds = {}
    for name in sorted(RSS_FEEDS, key=source_rank):
        try:
            parsed = feedparser.parse(RSS_FEEDS[name])
        except Exception as exc:
            print(f"WARNING: could not read {name}: {exc}", file=sys.stderr)
            continue
        items = []
        for entry in parsed.entries[:RSS_ITEMS_PER_FEED]:
            title = clean(entry.get("title", ""))
            link = entry.get("link", "")
            if not title or not link:
                continue
            items.append({
                "title": title,
                "summary": truncate(clean(entry.get("summary", "")), TOP_SUMMARY_CHARS),
                "link": link,
                "source": name,
                "kind": "brief",
            })
        if items:
            feeds[name] = items
        else:
            print(f"WARNING: no items found for {name}", file=sys.stderr)
    return feeds


def pick_top_stories(feeds):
    """Choose lead stories: AP first, then The Guardian, then the rest.

    A lead story that another source also covers is shown once, with the other
    sources listed under it.
    """
    top = []
    for source in sorted(feeds, key=source_rank):
        limit = TOP_PER_SOURCE.get(source, 1)
        taken = 0
        for item in feeds[source][: limit + 3]:
            if taken >= limit:
                break
            tokens = story_tokens(item["title"])
            if any(same_story(t["_tokens"], tokens) for t in top):
                continue   # already covered by a higher-priority source
            top.append(dict(item, _tokens=tokens, also=[]))
            taken += 1

    # List which other sources also cover each top story.
    for story in top:
        for source, items in feeds.items():
            if source == story["source"]:
                continue
            if any(same_story(story["_tokens"], story_tokens(i["title"])) for i in items):
                story["also"].append(source)
    return top


def matches(spec, text):
    """True if text matches the section's pattern and not its exclusion pattern."""
    if not re.search(spec["pattern"], text):
        return False
    exclude = spec.get("exclude")
    if not exclude or re.search(spec.get("keep_if", "(?!)"), text):
        return True
    return not re.search(exclude, text)


def build_digest():
    """Return the sections to print, in order: Top Stories, then each topic."""
    feeds = fetch_rss_by_source()
    top = pick_top_stories(feeds)

    # Anything already shown under Top Stories is never repeated below.
    seen_links = {normalize_link(t["link"]) for t in top}
    shown = [t["_tokens"] for t in top]

    def claim(item):
        """True if the item is new; records it as shown."""
        key = normalize_link(item["link"])
        tokens = story_tokens(item["title"])
        if not key or key in seen_links or any(same_story(tokens, s) for s in shown):
            return False
        seen_links.add(key)
        shown.append(tokens)
        return True

    by_priority = sorted(SECTIONS, key=lambda s: s["priority"])
    layout = {spec["name"]: {"name": spec["name"], "items": [], "spec": spec} for spec in SECTIONS}
    other = {"name": "Other Headlines", "items": [], "spec": None}

    # Candidates from every source. Guardian API stories are fetched per topic.
    candidates = []
    for spec in by_priority:
        for story in fetch_guardian(spec["guardian_query"], spec["guardian_section"], spec["guardian_stories"]):
            story.update(source="Guardian World", kind="story", summary="")
            candidates.append(story)
    for items in feeds.values():
        candidates.extend(items)

    # Order: AP, then The Guardian (full stories before headlines), then BBC, then NPR.
    # The sort is stable, so each feed keeps its own editorial order.
    candidates.sort(key=lambda i: (source_rank(i["source"]), 0 if i["kind"] == "story" else 1))

    for item in candidates:
        text = " ".join([item["title"], item.get("standfirst", ""), item.get("opening", ""),
                         item.get("summary", "")]).lower()
        target = next((layout[s["name"]] for s in by_priority if matches(s, text)), None)
        if target is None:
            if not INCLUDE_OTHER_HEADLINES or item["kind"] == "story":
                continue
            target = other

        if item["kind"] == "story":
            cap = target["spec"]["guardian_stories"]
            if sum(1 for i in target["items"] if i["kind"] == "story") >= cap:
                continue
        elif sum(1 for i in target["items"] if i["kind"] == "brief") >= MAX_BRIEFS_PER_SECTION:
            continue

        if claim(item):
            target["items"].append(item)

    sections = [{"name": "Top Stories", "items": top, "top": True}]
    sections += [layout[spec["name"]] for spec in SECTIONS]
    if INCLUDE_OTHER_HEADLINES:
        sections.append(other)
    return [s for s in sections if s["items"]]


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
    pdf.multi_cell(0, 6.2, story["title"], align="L", new_x="LMARGIN", new_y="NEXT")

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


def source_label(item):
    return DISPLAY_NAMES.get(item["source"], item["source"])


def top_story(pdf, item, lead=False):
    pdf.set_font("Serif", "B", 17 if lead else 13.5)
    pdf.multi_cell(0, 7.6 if lead else 6.2, item["title"], align="L", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Sans", "", 7.5)
    pdf.set_text_color(90, 90, 90)
    credit = source_label(item)
    if item.get("also"):
        credit += "   |   Also reported by " + ", ".join(DISPLAY_NAMES.get(s, s) for s in item["also"])
    pdf.multi_cell(0, 4.5, credit, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)

    if item["summary"]:
        pdf.set_font("Serif", "", 11 if lead else 10.5)
        pdf.multi_cell(0, 5.5, truncate(item["summary"], TOP_SUMMARY_CHARS), align="J",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    pdf.set_font("Sans", "", 6.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 3.8, f"Read the full story: {item['link']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    rule(pdf, 0.2, 4)


def brief_item(pdf, item):
    pdf.set_font("Serif", "B", 11)
    pdf.multi_cell(0, 5.2, item["title"], align="L", new_x="LMARGIN", new_y="NEXT")
    if item["summary"]:
        pdf.set_font("Serif", "", 9.5)
        pdf.multi_cell(0, 4.8, truncate(item["summary"], SUMMARY_CHARS), align="J",
                       new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 6.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 3.6, f"{source_label(item)}   |   {item['link']}", new_x="LMARGIN", new_y="NEXT")
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
        for index, item in enumerate(section["items"]):
            if section.get("top"):
                top_story(pdf, item, lead=(index == 0))
            elif item["kind"] == "story":
                guardian_story(pdf, item)
            else:
                brief_item(pdf, item)

    return bytes(pdf.output())


# ---- Web edition (HTML) --------------------------------------------------

HTML_CSS = """
:root { --bg:#fbfaf7; --fg:#1a1a1a; --muted:#666; --rule:#1a1a1a; --soft:#d9d6cf; color-scheme: light dark; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#16161a; --fg:#ececec; --muted:#a0a0a8; --rule:#ececec; --soft:#3a3a42; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font-family: Georgia, "Times New Roman", serif; line-height:1.55; }
.page { max-width:720px; margin:0 auto; padding:24px 18px 64px; }
.masthead { text-align:center; border-bottom:3px double var(--rule); padding-bottom:10px; margin-bottom:14px; }
.masthead h1 { margin:0; font-size:clamp(2rem, 8vw, 3.2rem); letter-spacing:.04em; }
.masthead .dateline { font-family:Helvetica, Arial, sans-serif; font-size:.72rem;
                      letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin-top:6px; }
nav { text-align:center; margin:0 0 8px; line-height:2;
      font-family:Helvetica, Arial, sans-serif; font-size:.78rem; letter-spacing:.06em; text-transform:uppercase; }
nav a { display:inline-block; margin:0 9px; color:var(--fg); text-decoration:none; border-bottom:1px solid var(--soft); }
h2 { font-family:Helvetica, Arial, sans-serif; font-size:.95rem; letter-spacing:.12em; text-transform:uppercase;
     border-bottom:2px solid var(--rule); padding-bottom:4px; margin:34px 0 14px; }
article { padding:14px 0; border-bottom:1px solid var(--soft); }
article h3 { margin:0 0 4px; font-size:1.25rem; line-height:1.25; }
article.lead h3 { font-size:1.75rem; }
article h3 a { color:var(--fg); text-decoration:none; }
article h3 a:hover { text-decoration:underline; }
.credit { font-family:Helvetica, Arial, sans-serif; font-size:.72rem; color:var(--muted); margin:0 0 8px; }
article p { margin:0 0 8px; }
.standfirst { font-weight:bold; }
.more { font-family:Helvetica, Arial, sans-serif; font-size:.75rem; }
.more a { color:var(--muted); }
footer { margin-top:40px; font-family:Helvetica, Arial, sans-serif; font-size:.72rem; color:var(--muted); text-align:center; }
"""


def esc(text):
    return html.escape(text or "", quote=True)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def html_item(item, top=False, lead=False):
    credit = source_label(item)
    if item.get("kind") == "story" and item.get("byline"):
        credit += f" \u00b7 By {item['byline']}"
    if item.get("also"):
        credit += " \u00b7 Also reported by " + ", ".join(DISPLAY_NAMES.get(s, s) for s in item["also"])

    body = ""
    if item.get("kind") == "story":
        if item.get("standfirst"):
            body += f'<p class="standfirst">{esc(item["standfirst"])}</p>'
        if item.get("opening"):
            body += f'<p>{esc(item["opening"])}</p>'
    elif item.get("summary"):
        body += f'<p>{esc(truncate(item["summary"], TOP_SUMMARY_CHARS if top else SUMMARY_CHARS))}</p>'

    cls = "lead" if lead else ""
    return (f'<article class="{cls}">'
            f'<h3><a href="{esc(item["link"])}">{esc(item["title"])}</a></h3>'
            f'<p class="credit">{esc(credit)}</p>{body}'
            f'<p class="more"><a href="{esc(item["link"])}">Read the full story</a></p>'
            f'</article>')


def build_html(sections, today: str) -> str:
    nav = "".join(f'<a href="#{slug(s["name"])}">{esc(s["name"])}</a>' for s in sections)
    blocks = []
    for section in sections:
        is_top = bool(section.get("top"))
        items = "".join(html_item(i, top=is_top, lead=(is_top and n == 0))
                        for n, i in enumerate(section["items"]))
        blocks.append(f'<section id="{slug(section["name"])}"><h2>{esc(section["name"])}</h2>{items}</section>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Daily Digest \u2013 {esc(today)}</title>
<style>{HTML_CSS}</style>
</head>
<body>
<div class="page">
<header class="masthead"><h1>THE DAILY DIGEST</h1>
<div class="dateline">{esc(today)} &nbsp;|&nbsp; Morning Edition</div></header>
<nav>{nav}</nav>
{"".join(blocks)}
<footer>Excerpts and links from AP News, The Guardian, BBC News and NPR. For personal reading.</footer>
</div>
</body>
</html>
"""


def save_html(html_doc: str):
    folder = os.path.dirname(HTML_OUTPUT_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(html_doc)


def send_html_email(html_doc: str, today: str):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = HTML_EMAIL_TO
    msg["Subject"] = f"The Daily Digest, web edition: {today}"
    msg.set_content("This email contains the web edition. Open the attached .html file in a browser.")
    msg.add_alternative(html_doc, subtype="html")
    msg.add_attachment(
        html_doc.encode("utf-8"),
        maintype="text",
        subtype="html",
        filename=f"Daily-Digest-{today}.html",
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)


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
    html_doc = build_html(sections, today)

    # The web edition is a bonus: a problem here must never stop the Kindle delivery.
    try:
        save_html(html_doc)
        print(f"Saved web edition to {HTML_OUTPUT_PATH}")
    except Exception as exc:
        print(f"WARNING: could not save the web edition: {exc}", file=sys.stderr)

    send_to_kindle(pdf_bytes, today)
    count = sum(len(s["items"]) for s in sections)
    print(f"Sent The Daily Digest for {today} ({count} stories) to {KINDLE_EMAIL}")

    if HTML_EMAIL_TO:
        try:
            send_html_email(html_doc, today)
            print(f"Emailed the web edition to {HTML_EMAIL_TO}")
        except Exception as exc:
            print(f"WARNING: could not email the web edition: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
