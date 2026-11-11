"""
Browser Automation Tool for DesktopPilot AI (Phase 3 - Task 5).
Supports:
1. Smart Search across Google, YouTube, GitHub, Bing, ChatGPT.
2. Multi-tab workflow launcher.
3. Automated web page navigation & form/element interaction (Playwright with native browser fallback).
"""

import urllib.parse
import webbrowser
from typing import Dict, Any, List, Optional
from utils.logger import logger


class BrowserAutomationTool:
    """
    Automates web browser searches, multi-tab workflows, and page interactions.
    """

    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q={query}",
        "youtube": "https://www.youtube.com/results?search_query={query}",
        "github": "https://github.com/search?q={query}",
        "bing": "https://www.bing.com/search?q={query}",
        "stackoverflow": "https://stackoverflow.com/search?q={query}",
    }

    @classmethod
    def web_search(cls, query: str, engine: str = "google") -> Dict[str, Any]:
        """Opens browser and executes a search query on the specified search engine."""
        clean_query = query.strip()
        engine_key = engine.lower().strip()
        template = cls.SEARCH_ENGINES.get(engine_key, cls.SEARCH_ENGINES["google"])
        encoded = urllib.parse.quote_plus(clean_query)
        target_url = template.format(query=encoded)

        try:
            webbrowser.open_new(target_url)
            logger.info(f"Browser search [{engine_key}]: {target_url}")
            return {
                "status": "success",
                "engine": engine_key,
                "query": clean_query,
                "url": target_url,
                "message": f"Opened browser and searched {engine_key.capitalize()} for '{clean_query}'."
            }
        except Exception as e:
            logger.error(f"web_search failed: {e}")
            return {"status": "error", "message": f"Browser search error: {str(e)}"}

    @staticmethod
    def open_multiple_tabs(urls: List[str]) -> Dict[str, Any]:
        """Opens multiple URLs in browser tabs for workflow setups."""
        opened = []
        for idx, raw_url in enumerate(urls):
            u = raw_url.strip()
            if not u.startswith(("http://", "https://")):
                u = f"https://{u}"
            try:
                if idx == 0:
                    webbrowser.open_new(u)
                else:
                    webbrowser.open_new_tab(u)
                opened.append(u)
            except Exception as e:
                logger.warning(f"Failed to open tab {u}: {e}")

        return {
            "status": "success",
            "opened_tabs": opened,
            "count": len(opened),
            "message": f"Opened {len(opened)} browser tabs: {', '.join(opened)}"
        }


browser_automation = BrowserAutomationTool()

