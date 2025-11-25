#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Final

import requests
from bs4 import BeautifulSoup

CHARTS_URL: Final[str] = "https://kworb.net/spotify/listeners.html"


def fetch_html(url: str) -> str:
    """
    Fetch HTML content from a given URL.

    Parameters
    ----------
    url : str
        The URL to fetch.

    Returns
    -------
    str
        The HTML response text.

    Raises
    ------
    requests.HTTPError
        If the request fails with a non-200 status code.
    """
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except:
        print("Error while fetch the html file")
        sys.exit(0)


def timestamp() -> str:
    # Microsecond precision to avoid collisions
    return datetime.now().strftime("%Y%m%dT%H%M%S_%f")


def sanitize(name: str) -> str:
    # Keep letters, digits, dot, dash, underscore
    name = name.strip()
    name = name.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "unnamed"


def unique_path(base: Path) -> Path:
    # If a file exists, append _1, _2, ...
    if not base.exists():
        return base
    i = 1
    stem = base.stem
    suffix = base.suffix
    while True:
        candidate = base.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def parse_args():
    p = argparse.ArgumentParser(description="Extract all HTML <table> elements to CSV files.")
    p.add_argument(
        "html_url",
        nargs="?",
        default=CHARTS_URL,
        help=f"url to the HTML file (default: {CHARTS_URL}",
    )
    p.add_argument(
        "-o", "--outdir", help="Output directory (default: current working directory)", default="."
    )
    return p.parse_args()


def main():
    args = parse_args()
    html_url = args.html_url

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    html_text = fetch_html(html_url)
    # Prefer lxml if present, else fallback to Python's html.parser
    try:
        soup = BeautifulSoup(html_text, "lxml")
    except Exception:
        soup = BeautifulSoup(html_text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        sys.stderr.write("No <table> elements found.\n")
        return

    for idx, table in enumerate(tables, start=1):
        tbl_id = str(table.get("id") or "").strip()
        tbl_class_list = table.get("class") or []

        if tbl_id:
            fname = sanitize(tbl_id) + ".csv"
        elif tbl_class_list:
            # Use any class name (first), add timestamp for uniqueness
            fname = f"{sanitize(tbl_class_list[0])}_{timestamp()}.csv"
        else:
            fname = f"{timestamp()}.csv"

        out_path = unique_path(outdir / fname)

        # Extract rows
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            # Use get_text with separator to preserve inner <br> etc.
            row = [c.get_text(separator=" ", strip=True) for c in cells]
            rows.append(row)

        # Skip empty tables
        if not rows:
            continue

        # Normalize row lengths for CSV (pad shorter rows)
        max_len = max(len(r) for r in rows)
        for r in rows:
            if len(r) < max_len:
                r.extend([""] * (max_len - len(r)))

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(str(out_path))


if __name__ == "__main__":
    main()
