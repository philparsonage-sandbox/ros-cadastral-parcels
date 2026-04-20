"""Playwright-based downloader for https://ros-inspire.themapcloud.com/."""

import json
import sys
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    Browser,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

TARGET_URL = "https://ros-inspire.themapcloud.com/"

# TODO - check download terms
_JS_FIND_TERMS_BOX = """() => {
    const allCheckboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
    const termsBox = allCheckboxes.find(el => {
        const label = (el.labels?.[0]?.innerText || el.getAttribute('aria-label') || '').toLowerCase();
        const nearby = el.closest('label')?.innerText?.toLowerCase() || '';
        return label.includes('term') || label.includes('agree') || label.includes('licence') ||
               nearby.includes('term') || nearby.includes('agree') || nearby.includes('licence');
    });
    if (termsBox && !termsBox.checked) { termsBox.click(); return true; }
    return !!termsBox;
}"""

_JS_CLICK_SUBMIT = """() => {
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'));
    const btn = btns.find(el => {
        const t = (el.innerText || el.value || '').toLowerCase();
        return t.includes('submit') || t.includes('download') || t.includes('request');
    });
    if (btn) { btn.click(); return btn.innerText || btn.value; }
    return null;
}"""


def _launch_browser(p: Playwright) -> tuple[Browser, Page]:
    """Launch a headless Chromium browser with downloads enabled.

    Returns a (Browser, Page) tuple ready for navigation.
    """
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    return browser, page


def _wait_for_page_ready(page: Page, download_dir: str | Path) -> None:
    """Navigate to TARGET_URL and wait for the React app to finish loading."""
    print(f"Navigating to {TARGET_URL}...")
    page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

    print("Waiting for dataset list to load...")
    try:
        page.wait_for_function(
            "() => !document.body.innerText.includes('Loading...')",
            timeout=30000,
        )
    except PlaywrightTimeoutError:
        print("Timed out waiting for 'Loading...' to clear — proceeding anyway")

    # Give React/Next.js a moment to fully render
    page.wait_for_timeout(3000)

    page.screenshot(path=str(Path(download_dir) / "_page_loaded.png"), full_page=True)
    print("Saved screenshot: _page_loaded.png")

    page_text = page.evaluate("() => document.body.innerText")
    (Path(download_dir) / "_page_text.txt").write_text(page_text)
    print("Saved page text: _page_text.txt")


def _log_page_structure(page: Page, download_dir: str | Path) -> None:
    """Scrape and print the interactive elements on the page for debugging."""
    dataset_info = page.evaluate("""() => {
        const result = { checkboxes: [], selects: [], links: [], buttons: [] };
        document.querySelectorAll('input[type="checkbox"]').forEach(el => {
            result.checkboxes.push({
                id: el.id, name: el.name, value: el.value, checked: el.checked,
                label: el.labels?.[0]?.innerText || el.getAttribute('aria-label') || '',
            });
        });
        document.querySelectorAll('select').forEach(el => {
            const options = Array.from(el.options).map(o => ({ value: o.value, text: o.text }));
            result.selects.push({ id: el.id, name: el.name, options });
        });
        document.querySelectorAll('a').forEach(el => {
            const href = el.href || '';
            if (href.match(/\\.(zip|gz|gml|xml|json|geojson|gpkg|shp|csv)/i) ||
                el.download || el.innerText.toLowerCase().includes('download')) {
                result.links.push({ href, text: el.innerText.trim(), download: el.download });
            }
        });
        document.querySelectorAll('button, input[type="submit"], input[type="button"]').forEach(el => {
            result.buttons.push({ text: el.innerText || el.value, type: el.type, id: el.id });
        });
        return result;
    }""")

    print("\n=== Page structure ===")
    print(f"Checkboxes: {len(dataset_info['checkboxes'])}")
    for c in dataset_info["checkboxes"]:
        label = c.get("label") or c.get("name") or c.get("value", "")
        print(f"  [{'x' if c.get('checked') else ' '}] {label} (id={c.get('id')})")
    print(f"Selects: {len(dataset_info['selects'])}")
    print(f"Download links: {len(dataset_info['links'])}")
    for lnk in dataset_info["links"]:
        print(f"  {lnk.get('text')} -> {lnk.get('href')}")
    print(f"Buttons: {len(dataset_info['buttons'])}")
    for btn in dataset_info["buttons"]:
        print(f"  [{btn.get('type')}] \"{btn.get('text')}\" id={btn.get('id')}")

    (Path(download_dir) / "_page_structure.json").write_text(
        json.dumps(dataset_info, indent=2)
    )


