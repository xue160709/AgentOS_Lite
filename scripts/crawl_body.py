"""Optional isolated Crawl4AI adapter. JSON file handoff keeps stdout diagnostics separate."""
import asyncio
import json
import sys
from pathlib import Path


async def main(url, output):
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url, config=CrawlerRunConfig(
            page_timeout=25000, cache_mode=CacheMode.BYPASS, verbose=False))
        if not result.success:
            raise RuntimeError(result.error_message)
        markdown = result.markdown
        text = markdown.raw_markdown if hasattr(markdown, 'raw_markdown') else str(markdown)
        Path(output).write_text(json.dumps({'text': text, 'status_code': result.status_code}), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1], sys.argv[2]))
