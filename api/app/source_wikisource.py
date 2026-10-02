# Copyright 2026 Aaron John Schlosser, PhD.
"""Wikisource provider: project discovery, author-page enumeration, and whole-work acquisition.

Everything goes through supported MediaWiki/Wikibase APIs (sitematrix, siteinfo,
query/links with continuation, parse, proofreadinfo), never by scraping /wiki/
pages. Parsing functions take plain payloads so fixtures can test them offline.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from html import escape, unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, unquote

import httpx

from .source_identity import (
    CaptureError,
    CaptureErrorCode,
    CaptureOptions,
    ContributionRole,
    ResolvedAuthor,
    SourceCandidate,
    fold,
    normalize_language,
)
from .source_provider import (
    USER_AGENT,
    AcquiredSource,
    DiscoveryReport,
    ProgressCallback,
    ProviderHttp,
)

_RATE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0

# A bounded fallback, used only when Wikimedia's sitematrix cannot be reached. It is labelled
# as such to callers; the authoritative list comes from project discovery.
FALLBACK_PROJECTS = ("en", "fr", "de", "it", "es", "pt", "la", "el", "ru", "pl", "nl", "sv", "he", "ar", "zh", "ja")
# Legacy name kept for callers that imported the closed list.
WIKISOURCE_LANGUAGES = FALLBACK_PROJECTS
_PROJECT_CODE = re.compile(r"^[a-z][a-z0-9-]{1,15}$")
_PROJECT_CACHE: dict[str, Any] = {"at": 0.0, "projects": None}
_PROJECT_CACHE_TTL_S = 24 * 3600
_FAILED_CACHE_TTL_S = 300  # a failed discovery is not cached for long

MAX_WIKISOURCE_SUBPAGES = 400
MAX_LINK_PAGES = 40  # continuation pages per author page (500 links each)


def project_host(code: str) -> str:
    if not _PROJECT_CODE.match(code or ""):
        raise ValueError(f"Unsupported Wikisource language: {code}")
    # The multilingual project lives at wikisource.org itself.
    return "https://wikisource.org" if code == "mul" else f"https://{code}.wikisource.org"


# --- Project discovery -------------------------------------------------------------


def parse_sitematrix(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Open Wikisource projects from a ``action=sitematrix`` payload."""
    matrix = payload.get("sitematrix") or {}
    projects: list[dict[str, Any]] = []
    for key, entry in matrix.items():
        if key == "count" or not isinstance(entry, dict):
            continue
        for site in entry.get("site") or []:
            if not isinstance(site, dict) or site.get("code") != "wikisource" or site.get("closed"):
                continue
            code = str(site.get("lang") or entry.get("code") or "")
            if _PROJECT_CODE.match(code):
                projects.append({"code": code, "name": str(entry.get("localname") or entry.get("name") or code), "url": str(site.get("url") or "")})
    for site in matrix.get("specials") or []:
        if isinstance(site, dict) and site.get("dbname") == "sourceswiki" and not site.get("closed"):
            projects.append({"code": "mul", "name": "Multilingual Wikisource", "url": "https://wikisource.org"})
    return sorted(projects, key=lambda item: item["code"])


def discover_projects(http: ProviderHttp | None = None, *, now: float | None = None) -> dict[str, Any]:
    """Wikisource projects from Wikimedia's sitematrix, cached; a labelled fallback when unavailable."""
    moment = now if now is not None else time.monotonic()
    cached = _PROJECT_CACHE.get("projects")
    if cached is not None and moment - float(_PROJECT_CACHE["at"]) < float(_PROJECT_CACHE.get("ttl") or _PROJECT_CACHE_TTL_S):
        return cached
    http = http or ProviderHttp("wikimedia")
    try:
        payload = http.get_json(
            "https://meta.wikimedia.org/w/api.php",
            {"action": "sitematrix", "smtype": "language|special", "smsiteprop": "url|dbname|code|lang", "smlangprop": "code|site|localname", "format": "json", "formatversion": 2},
        )
        projects = parse_sitematrix(payload)
        if not projects:
            raise CaptureError(CaptureErrorCode.INVALID_PROVIDER_RESPONSE, "Wikimedia listed no Wikisource projects.")
        result = {"authoritative": True, "projects": projects}
        ttl = _PROJECT_CACHE_TTL_S
    except CaptureError as exc:
        result = {
            "authoritative": False,
            "projects": [{"code": code, "name": code, "url": project_host(code)} for code in FALLBACK_PROJECTS],
            "warning": exc.message,
        }
        ttl = _FAILED_CACHE_TTL_S
    _PROJECT_CACHE.update({"at": moment, "projects": result, "ttl": ttl})
    return result


