import subprocess
import mypkg
from lxml import html
class LightPanda_html:
    def __init__(self, binary_path="timeout 60s ./lightpanda"):
        self.binary_path = binary_path

    def get_html(self, url: str) -> str:
        cmd = f'{self.binary_path} fetch --dump "{url}"'
        try:
            resp = subprocess.getoutput(cmd)
            lines = resp.split("\n")
            _html = []
            for idx, line in enumerate(lines):
                if line.startswith("info") or line.startswith("warning") or "(browser)" in line:
                    continue
                else:
                    _html = lines[idx:]
                    break
            if 'error(cli)' in _html[0]:
                mypkg.logger.error("❌️ 未解析到有效 HTML 内容,请检测🪜网络")
                #raise ValueError("未解析到有效 HTML 内容")
                return ''
            mypkg.logger.info("✅ 成功开始解析")
            return "\n".join(_html)
        except Exception as e:
            mypkg.logger.error("❌ LightPanda超时或执行失败")
            mypkg.logger.debug("🐞 LightPanda执行失败错误代码：" + str(e))
            return ''
            #return f"访问出错: {e}"
