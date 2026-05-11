#!/usr/bin/env python3
"""
AHS - Web Search Tool
=====================
باحث ويب حقيقي — يستخدم DuckDuckGo API (مجاني، بدون مفتاح API).

الميزات:
  - بحث في الويب (DuckDuckGo)
  - جلب محتوى صفحة URL
  - استخراج النص من HTML
  - ذاكرة مؤقتة للنتائج (LRU cache)

الاعتماديات:
  - requests (موجود)
  - BeautifulSoup4 (اختياري — يعمل بدونه)
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# تثبيت beautifulsoup4 إذا لم يكن موجوداً
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger("ahs.web_search")

# ─── ثوابت ────────────────────────────────────────────────────
CACHE_SIZE = 50
CACHE_TTL = 300  # 5 دقائق
REQUEST_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ─── ذاكرة مؤقتة ───────────────────────────────────────────────

class LRUCache:
    """LRU cache بسيط مع TTL"""
    def __init__(self, max_size: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}  # key → (timestamp, value)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        if time.time() - ts > self.ttl:
            del self._cache[key]
            return None
        # Move to end (mark as recently used)
        del self._cache[key]
        self._cache[key] = (ts, value)
        return value

    def set(self, key: str, value: Any):
        if len(self._cache) >= self.max_size:
            # Remove oldest
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest]
        self._cache[key] = (time.time(), value)

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# ─── أدوات بحث ويب ────────────────────────────────────────────

class WebSearchTool:
    """
    Web Search Tool — بحث حقيقي في الويب.

    المصادر:
      - DuckDuckGo HTML search (مجاني، بدون API key)
      - DuckDuckGo Instant Answer API
      - Fetch URL للحصول على محتوى الصفحة
    """

    def __init__(self):
        self.cache = LRUCache()
        self.call_count = 0
        self.error_count = 0

    def search(self, query: str, max_results: int = 5, region: str = "wt-wt") -> Dict:
        """
        بحث في الويب عبر DuckDuckGo.

        Args:
            query: مصطلحات البحث
            max_results: أقصى عدد نتائج (1-10)
            region: منطقة البحث (wt-wt = عالمي)

        Returns:
            Dict: {"success": bool, "results": [...], "total": int, "query": str}
        """
        self.call_count += 1
        cache_key = f"search:{query}:{max_results}:{region}"

        # 1. Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"📦 Cache hit: {query[:50]}...")
            return cached

        start = time.time()
        logger.info(f"🔍 Searching: {query[:80]}...")

        # 2. Try DuckDuckGo Instant Answer API first
        results = self._search_duckduckgo_api(query)

        # 3. Fallback: try DuckDuckGo HTML search
        if not results:
            results = self._search_duckduckgo_html(query)

        # 4. Limit results
        results = results[:max_results]

        elapsed = round(time.time() - start, 2)
        response = {
            "success": len(results) > 0,
            "results": results,
            "total": len(results),
            "query": query,
            "elapsed": elapsed,
        }

        # Cache the result
        self.cache.set(cache_key, response)
        logger.info(f"✅ Search complete: {len(results)} results in {elapsed}s")
        return response

    def _search_duckduckgo_api(self, query: str) -> List[Dict]:
        """
        DuckDuckGo Instant Answer API.
        يعطي إجابات فورية ونتائج محدودة.
        """
        if not HAS_REQUESTS:
            logger.warning("requests module not available")
            return []

        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            }
            resp = requests.get(
                url, params=params, timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT}
            )
            resp.raise_for_status()
            data = resp.json()

            results = []

            # Abstract (answer)
            abstract = data.get("AbstractText", "")
            abstract_source = data.get("AbstractSource", "")
            abstract_url = data.get("AbstractURL", "")
            if abstract:
                results.append({
                    "title": abstract_source or "DuckDuckGo Answer",
                    "url": abstract_url,
                    "snippet": abstract[:500],
                    "source": "duckduckgo_api",
                })

            # Related topics
            for topic in data.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic.get("Text", "").split(" - ")[0] or topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")[:500],
                        "source": "duckduckgo_api",
                    })
                elif "Topics" in topic:
                    for sub in topic.get("Topics", [])[:3]:
                        if "Text" in sub and "FirstURL" in sub:
                            results.append({
                                "title": sub.get("Text", "").split(" - ")[0] or sub.get("Text", ""),
                                "url": sub.get("FirstURL", ""),
                                "snippet": sub.get("Text", "")[:500],
                                "source": "duckduckgo_api",
                            })

            return results

        except requests.RequestException as e:
            logger.warning(f"DuckDuckGo API failed: {e}")
            return []
        except Exception as e:
            logger.warning(f"DuckDuckGo API error: {e}")
            return []

    def _search_duckduckgo_html(self, query: str) -> List[Dict]:
        """
        DuckDuckGo HTML search (fallback).
        أفضل للحصول على نتائج كاملة.
        """
        if not HAS_REQUESTS:
            return []

        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}
            resp = requests.post(
                url, data=data, timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )
            resp.raise_for_status()

            results = []

            if HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")
                for result in soup.select(".result")[:10]:
                    title_elem = result.select_one(".result__title a")
                    snippet_elem = result.select_one(".result__snippet")

                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": title_elem.get("href", ""),
                            "snippet": snippet_elem.get_text(strip=True)[:500]
                            if snippet_elem else "",
                            "source": "duckduckgo_html",
                        })
            else:
                # Manual HTML extraction (fallback)
                # Extract URLs and titles from <a> tags with result__a class
                links = re.findall(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
                    resp.text
                )
                snippets = re.findall(
                    r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>',
                    resp.text
                )
                for i, (url, title) in enumerate(links[:10]):
                    snippet = snippets[i] if i < len(snippets) else ""
                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "snippet": snippet[:500],
                        "source": "duckduckgo_html",
                    })

            return results

        except requests.RequestException as e:
            logger.warning(f"DuckDuckGo HTML search failed: {e}")
            return []
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML error: {e}")
            return []

    def fetch_url(self, url: str, timeout: int = 15) -> Dict:
        """
        جلب محتوى صفحة URL.

        Args:
            url: رابط الصفحة
            timeout: مهلة الاستجابة بالثواني

        Returns:
            Dict: {"success": bool, "url": str, "title": str,
                   "content": str, "text_length": int}
        """
        self.call_count += 1
        cache_key = f"fetch:{url}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"📦 Cache hit: {url[:60]}...")
            return cached

        start = time.time()

        if not HAS_REQUESTS:
            return {"success": False, "error": "requests module not available",
                    "url": url}

        try:
            resp = requests.get(
                url, timeout=timeout,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True
            )
            resp.raise_for_status()

            # Extract title
            title = ""
            content = ""

            if HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove scripts, styles, nav, footer
                for tag in soup(["script", "style", "nav", "footer",
                                 "header", "aside", "noscript"]):
                    tag.decompose()

                title = soup.title.get_text(strip=True) if soup.title else ""
                # Get main content
                main = soup.find("main") or soup.find("article") or soup.find("body")
                if main:
                    content = main.get_text(separator="\n", strip=True)
                else:
                    content = soup.get_text(separator="\n", strip=True)
            else:
                # Manual: extract title
                title_match = re.search(r'<title>([^<]*)</title>', resp.text, re.IGNORECASE)
                title = title_match.group(1) if title_match else url
                # Remove HTML tags for content
                content = re.sub(r'<[^>]+>', ' ', resp.text)
                content = re.sub(r'\s+', ' ', content).strip()

            # Limit content length
            if len(content) > 5000:
                content = content[:5000] + "\n... [مقتطع]"

            elapsed = round(time.time() - start, 2)
            response = {
                "success": True,
                "url": url,
                "title": title[:200],
                "content": content,
                "text_length": len(content),
                "status_code": resp.status_code,
                "elapsed": elapsed,
            }

            self.cache.set(cache_key, response)
            logger.info(f"✅ Fetched: {title[:50]} ({elapsed}s)")
            return response

        except requests.Timeout:
            self.error_count += 1
            return {"success": False, "url": url, "error": "Timeout",
                    "elapsed": timeout}
        except requests.RequestException as e:
            self.error_count += 1
            return {"success": False, "url": url, "error": str(e)[:200]}
        except Exception as e:
            self.error_count += 1
            return {"success": False, "url": url, "error": str(e)[:200]}

    def google_search(self, query: str, max_results: int = 5) -> Dict:
        """
        بحث عبر Google (بدون API — يستخدم scraping).
        ملاحظة: قد لا يعمل دائماً بدون حلول anti-bot.

        Args:
            query: مصطلحات البحث
            max_results: أقصى عدد نتائج

        Returns:
            Dict: نتائج البحث
        """
        self.call_count += 1
        cache_key = f"google:{query}:{max_results}"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        start = time.time()
        logger.info(f"🔍 Google search: {query[:60]}...")

        if not HAS_REQUESTS:
            return {"success": False, "error": "requests not available"}

        try:
            url = "https://www.google.com/search"
            params = {"q": query, "hl": "en"}
            resp = requests.get(
                url, params=params, timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT}
            )
            resp.raise_for_status()

            results = []

            if HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")
                for g in soup.select("div.g")[:max_results]:
                    title_elem = g.select_one("h3")
                    link_elem = g.select_one("a")
                    snippet_elem = g.select_one(".VwiC3b")

                    if title_elem and link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith("/url?q="):
                            href = href.split("/url?q=")[1].split("&")[0]
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": href,
                            "snippet": snippet_elem.get_text(strip=True)[:500]
                            if snippet_elem else "",
                            "source": "google",
                        })

            elapsed = round(time.time() - start, 2)
            response = {
                "success": len(results) > 0,
                "results": results,
                "total": len(results),
                "query": query,
                "elapsed": elapsed,
            }
            self.cache.set(cache_key, response)
            return response

        except requests.RequestException as e:
            self.error_count += 1
            return {"success": False, "error": str(e)[:200]}
        except Exception as e:
            self.error_count += 1
            return {"success": False, "error": str(e)[:200]}

    def multi_search(self, query: str, max_results: int = 5) -> Dict:
        """
        بحث متعدد المصادر — يجمع DuckDuckGo + Google + Fetch.
        """
        combined_results = []
        seen_urls = set()

        # 1. DuckDuckGo
        ddg = self.search(query, max_results=max_results)
        for r in ddg.get("results", []):
            url = r.get("url", "")
            if url and url not in seen_urls:
                combined_results.append(r)
                seen_urls.add(url)

        # 2. Google (إذا نجح)
        google = self.google_search(query, max_results=max_results)
        for r in google.get("results", []):
            url = r.get("url", "")
            if url and url not in seen_urls:
                combined_results.append(r)
                seen_urls.add(url)

        return {
            "success": len(combined_results) > 0,
            "results": combined_results[:max_results],
            "total": len(combined_results),
            "query": query,
            "sources": ["duckduckgo", "google"],
        }

    def status(self) -> Dict:
        """حالة الأداة"""
        return {
            "name": "web_search_tool",
            "calls": self.call_count,
            "errors": self.error_count,
            "cache_size": self.cache.size,
            "has_bs4": HAS_BS4,
            "has_requests": HAS_REQUESTS,
        }


# ====== دالة واحدة للاستخدام المباشر ======

_web_search_instance = None

def get_web_search() -> WebSearchTool:
    """Get or create the singleton WebSearchTool instance."""
    global _web_search_instance
    if _web_search_instance is None:
        _web_search_instance = WebSearchTool()
    return _web_search_instance


def web_search(query: str, max_results: int = 5) -> Dict:
    """
    استدعاء بسيط للبحث — ينفع يستخدم من أي مكان.

    Args:
        query: مصطلحات البحث
        max_results: عدد النتائج (1-10)

    Returns:
        Dict: {"success": bool, "results": [...], "query": str}
    """
    return get_web_search().search(query, max_results=max_results)


def fetch_url(url: str) -> Dict:
    """
    جلب محتوى URL.

    Args:
        url: رابط الصفحة

    Returns:
        Dict: {"success": bool, "title": str, "content": str, ...}
    """
    return get_web_search().fetch_url(url)


# ─── اختبار ────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 50)
    print("  🧪 Web Search Tool — اختبار")
    print("=" * 50)

    tool = WebSearchTool()

    # اختبار البحث
    print("\n📌 اختبار 1: بحث DuckDuckGo")
    r = tool.search("AI agents 2026 best practices")
    print(f"  ✅ {r['total']} نتائج في {r.get('elapsed', 0)}s")
    for i, res in enumerate(r.get("results", [])[:3], 1):
        print(f"  {i}. {res['title'][:60]}")
        print(f"     {res['url'][:70]}")

    # اختبار جلب URL
    if r.get("results"):
        url = r["results"][0]["url"]
        print(f"\n📌 اختبار 2: جلب URL — {url[:50]}")
        r2 = tool.fetch_url(url)
        if r2["success"]:
            print(f"  ✅ العنوان: {r2['title'][:60]}")
            print(f"  📝 {r2['text_length']} حرف")
        else:
            print(f"  ❌ {r2.get('error')}")

    # اختبار متعدد المصادر
    print("\n📌 اختبار 3: Multi-Search")
    r3 = tool.multi_search("Python async web scraping", max_results=3)
    print(f"  ✅ {r3['total']} نتائج من {r3['sources']}")
    for i, res in enumerate(r3.get("results", [])[:3], 1):
        print(f"  {i}. {res['title'][:60]}")

    print(f"\n📊 الحالة: {tool.status()}")
    print("\n✅ اختبار Web Search Tool اكتمل")