def known_project(code: str) -> bool:
    projects = discover_projects()
    return any(item["code"] == code for item in projects["projects"])


# --- Legacy single-page search/import (kept on this module; re-exported by source_gutenberg) ---


def _legacy_wait() -> None:
    global _LAST_REQUEST
    with _RATE_LOCK:
        elapsed = time.monotonic() - _LAST_REQUEST
        if elapsed < 0.2:
            time.sleep(0.2 - elapsed)
        _LAST_REQUEST = time.monotonic()


def search_wikisource(query: str, limit: int = 12, language: str = "en") -> list[dict[str, Any]]:
    """Search one Wikisource project through the public MediaWiki API after an explicit user search."""
    text = str(query or "").strip()
    if not text:
        return []
    if not known_project(language):
        raise ValueError(f"Unsupported Wikisource language: {language}")
    host = project_host(language)
    limit = max(1, min(30, int(limit)))
    _legacy_wait()
    response = httpx.get(
        f"{host}/w/api.php",
        params={"action": "query", "list": "search", "srsearch": text, "srlimit": limit, "srnamespace": 0, "srprop": "snippet|wordcount", "format": "json", "formatversion": 2},
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0, connect=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("query", {}).get("search", [])
    return [
        {
            "source": "wikisource",
            "language": language,
            "title": str(item.get("title") or ""),
            "page_id": int(item["pageid"]),
            "snippet": unescape(re.sub(r"<[^>]+>", "", str(item.get("snippet") or ""))).strip(),
            "word_count": int(item.get("wordcount") or 0),
            "url": f"{host}/wiki/{quote(str(item.get('title') or '').replace(' ', '_'))}",
        }
        for item in results
        if isinstance(item, dict) and item.get("title") and item.get("pageid")
    ]


_WIKISOURCE_HOST = re.compile(r"^([a-z\-]+\.)?wikisource\.org$", re.IGNORECASE)


def wikisource_page_title(parsed: Any) -> str:
    """Page title for a /wiki/<Title> or ?title=<Title> Wikisource URL, else ''."""
    host = (parsed.hostname or "").lower()
    if not _WIKISOURCE_HOST.match(host):
        return ""
    if parsed.path.startswith("/wiki/"):
        return unquote(parsed.path[len("/wiki/"):]).replace("_", " ").strip()
    match = re.search(r"(?:^|&)title=([^&]+)", parsed.query or "")
    return unquote(match.group(1).replace("+", " ")).replace("_", " ").strip() if match else ""


def _parse_params(title: str) -> dict[str, Any]:
    return {"action": "parse", "page": title, "prop": "text|revid", "redirects": 1, "disableeditsection": 1, "disabletoc": 1, "format": "json", "formatversion": 2}


def _parse_result(payload: dict[str, Any], title: str) -> tuple[str, str, dict[str, Any]]:
    if isinstance(payload.get("error"), dict):
        raise ValueError(f"Wikisource: {payload['error'].get('info') or 'page not found'}")
    parse = payload.get("parse") or {}
    html = str(parse.get("text") or "")
    if not html:
        raise ValueError("Wikisource returned no page content.")
    info = {"page_id": parse.get("pageid"), "revision_id": parse.get("revid")}
    return str(parse.get("title") or title), html, info


def wikisource_parse(base: str, title: str, http: ProviderHttp | None = None) -> tuple[str, str, dict[str, Any]]:
    """(resolved title, rendered HTML, page/revision ids) for one page through the parse API."""
    if http is not None:
        return _parse_result(http.get_json(f"{base}/w/api.php", _parse_params(title)), title)
    _legacy_wait()
    response = httpx.get(f"{base}/w/api.php", params=_parse_params(title), headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(45.0, connect=10.0))
    response.raise_for_status()
    return _parse_result(response.json(), title)


def _wikisource_parse(parsed: Any, title: str) -> tuple[str, str]:
    """Compatibility shim for callers/tests of the pre-provider helper."""
    resolved, html, _info = wikisource_parse(f"{parsed.scheme}://{parsed.netloc}", title)
    return resolved, html


def wikisource_subpage_titles(html: str, root_title: str) -> list[str]:
    """Subpages of `root_title` linked from its page, in reading order, each once (the work's contents).

    Bounded and cycle-free: only strict ``root/…`` subpages, deduplicated, capped at MAX_WIKISOURCE_SUBPAGES.
    """
    prefix = root_title.replace(" ", "_") + "/"
    seen: set[str] = set()
    titles: list[str] = []
    for href in re.findall(r'href="/wiki/([^"#?]+)', html):
        name = unquote(href.replace("&amp;", "&"))
        if not name.startswith(prefix) or name in seen:
            continue
        seen.add(name)
        titles.append(name.replace("_", " "))
    return titles[:MAX_WIKISOURCE_SUBPAGES]


def fetch_whole_work(
    base: str, title: str, *, max_bytes: int, http: ProviderHttp | None = None, parse: Any = None
) -> tuple[bytes, str, dict[str, Any]]:
    """A work page plus its subpages, each in a section naming the page it came from.

    Returns (html bytes, resolved title, provenance with page/revision ids of every page fetched).
    """
    parse = parse or (lambda t: wikisource_parse(base, t, http))
    resolved, html, info = parse(title)
    parts = [html]
    pages = [{"title": resolved, **info}]
    total = len(html.encode("utf-8"))
    for subpage in wikisource_subpage_titles(html, resolved):
        if http is not None:
            http.check_cancelled()
        sub_title, sub_html, sub_info = parse(subpage)
        section = f'<section data-wikisource-page="{escape(sub_title, quote=True)}">{sub_html}</section>'
        total += len(section.encode("utf-8"))
        if total > max_bytes:
            raise ValueError("This Wikisource work exceeds the upload size limit; import its parts (subpages) separately.")
        parts.append(section)
        pages.append({"title": sub_title, **sub_info})
    data = "\n".join(parts).encode("utf-8")
    if len(data) > max_bytes:
        raise ValueError("The URL exceeds the upload size limit.")
    return data, resolved, {"pages": pages}


_SCAN_TITLE = re.compile(r"(?:^|:)([^:/]+\.(?:djvu|pdf))/(\d+)\s*$", re.I)
MAX_SCAN_PAGES = 80
MAX_SCAN_PAGE_BYTES = 800_000
MAX_SCAN_TOTAL_BYTES = 16 * 1024 * 1024


def scan_targets_from_titles(titles: list[str]) -> list[dict[str, Any]]:
    """DjVu/PDF scan pages named by ProofreadPage titles, in first-seen order."""
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for raw in titles:
        title = unquote(str(raw or "").replace("_", " ")).strip()
        match = _SCAN_TITLE.search(title)
        if not match:
            continue
        file_name = match.group(1).strip()
        page = int(match.group(2))
        key = (file_name.casefold(), page)
        if page < 1 or key in seen:
            continue
        seen.add(key)
        found.append({"file": file_name, "djvu_page": page})
        if len(found) >= MAX_SCAN_PAGES:
            break
    return found


def scan_targets_from_html(html: str) -> list[dict[str, Any]]:
    titles = re.findall(r'data-page-name="([^"]+)"', html, re.I)
    titles += re.findall(r"(?:/wiki/|title=)(Page:[^\"'#<\s]+)", html, re.I)
    return scan_targets_from_titles(titles)


def fetch_wikisource_scans(http: Any, api_base: str, targets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Bounded JPEG renders of Wikisource scan pages. Failures are warnings, not lost text."""
    from .source_provider import host_allowed

    saved: list[dict[str, Any]] = []
    warnings: list[str] = []
    total = 0
    policy = getattr(http, "policy", None)
    for target in targets:
        if len(saved) >= MAX_SCAN_PAGES or total >= MAX_SCAN_TOTAL_BYTES:
            warnings.append("scan_pages_truncated")
            break
        title = f"File:{target['file']}"
        try:
            payload = http.get_json(f"{api_base.rstrip('/')}/w/api.php", {
                "action": "query", "titles": title, "prop": "imageinfo",
                "iiprop": "url|mime", "iiurlparam": f"page{int(target['djvu_page'])}-640px",
                "format": "json", "formatversion": "2",
            })
        except CaptureError as exc:
            warnings.append(f"scan_lookup_failed:{exc.code}")
            break
        pages = ((payload.get("query") or {}).get("pages") or [])
        info = (pages[0].get("imageinfo") or [{}])[0] if pages and isinstance(pages[0], dict) else {}
        thumb = str(info.get("thumburl") or "")
        if not thumb:
            warnings.append("scan_thumbnail_missing")
            continue
        try:
            response = http.get(thumb, max_bytes=MAX_SCAN_PAGE_BYTES)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = str(response.headers.get("location") or "")
                if location and policy is not None and host_allowed(location, policy):
                    response = http.get(location, max_bytes=MAX_SCAN_PAGE_BYTES)
            data = bytes(response.content or b"")
        except CaptureError as exc:
            warnings.append(f"scan_download_failed:{exc.code}")
            break
        if response.status_code != 200 or not data.startswith(b"\xff\xd8"):
            warnings.append("scan_not_jpeg")
            continue
        saved.append({**target, "data": data})
        total += len(data)
    return saved, warnings


def fetch_wikisource_page(parsed: Any, title: str, *, max_bytes: int) -> tuple[bytes, str, str]:
    """Fetch a Wikisource work through the MediaWiki API (never by scraping /wiki/)."""
    base = f"{parsed.scheme}://{parsed.netloc}"
    data, resolved, _prov = fetch_whole_work(base, title, max_bytes=max_bytes, parse=lambda t: (*_wikisource_parse(parsed, t), {}))
    safe = re.sub(r"[^\w.\- ]+", "_", resolved).strip().replace(" ", "_") or "wikisource"
    return data, f"{safe}.html", "text/html; charset=utf-8"


# --- Author-page discovery -----------------------------------------------------------

# Deterministic section-heading evidence, per project language. A heading that matches none of
# these leaves the role "unknown" (reviewable) — ambiguity is never turned into authorship.
_SECTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ContributionRole.ABOUT_AUTHOR, ("works about", "about ", "sur ", "über ", "uber ", "zu ", "sobre ", "su ", "de ce", "bibliograph", "sekundär", "secondaire", "references", "références", "literatur")),
    (ContributionRole.TRANSLATOR, ("translations by", "translated by", "translations", "traductions", "traduction", "übersetzung", "ubersetzung", "traducciones", "traduzioni")),
    (ContributionRole.EDITOR, ("edited", "éditions", "herausgegeben", "herausgeber", "a cura")),
    (ContributionRole.CONTRIBUTOR, ("contributions", "contributed", "beiträge", "beitrage", "collaborations")),
    (ContributionRole.AUTHOR, ("works", "œuvres", "oeuvres", "werke", "schriften", "obras", "opere", "opera", "writings", "books", "poems", "poèmes", "gedichte", "essays", "letters", "lettres", "briefe")),
)


def classify_section(heading: str) -> str:
    text = fold(heading)
    if not text:
        return ContributionRole.UNKNOWN
    padded = f" {text} "
    for role, needles in _SECTION_RULES:
        for needle in needles:
            key = fold(needle)
            # Needles match at a word start; a trailing space marks a whole word, so "über " never
            # matches "Übersetzungen" and "zu " never matches inside another word.
            if key and (f" {key} " if needle.endswith(" ") else f" {key}") in padded:
                return role
    return ContributionRole.UNKNOWN


class _SectionLinkParser(HTMLParser):
    """Map each internal /wiki/ link in rendered author-page HTML to the nearest preceding heading."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading_level = 0
        self.heading_text: list[str] = []
        self.section = ""
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if re.fullmatch(r"h[2-6]", tag):
            self.heading_level = int(tag[1])
            self.heading_text = []
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("/wiki/"):
                title = unquote(href[len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                self.links.setdefault(title, self.section)

    def handle_endtag(self, tag: str) -> None:
        if self.heading_level and tag == f"h{self.heading_level}":
            self.section = " ".join("".join(self.heading_text).split())
            self.heading_level = 0

    def handle_data(self, data: str) -> None:
        if self.heading_level:
            self.heading_text.append(data)


def link_sections(html: str) -> dict[str, str]:
    parser = _SectionLinkParser()
    parser.feed(html)
    return parser.links


def collect_links(http: ProviderHttp, base: str, title: str, namespace: int = 0) -> tuple[list[str], bool]:
    """Every main-namespace page linked from ``title``, following API continuation to the end (bounded)."""
    params: dict[str, Any] = {"action": "query", "prop": "links", "titles": title, "plnamespace": namespace, "pllimit": "max", "format": "json", "formatversion": 2}
    titles: list[str] = []
    for _page in range(MAX_LINK_PAGES):
        http.check_cancelled()
        payload = http.get_json(f"{base}/w/api.php", params)
        for page in (payload.get("query") or {}).get("pages") or []:
            if page.get("missing"):
                raise CaptureError(CaptureErrorCode.SOURCE_NOT_FOUND, "The author page does not exist on this project.", detail=title)
            titles.extend(str(link.get("title")) for link in page.get("links") or [] if link.get("title"))
        cont = payload.get("continue")
        if not isinstance(cont, dict):
            return list(dict.fromkeys(titles)), True
        params = {**params, **{key: value for key, value in cont.items() if isinstance(value, str)}}
    return list(dict.fromkeys(titles)), False


def _work_root(title: str) -> str:
    return title.split("/", 1)[0]


def classify_author_links(
    linked: list[str], sections: dict[str, str]
) -> list[tuple[str, str, str]]:
    """(work title, role, section) per linked work root; a subpage link counts for its root only once."""
    out: dict[str, tuple[str, str, str]] = {}
    for title in linked:
        root = _work_root(title)
        section = sections.get(title) or sections.get(root) or ""
        role = classify_section(section) if section else ContributionRole.UNKNOWN
        if title != root and role == ContributionRole.AUTHOR:
            # "Encyclopedia/Entry" under Works is still an entry in someone else's collection.
            role = ContributionRole.UNKNOWN
        previous = out.get(root)
        if previous is None or (previous[1] == ContributionRole.UNKNOWN and role != ContributionRole.UNKNOWN):
            out[root] = (root if title == root else title, role, section)
    return list(out.values())


class WikisourceProvider:
    provider_id = "wikisource"

    def __init__(self, http: ProviderHttp) -> None:
        self.http = http
        self._namespaces: dict[str, dict[str, Any]] = {}

    def namespaces(self, code: str) -> dict[str, Any]:
        """Localized namespace ids for one project (Author/Page/Index ids differ per language)."""
        if code in self._namespaces:
            return self._namespaces[code]
        payload = self.http.get_json(
            f"{project_host(code)}/w/api.php",
            {"action": "query", "meta": "siteinfo|proofreadinfo", "siprop": "namespaces|namespacealiases", "piprop": "namespaces", "format": "json", "formatversion": 2},
        )
        query = payload.get("query") or {}
        names: dict[str, int] = {}
        for key, ns in (query.get("namespaces") or {}).items():
            for label in (ns.get("name"), ns.get("canonical")):
                if label:
                    names[fold(str(label))] = int(key)
        for alias in query.get("namespacealiases") or []:
            if alias.get("alias"):
                names[fold(str(alias["alias"]))] = int(alias.get("id", 0))
        proofread = (query.get("proofreadnamespaces") or {})
        info = {"by_name": names, "page": (proofread.get("page") or {}).get("id"), "index": (proofread.get("index") or {}).get("id")}
        self._namespaces[code] = info
        return info

    def author_pages(self, author: ResolvedAuthor, options: CaptureOptions) -> list[tuple[str, str, str]]:
        """(project code, author page title, evidence) — sitelinks first; nothing is guessed from names."""
        pages = [(code, title, "wikidata_sitelink") for code, title in sorted(author.wikisource_sitelinks.items())]
        if options.languages:
            pages = [page for page in pages if page[0] in options.languages]
        return pages

    def enumerate_author_sources(
        self, author: ResolvedAuthor, options: CaptureOptions, report: DiscoveryReport, progress: ProgressCallback
    ) -> Iterator[SourceCandidate]:
        pages = self.author_pages(author, options)
        if not pages:
            report.warnings = [*(report.warnings or []), "no_wikisource_sitelinks"]
        wanted_roles = {str(role) for role in options.roles}
        emitted = 0
        for index, (code, title, evidence) in enumerate(pages):
            self.http.check_cancelled()
            progress("discovering_wikisource", {"project": code, "done": index, "total": len(pages)})
            base = project_host(code)
            try:
                linked, complete = collect_links(self.http, base, title)
                _resolved, html, info = wikisource_parse(base, title, self.http)
            except CaptureError as exc:
                if exc.code == CaptureErrorCode.CANCELLED:
                    raise
                # One broken project never ends discovery for the others.
                report.errors = [*(report.errors or []), {"project": code, **exc.to_dict()}]
                continue
            report.projects_searched.append(code)
            report.identities_used.append(f"{code}:{title}")
            report.pagination_complete = report.pagination_complete and complete
            sections = link_sections(html)
            for work, role, section in classify_author_links(linked, sections):
                # Unknown-role links stay visible (deselected) for review; other roles follow the options.
                if role != ContributionRole.UNKNOWN and role not in wanted_roles:
                    continue
                if emitted >= options.max_candidates_per_provider:
                    report.warnings = [*(report.warnings or []), "candidate_limit_reached"]
                    return
                emitted += 1
                report.result_count += 1
                yield SourceCandidate(
                    provider=self.provider_id,
                    provider_item_id=f"{code}:{work}",
                    title=work,
                    source_uri=f"{base}/wiki/{quote(work.replace(' ', '_'))}",
                    contribution_role=role,
                    provider_author_identity=f"{code}:{title}",
                    document_author=author.canonical_name if role in {ContributionRole.AUTHOR, ContributionRole.COAUTHOR} else "",
                    # The project's language is where the transcription lives; it is also the language of the
                    # text on every Wikisource except the multilingual one. It is never taken as the work's original language.
                    document_languages=[code] if code != "mul" and normalize_language(code) else [],
                    source_project_language=code,
                    catalog_uri=f"{base}/wiki/{quote(title.replace(' ', '_'))}",
                    discovery_method="wikisource_author_page_links",
                    discovery_evidence={"author_page": title, "author_page_id": info.get("page_id"), "author_page_revision": info.get("revision_id"), "section": section, "author_page_evidence": evidence},
                    identity_confidence="exact" if role != ContributionRole.UNKNOWN else "needs_review",
                )
        progress("discovering_wikisource", {"done": len(pages), "total": len(pages)})

    def enrich_work_ids(self, candidates: list[SourceCandidate]) -> None:
        """Attach Wikidata item ids (via ``pageprops.wikibase_item``) in batched calls per project."""
        by_project: dict[str, list[SourceCandidate]] = {}
        for candidate in candidates:
            by_project.setdefault(str(candidate.source_project_language), []).append(candidate)
        for code, items in by_project.items():
            base = project_host(code)
            for start in range(0, len(items), 50):
                self.http.check_cancelled()
                chunk = items[start : start + 50]
                try:
                    payload = self.http.get_json(f"{base}/w/api.php", {"action": "query", "prop": "pageprops|info", "ppprop": "wikibase_item", "titles": "|".join(c.title for c in chunk), "redirects": 1, "format": "json", "formatversion": 2})
                except CaptureError as exc:
                    if exc.code == CaptureErrorCode.CANCELLED:
                        raise
                    continue
                query = payload.get("query") or {}
                renamed = {str(r.get("from")): str(r.get("to")) for r in (query.get("normalized") or []) + (query.get("redirects") or [])}
                pages = {str(p.get("title")): p for p in query.get("pages") or []}
                for candidate in chunk:
                    page = pages.get(renamed.get(candidate.title, candidate.title))
                    if not page or page.get("missing"):
                        continue
                    candidate.provider_page_id = page.get("pageid")
                    candidate.provider_revision_id = page.get("lastrevid")
                    item = (page.get("pageprops") or {}).get("wikibase_item")
                    if item:
                        candidate.wikidata_edition_id = str(item)

    def fetch_source(self, candidate: SourceCandidate, *, max_bytes: int) -> AcquiredSource:
        code = str(candidate.source_project_language or "")
        base = project_host(code)
        try:
            data, resolved, provenance = fetch_whole_work(base, candidate.title, max_bytes=max_bytes, http=self.http)
        except ValueError as exc:
            code_ = CaptureErrorCode.SOURCE_TOO_LARGE if "size limit" in str(exc) else CaptureErrorCode.ACQUISITION_FAILED
            raise CaptureError(code_, str(exc)) from exc
        provenance["proofread"] = self._proofread(base, code, [page["title"] for page in provenance["pages"]])
        scans, scan_warnings = self._scans(base, provenance, data)
        safe = re.sub(r"[^\w.\- ]+", "_", resolved).strip().replace(" ", "_") or "wikisource"
        root = provenance["pages"][0] if provenance["pages"] else {}
        return AcquiredSource(
            data=data,
            filename=f"{safe}.html",
            content_type="text/html; charset=utf-8",
            source_uri=candidate.source_uri,
            catalog_metadata={
                "provider": "wikisource",
                "title": resolved,
                "document_author": candidate.document_author,
                "language": (candidate.document_languages or [""])[0],
                "source_project_language": code,
                "wikisource_page_id": root.get("page_id"),
                "wikisource_revision_id": root.get("revision_id"),
                "wikisource_pages": provenance["pages"],
                "proofread": provenance["proofread"],
                "source_sha256": hashlib.sha256(data).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "document_type": "book",
                **({"scan_warnings": scan_warnings} if scan_warnings else {}),
            },
            scans=scans,
        )

    def _scans(self, base: str, provenance: dict[str, Any], data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
        proofread = provenance.get("proofread") if isinstance(provenance.get("proofread"), dict) else {}
        titles = [str(page.get("title") or "") for page in (proofread.get("pages") or [])]
        targets = scan_targets_from_titles(titles) or scan_targets_from_html(data.decode("utf-8", errors="replace"))
        if not targets:
            return [], []
        try:
            return fetch_wikisource_scans(self.http, base, targets)
        except Exception as exc:  # noqa: BLE001 - a missing scan must not drop the transcription
            return [], [f"scan_download_failed:{type(exc).__name__}"]

    def _proofread(self, base: str, code: str, titles: list[str]) -> dict[str, Any] | None:
        """ProofreadPage provenance (transcluded Page:/Index: ids and proofreading quality), when the project has it."""
        try:
            ns = self.namespaces(code)
        except CaptureError:
            return None
        if not ns.get("page"):
            return None
        pages: list[dict[str, Any]] = []
        for start in range(0, min(len(titles), 200), 50):
            chunk = titles[start : start + 50]
            try:
                payload = self.http.get_json(f"{base}/w/api.php", {"action": "query", "prop": "templates", "tlnamespace": ns["page"], "tllimit": "max", "titles": "|".join(chunk), "format": "json", "formatversion": 2})
            except CaptureError:
                return None
            for page in (payload.get("query") or {}).get("pages") or []:
                pages.extend({"title": t.get("title")} for t in page.get("templates") or [] if t.get("title"))
        if not pages:
            return None
        scan_pages = list({p["title"]: p for p in pages}.values())[:500]
        quality: dict[str, Any] = {}
        for start in range(0, len(scan_pages), 50):
            chunk = [p["title"] for p in scan_pages[start : start + 50]]
            try:
                payload = self.http.get_json(f"{base}/w/api.php", {"action": "query", "prop": "proofread|info", "titles": "|".join(chunk), "format": "json", "formatversion": 2})
            except CaptureError:
                break
            for page in (payload.get("query") or {}).get("pages") or []:
                quality[str(page.get("title"))] = {"page_id": page.get("pageid"), "revision_id": page.get("lastrevid"), "quality": (page.get("proofread") or {}).get("quality_text")}
        indexes = sorted({str(p["title"]).split(":", 1)[-1].rsplit("/", 1)[0] for p in scan_pages})
        return {"page_count": len(scan_pages), "indexes": indexes, "pages": [{"title": p["title"], **quality.get(p["title"], {})} for p in scan_pages]}