def _get_dataset_options(page: Page, browser: Browser) -> list[dict[str, str]]:
    """Return the list of {value, text} options from #file-to-download, or exit."""
    options = page.evaluate(
        """() => Array.from(document.querySelectorAll('#file-to-download option'))
            .map(o => ({ value: o.value, text: o.text.trim() }))
            .filter(o => o.value)"""
    )

    if not options:
        print(
            "No options found in #file-to-download — check _page_structure.json",
            file=sys.stderr,
        )
        browser.close()
        sys.exit(1)

    print(f"\nFound {len(options)} dataset(s) in #file-to-download:")
    for i, o in enumerate(options):
        print(f"  {i + 1}. {o['text']} (value=\"{o['value']}\")")

    return options


def _accept_terms(page: Page) -> None:
    """Tick the terms & conditions checkbox if present."""
    accepted = page.evaluate(_JS_FIND_TERMS_BOX)
    if accepted:
        print("Terms & conditions checkbox accepted")


def _download_option(
    page: Page, option: dict[str, str], index: int, total: int, download_dir: str | Path
) -> str | None:
    """Select one dataset option, re-accept terms if needed,
    and trigger the download.

    Returns the saved file path, or None if the download was skipped or failed.
    """
    value, text = option["value"], option["text"]
    print(f"\n[{index}/{total}] Selecting: {text}")

    page.select_option("#file-to-download", value)
    page.wait_for_timeout(300)

    # Some sites reset the terms checkbox on option change — re-check if needed
    page.evaluate(_JS_FIND_TERMS_BOX)

    has_submit = page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'));
        return !!btns.find(el => {
            const t = (el.innerText || el.value || '').toLowerCase();
            return t.includes('submit') || t.includes('download') || t.includes('request');
        });
    }""")

    if not has_submit:
        print("  No submit button found — skipping")
        return None

    try:
        with page.expect_download(timeout=120000) as download_info:
            page.evaluate(_JS_CLICK_SUBMIT)
        download = download_info.value
    except PlaywrightTimeoutError as exc:
        print(f"  Download wait failed: {exc}")
        return None

    dest = Path(download_dir) / download.suggested_filename
    download.save_as(str(dest))
    size = dest.stat().st_size if dest.exists() else 0
    print(f"  Saved: {dest} ({size / 1024:.1f} KB)")
    return str(dest)


def download_files(download_dir: str | Path) -> list[str]:
    """Download all datasets from TARGET_URL via Playwright.

    Navigates to the ROS Inspire site, iterates through every option in the
    #file-to-download select, accepts the terms checkbox, clicks submit, and
    saves each file to download_dir.

    Returns a list of saved file paths.
    """
    print(f"Starting scraper. Downloads will be saved to: {download_dir}")
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser, page = _launch_browser(p)

        _wait_for_page_ready(page, download_dir)
        _log_page_structure(page, download_dir)

        options = _get_dataset_options(page, browser)
        _accept_terms(page)

        saved_files = []
        for i, option in enumerate(options):
            path = _download_option(page, option, i + 1, len(options), download_dir)
            if path:
                saved_files.append(path)

        browser.close()
        return saved_files
