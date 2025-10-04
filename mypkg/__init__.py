import os
import logging
import colorlog
import shutil

class EnvInit:
    """环境初始化：检测并创建目录，并清空 tmp"""

    def __init__(self, folders=None):
        if folders is None:
            folders = ["tmp", "tmp/videos_nfo_jpg"]
        self.folders = folders

    def setup(self):
        # 每次先清空 tmp 目录
        tmp_root = "tmp/videos_nfo_jpg"
        if os.path.exists(tmp_root):
            shutil.rmtree(tmp_root)
            print(f"初始化: 已清空 {tmp_root} 目录")

        # 再创建所需目录
        for folder in self.folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"初始化: 已创建目录 {folder}")
        return self


class LoggerFactory:
    """彩色日志工厂"""

    def __init__(self, name="mypkg", level=logging.DEBUG):
        self.name = name
        self.level = level

    def get_logger(self):
        log_colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }

        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors=log_colors
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger = logging.getLogger(self.name)
        # 避免重复添加 handler
        if not logger.handlers:
            logger.addHandler(handler)
        logger.setLevel('INFO')

        return logger


class Page:
    """页码解析：把范围字符串转为列表"""

    def __init__(self, expr: str):
        self.expr = expr.strip()

    def to_list(self):
        if "-" in self.expr:  # 区间
            start, end = map(int, self.expr.split("-"))
            return list(range(start, end + 1))
        else:  # 单个数字
            return [int(self.expr)]


# 默认执行：初始化目录 + 提供默认 logger
#_env = EnvInit().setup()
logger = LoggerFactory().get_logger()

__all__ = ["EnvInit", "LoggerFactory", "Page", "logger"]