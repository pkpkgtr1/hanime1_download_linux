import asyncio
from playwright.async_api import async_playwright
import mypkg
import time
class PageFetcher:
    def __init__(self, headless: bool = True, user_agent: str = None):
        self.headless = headless
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.playwright = None
        self.browser = None

    async def _init_browser(self):
        """初始化浏览器"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    f"--user-agent={self.user_agent}",
                ],
            )

    async def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def fetch(self, url: str, scroll: bool = True, scroll_pause: int = 2000) -> str:
        """
        获取网页源码，可选滚动加载
        :param url: 网页 URL
        :param scroll: 是否模拟滚动加载
        :param scroll_pause: 每次滚动等待时间（毫秒）
        :return: 网页源码
        """
        await self._init_browser()
        page = await self.browser.new_page()
        try:
            await page.goto(url, timeout=30000)

            if scroll:
                last_height = await page.evaluate("document.body.scrollHeight")
                while True:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(scroll_pause)

                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

            content = await page.content()
            await page.close()
            return content
        finally:
            await page.close()

    async def close(self):
        """手动关闭浏览器"""
        await self._close_browser()

async def main(url):
    fetcher = PageFetcher()
    html = await fetcher.fetch(url)
    #print(html)  # 打印前1000字符检查
    await fetcher.close()
    return html


'''
class playwright_html:

    def get_html(self, url: str) -> str:
        try:
            html=asyncio.run(main(url))
            return html
            time.sleep(1)
            mypkg.logger.info(f"✅ {url}成功解析")
        except Exception as e:
            mypkg.logger.error(f"❌ {url}超时或执行失败")
            mypkg.logger.debug(f"🐞 {url}执行失败错误代码：" + str(e))
            return ''
'''

class playwright_html:

    def get_html(self, url: str) -> str:
        max_retries = 8
        for attempt in range(1, max_retries + 1):
            try:
                html = asyncio.run(main(url))
                mypkg.logger.info(f"✅ [第{attempt}/{max_retries}次尝试]{url} 成功解析 ")
                return html
            except Exception as e:
                mypkg.logger.error(f"❌ [第{attempt}/{max_retries}次尝试]{url} 解析失败 ")
                mypkg.logger.debug(f"🐞 错误代码：{str(e)}")
                if attempt < max_retries:
                    time.sleep(10)  # 失败后等待 10 秒再重试

