"""Scrape Family Feud survey boards transcribed from TV episodes.

Source: https://mstiescott.neocities.org/
These pages transcribe face-off questions and on-board answers/scores
from broadcast episodes (not an official Fremantle dump).
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup

BASE_URL = "https://mstiescott.neocities.org"
SEASONS = [5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
ANSWER_COUNTS = [8, 7, 6, 5, 4]  # skip 1-answer Fast Money boards
USER_AGENT = (
    "family-feud-benchmark/1.0 (research; "
    "+https://github.com/tcondello/family_feud_benchmark)"
)


def fetch(url: str, retries: int = 4) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    delay = 1.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                for encoding in ("utf-8", "windows-1252", "latin-1"):
                    try:
                        return raw.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
        time.sleep(delay)
        delay *= 2
    return None


def season_index_urls(season: int) -> list[str]:
    return [
        f"{BASE_URL}/feud{season}",
        f"{BASE_URL}/feud{season}.html",
    ]


def page_urls(season: int, answers: int) -> list[str]:
    return [
        f"{BASE_URL}/feud{season}_{answers}",
        f"{BASE_URL}/feud{season}_{answers}.html",
        f"{BASE_URL}/feud{season}s{answers}a.html",
    ]


def discover_page_urls(season: int) -> list[tuple[int, str]]:
    html = None
    for url in season_index_urls(season):
        html = fetch(url)
        if html and "Not Found" not in html[:200]:
            break
        html = None
    if not html:
        raise RuntimeError(f"Could not load index for season {season}")

    soup = BeautifulSoup(html, "html.parser")
    found: dict[int, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        match = re.search(rf"feud{season}(?:_(\d+)|s(\d+)a\.html)", href)
        if not match:
            continue
        count = int(match.group(1) or match.group(2))
        if count not in ANSWER_COUNTS:
            continue
        absolute = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
        found[count] = absolute

    if found:
        return [(count, found[count]) for count in sorted(found, reverse=True)]

    pages = []
    for count in ANSWER_COUNTS:
        for url in page_urls(season, count):
            html = fetch(url)
            if html and "Not Found" not in html[:200]:
                pages.append((count, url))
                break
    return pages


def clean_text(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cell_text(cell) -> str:
    return clean_text(cell.get_text(" ", strip=True))


def is_score(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}", text))


def normalize_answer(text: str) -> str:
    if text.isupper() and len(text) > 3:
        return text.title()
    return text


def looks_like_question(text: str) -> bool:
    if len(text) < 12 or len(text) > 320:
        return False
    if is_score(text):
        return False
    lowered = text.lower()
    if lowered.startswith("season "):
        return False
    if "survey" in lowered and "answer" in lowered and len(text) < 80:
        return False
    # Reject flattened answer boards mistaken for questions.
    if len(re.findall(r"\b\d{1,3}\b", text)) >= 3 and text.upper() == text:
        return False
    if re.search(r"\b\d{1,3}\b.*\b\d{1,3}\b.*\b\d{1,3}\b", text) and "/" in text:
        return False
    return True


def extract_answers_from_table(table) -> list[dict]:
    """Extract answer/score pairs from a board table.

    Older season pages have malformed/unclosed <tr> tags, so BeautifulSoup may
    nest later rows inside the first. Walk leaf <td> cells in document order
    instead of trusting row structure.
    """
    nested_boards = [
        child
        for child in table.find_all("table")
        if str(child.get("border") or "") == "1" and child is not table
    ]
    if nested_boards:
        return extract_answers_from_table(nested_boards[0])

    cells = [td for td in table.find_all("td") if not td.find("table")]
    answers: list[dict] = []
    i = 0
    while i < len(cells):
        text = cell_text(cells[i])
        colspan = int(cells[i].get("colspan") or 1)
        if not text or colspan > 1:
            i += 1
            continue
        if i + 1 < len(cells):
            score_text = cell_text(cells[i + 1])
            if is_score(score_text) and not is_score(text):
                answers.append(
                    {"answer": normalize_answer(text), "score": int(score_text)}
                )
                i += 2
                continue
        i += 1
    return answers


def next_answer_table(node, expected_answers: int | None = None):
    for table in node.find_all_next("table"):
        border = str(table.get("border") or "")
        if border != "1":
            continue
        # Skip outer chrome tables that only wrap another board.
        nested = [
            child
            for child in table.find_all("table")
            if str(child.get("border") or "") == "1"
        ]
        answers = extract_answers_from_table(table)
        if len(answers) < 2:
            continue
        if expected_answers is not None and abs(len(answers) - expected_answers) > 1:
            continue
        # Prefer the innermost matching board when both outer/inner match.
        if nested:
            inner_answers = extract_answers_from_table(nested[0])
            if len(inner_answers) >= 2 and (
                expected_answers is None
                or abs(len(inner_answers) - expected_answers) <= 1
            ):
                return nested[0], inner_answers
        return table, answers
    return None, []


def parse_modern_font_questions(soup: BeautifulSoup, expected_answers: int | None) -> list[dict]:
    questions = []
    seen = set()
    for font in soup.find_all("font"):
        if str(font.get("size") or "") != "4":
            continue
        question = clean_text(font.get_text(" ", strip=True))
        if not looks_like_question(question):
            continue
        _, answers = next_answer_table(font, expected_answers)
        if len(answers) < 2:
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        questions.append({"question": question, "answers": answers})
    return questions


def parse_classic_question_tables(soup: BeautifulSoup, expected_answers: int | None) -> list[dict]:
    questions = []
    seen = set()
    for table in soup.find_all("table"):
        border = str(table.get("border") or "0")
        if border != "0":
            continue
        rows = table.find_all("tr", recursive=False)
        if len(rows) != 1:
            continue
        question = cell_text(rows[0])
        if not looks_like_question(question):
            continue
        # Classic pages put the prompt in a narrow gray/blue banner table.
        width_hint = rows[0].find("td")
        width = int((width_hint.get("width") if width_hint else None) or 0)
        if width and width < 400:
            continue
        _, answers = next_answer_table(table, expected_answers)
        if len(answers) < 2:
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        questions.append({"question": question, "answers": answers})
    return questions


def parse_page(html: str, expected_answers: int | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    modern = parse_modern_font_questions(soup, expected_answers)
    if modern:
        return modern
    return parse_classic_question_tables(soup, expected_answers)


def scrape_season(season: int) -> dict:
    pages = discover_page_urls(season)
    all_questions: list[dict] = []
    sources: list[str] = []
    for count, url in pages:
        html = fetch(url)
        if not html:
            continue
        parsed = parse_page(html, expected_answers=count)
        print(f"season {season}: {url} -> {len(parsed)} questions")
        all_questions.extend(parsed)
        sources.append(url)
        time.sleep(0.35)

    deduped = []
    seen = set()
    for item in all_questions:
        key = item["question"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "source": {
            "name": "mstiescott_neocities",
            "description": (
                "Survey questions and board answers transcribed from Family Feud "
                "TV episodes (face-off wording and on-screen answers/scores)."
            ),
            "homepage": f"{BASE_URL}/feud{season}",
            "season": season,
            "pages": sources,
        },
        "questions": deduped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        default=SEASONS,
        help="Season numbers to scrape (default: all available).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("questions/mstiescott"),
        help="Directory for per-season JSON files.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    combined: list[dict] = []
    for season in args.seasons:
        payload = scrape_season(season)
        out_path = args.output_dir / f"season_{season:02d}.json"
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path} ({len(payload['questions'])} questions)")
        combined.extend(payload["questions"])

    combined_path = args.output_dir / "all_seasons.json"
    combined_payload = {
        "source": {
            "name": "mstiescott_neocities",
            "description": (
                "Combined TV-episode survey transcriptions from "
                "https://mstiescott.neocities.org/"
            ),
            "homepage": BASE_URL,
            "seasons": args.seasons,
        },
        "questions": combined,
    }
    combined_path.write_text(json.dumps(combined_payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {combined_path} ({len(combined)} questions)")


if __name__ == "__main__":
    main()
