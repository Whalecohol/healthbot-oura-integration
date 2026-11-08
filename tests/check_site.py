#!/usr/bin/env python3
"""Check the provisional static site for structure, links, and wording limits."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

EXPECTED_HTML = {
    DOCS / "index.html": {
        "title": "HealthBot Personal Oura Integration",
        "nav_current": "Overview",
        "phrases": [
            "single-user",
            "non-commercial",
            "official OAuth",
            "shared hosted computer",
            "HealthBot",
            "gjlumsden/oura-mcp",
            "Exact OAuth scopes",
            "AI service providers",
            "may be sent through HealthBot",
        ],
    },
    DOCS / "privacy" / "index.html": {
        "title": "Privacy draft | HealthBot Personal Oura Integration",
        "nav_current": "Privacy draft",
        "phrases": [
            "not an adopted privacy policy",
            "access tokens and refresh tokens",
            "AI service providers",
            "exact scopes are unconfirmed",
            "Deletion is unconfirmed",
            "operator contact method is unconfirmed",
            "sharing, selling, or advertising",
            "conversation logs",
        ],
    },
    DOCS / "terms" / "index.html": {
        "title": "Terms draft | HealthBot Personal Oura Integration",
        "nav_current": "Terms draft",
        "phrases": [
            "not a contract",
            "non-commercial",
            "not a medical device",
            "medical advice",
            "as is",
            "API agreement",
            "revoke OAuth access",
            "operator contact method is unconfirmed",
            "shared hosted computer",
        ],
    },
}

REQUIRED_EVERY_PAGE = [
    "Not enabled.",
    "2026-11-08",
    "The owner has not adopted this text.",
    "unconfirmed",
    "is not affiliated with or endorsed by Oura Health Oy",
    "Skip to content",
    "Provisional draft",
    "drafting date",
]

FORBIDDEN = [
    "we do not sell",
    "we never sell",
    "will not sell",
    "do not sell",
    "never sell",
    "not sold",
    "we do not share",
    "will not share",
    "never share",
    "no sharing",
    "will not be shared",
    "hipaa",
    "gdpr",
    "ccpa",
    "iso 27001",
    "soc 2",
    "encrypted",
    "encryption",
    "bank-grade",
    "military-grade",
    "guarantee",
    "mailto:",
    "support@",
    "privacy@",
    "contact@",
    "lorem",
    "todo",
    "fixme",
    "tbd",
    "[pending]",
    "placeholder",
    "click here",
    "your privacy is important",
    "we take privacy seriously",
    "effective date",
    "last updated",
    "hereby",
    "you agree",
    "by accessing",
    "by using this",
    "governed by the laws",
    "limitation of liability",
    "indemnif",
    "cookie",
    "google-analytics",
    "gtag(",
    "facebook",
    "hotjar",
    "mixpanel",
    "plausible",
    "sentry",
]

ALLOWED_EXTERNAL = {
    "https://github.com/gjlumsden/oura-mcp",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s\"')>]+")
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
FORBIDDEN_TAGS = {
    "script",
    "form",
    "iframe",
    "object",
    "embed",
    "img",
    "video",
    "audio",
    "button",
    "input",
    "textarea",
    "select",
    "style",
}

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def contrast_ratio(left: str, right: str) -> float:
    def channel(value: int) -> float:
        scaled = value / 255
        if scaled <= 0.04045:
            return scaled / 12.92
        return ((scaled + 0.055) / 1.055) ** 2.4

    def luminance(color: str) -> float:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
        return (
            0.2126 * channel(red)
            + 0.7152 * channel(green)
            + 0.0722 * channel(blue)
        )

    lighter = max(luminance(left), luminance(right))
    darker = min(luminance(left), luminance(right))
    return (lighter + 0.05) / (darker + 0.05)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.tags: list[str] = []
        self.attrs: list[tuple[str, list[tuple[str, str | None]]]] = []
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.ids: list[str] = []
        self.current_pages = 0
        self.skip_href = None
        self.h1 = 0
        self.stylesheets: list[str] = []
        self.hrefs: list[str] = []
        self.bad_attrs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attrs.append((tag, attrs))
        attr_map = {key: value for key, value in attrs}
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1 += 1
        element_id = attr_map.get("id")
        if element_id:
            self.ids.append(element_id)
        if attr_map.get("aria-current") == "page":
            self.current_pages += 1
        if tag == "a" and attr_map.get("class") and "skip" in attr_map["class"].split():
            self.skip_href = attr_map.get("href")
        if tag == "a" and attr_map.get("href"):
            self.hrefs.append(attr_map["href"])
        if tag == "link" and attr_map.get("rel") == "stylesheet" and attr_map.get("href"):
            self.stylesheets.append(attr_map["href"])
        for key, value in attrs:
            if key.startswith("on"):
                self.bad_attrs.append(key)
            if value and key == "style":
                self.bad_attrs.append("style")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            fail(f"unbalanced tag </{tag}> near {self.stack[-3:]}")
            return
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)


def resolve(page: Path, href: str) -> Path | None:
    if href.startswith("#"):
        return page
    path_part = href.split("#", 1)[0]
    if path_part == "":
        return page
    target = (page.parent / path_part).resolve()
    if target.is_dir():
        target = target / "index.html"
    return target


def color_tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})", block))


def check_contrast(css_text: str) -> None:
    light_match = re.search(r":root\s*\{([^}]*)\}", css_text)
    dark_match = re.search(
        r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{([^}]*)\}",
        css_text,
        re.DOTALL,
    )
    if not light_match or not dark_match:
        fail("site.css is missing light or dark color tokens")
        return
    light = color_tokens(light_match.group(1))
    dark = color_tokens(dark_match.group(1))
    if not light or not dark:
        fail("site.css is missing light or dark color tokens")
        return
    pairs = [
        ("--ink", "--bg"),
        ("--muted", "--bg"),
        ("--accent", "--bg"),
        ("--accent", "--paper"),
        ("--accent-hover", "--bg"),
        ("--visited", "--bg"),
        ("--visited", "--paper"),
        ("--ink", "--paper"),
        ("--banner-ink", "--banner-bg"),
    ]
    for theme_name, theme in ("light", light), ("dark", dark):
        for foreground, background in pairs:
            ratio = contrast_ratio(theme[foreground], theme[background])
            if ratio < 4.5:
                fail(
                    f"{theme_name} contrast {foreground} on {background} is {ratio:.2f}"
                )


def main() -> int:
    if not (DOCS / ".nojekyll").is_file():
        fail("docs/.nojekyll is missing")

    html_files = sorted(DOCS.rglob("*.html"))
    expected = set(EXPECTED_HTML)
    if set(html_files) != expected:
        fail(f"unexpected html files: {set(html_files) ^ expected}")

    css_path = DOCS / "site.css"
    if not css_path.is_file():
        fail("docs/site.css is missing")
    else:
        css_text = css_path.read_text(encoding="utf-8")
        if "@media (max-width: 40rem)" not in css_text:
            fail("site.css has no mobile layout breakpoint")
        if "prefers-color-scheme: dark" not in css_text:
            fail("site.css has no dark color scheme")
        external_in_css = URL_RE.findall(css_text)
        if external_in_css:
            fail(f"site.css references external URLs: {external_in_css}")
        check_contrast(css_text)

    for page in html_files:
        text = page.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        parser.close()
        visible = " ".join(parser.text_parts)
        lowered = text.lower()
        spec = EXPECTED_HTML[page]

        if parser.stack:
            fail(f"{page.relative_to(ROOT)} has unclosed tags: {parser.stack}")
        if 'lang="en"' not in text:
            fail(f"{page.name} is missing lang=en")
        if 'name="viewport" content="width=device-width, initial-scale=1"' not in text:
            fail(f"{page.name} is missing a responsive viewport")
        if parser.h1 != 1:
            fail(f"{page.relative_to(ROOT)} has {parser.h1} h1 elements")
        title = " ".join(part.strip() for part in parser.title_parts if part.strip())
        if title != spec["title"]:
            fail(f"{page.relative_to(ROOT)} title is {title!r}")
        if "content" not in parser.ids:
            fail(f"{page.relative_to(ROOT)} is missing main id=content")
        if parser.skip_href != "#content":
            fail(f"{page.relative_to(ROOT)} skip link is {parser.skip_href!r}")
        if parser.current_pages != 2:
            fail(
                f"{page.relative_to(ROOT)} should mark the current page in header and footer"
            )
        if spec["nav_current"] not in visible:
            fail(f"{page.relative_to(ROOT)} is missing nav label {spec['nav_current']}")
        for phrase in REQUIRED_EVERY_PAGE + spec["phrases"]:
            if phrase not in text and phrase not in visible:
                fail(f"{page.relative_to(ROOT)} is missing {phrase!r}")
        for phrase in FORBIDDEN:
            if phrase in lowered:
                fail(f"{page.relative_to(ROOT)} contains forbidden wording {phrase!r}")
        email = EMAIL_RE.search(text)
        if email:
            fail(f"{page.relative_to(ROOT)} contains an email address")
        for tag in FORBIDDEN_TAGS:
            if tag in parser.tags:
                fail(f"{page.relative_to(ROOT)} contains <{tag}>")
        if parser.bad_attrs:
            fail(f"{page.relative_to(ROOT)} contains {parser.bad_attrs}")
        if len(parser.stylesheets) != 1:
            fail(f"{page.relative_to(ROOT)} should link one stylesheet")
        else:
            sheet = resolve(page, parser.stylesheets[0])
            if sheet != css_path.resolve():
                fail(f"{page.relative_to(ROOT)} stylesheet does not resolve to docs/site.css")
        for match in URL_RE.findall(text):
            cleaned = match.rstrip(".,")
            if cleaned not in ALLOWED_EXTERNAL:
                fail(f"{page.relative_to(ROOT)} has disallowed URL {cleaned}")
        targets = set()
        for href in parser.hrefs:
            if href.startswith(("http://", "https://", "mailto:", "javascript:", "data:", "//")):
                continue
            if href.startswith("/"):
                fail(f"{page.relative_to(ROOT)} uses a root-absolute link {href}")
                continue
            target = resolve(page, href)
            if target is None or not target.is_file():
                fail(f"{page.relative_to(ROOT)} broken link {href}")
            elif target.suffix == ".html":
                targets.add(target)
        missing = expected - targets
        if missing:
            fail(
                f"{page.relative_to(ROOT)} does not link to "
                + ", ".join(str(item.relative_to(ROOT)) for item in sorted(missing))
            )

    workflow = ROOT / ".github" / "workflows" / "site-checks.yml"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    if "python3 tests/check_site.py" not in workflow_text:
        fail("the site check workflow is missing")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in (
        "Deploy from a branch",
        "/docs",
        "main",
        "https://whalecohol.github.io/healthbot-oura-integration/",
        "https://whalecohol.github.io/healthbot-oura-integration/privacy/",
        "https://whalecohol.github.io/healthbot-oura-integration/terms/",
    ):
        if phrase not in readme:
            fail(f"README is missing Pages setting detail {phrase!r}")

    if failures:
        print(f"{len(failures)} check(s) failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print(f"Checked {len(html_files)} pages, stylesheet, links, contrast, and provisional wording.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
