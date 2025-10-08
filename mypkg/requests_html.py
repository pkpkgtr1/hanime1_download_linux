import requests
import json
import mypkg
import time
class requests_html:

    def get_html(self, url: str) -> str:
        max_retries = 8
        #填写FlareSolverr地址
        FlareSolverr_url = "http://localhost:8191/v1"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/128.0.0.0 Safari/537.36"}
        data = {
            "cmd": "request.get",
            "session": 110,
            "url": url,
            "maxTimeout": 60000
        }
        for attempt in range(1, max_retries + 1):
            try:

                response = requests.post(FlareSolverr_url, headers=headers, json=data)
                html=json.loads(response.text)['solution']['response']
                mypkg.logger.info(f"✅ [第{attempt}/{max_retries}次尝试]{url} 成功解析 ")
                return html
            except Exception as e:
                mypkg.logger.error(f"❌ [第{attempt}/{max_retries}次尝试]{url} 解析失败 ")
                mypkg.logger.debug(f"🐞 错误代码：{str(e)}")
                if attempt < max_retries:
                    time.sleep(10)  # 失败后等待 10 秒再重试