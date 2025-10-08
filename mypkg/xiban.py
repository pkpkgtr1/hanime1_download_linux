import sqlite3
import os
import time
from tqdm import tqdm
from mypkg.hanime_info import videos_nfo_jpg,hanime1_id_info,sx_tags_db
import mypkg
import re
import datetime
from mypkg.playwright_html import playwright_html
from lxml import html
from mypkg.requests_html import requests_html

#需要洗版的里番id
def xb_data_db(table_name):
    """
    获取指定数据库表中的所有数据。

    Args:
        table_name (str): 表名。

    Returns:
        list: 包含表中所有记录的列表，每个记录是一个元组。
    """
    try:
        # 连接数据库
        conn = sqlite3.connect("./db/hanime1.db")
        # 创建游标对象
        cursor = conn.cursor()
        # 执行查询，获取所有记录
        cursor.execute(f"SELECT * FROM '{table_name}' Where (name_cn like '%[中字後補]%' or resolution in ('720p','480p')) and sfxz='1'")
        # 提取所有记录
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        mypkg.logger.error(f"❌️ xb_data_db错误：{e}")
        return []
    finally:
        # 确保关闭连接
        if 'conn' in locals():
            conn.close()


def xb_data_db_update(table_name,lfid, new_name_cn,resolution):
    """
    更新指定数据库表中符合条件的数据（同时更新 sfxz, name_cn, name_jp）。

    Args:
        table_name (str): 表名。
        new_sfxz (str): 更新后的 sfxz 值。
        new_name_cn (str): 更新后的 name_cn 值。
        new_name_jp (str): 更新后的 name_jp 值。

    Returns:
        int: 被更新的记录数。
    """
    try:
        conn = sqlite3.connect("./db/hanime1.db")
        cursor = conn.cursor()
        # 执行更新
        cursor.execute(
            f"""
            UPDATE '{table_name}'
            SET sfxz = NULL, 
                name_cn = ?, 
                name_jp = REPLACE(name_jp, '中字後補', '中文字幕'),
                resolution= ?
            WHERE (name_cn LIKE '%[中字後補]%' OR resolution IN ('720p', '480p'))
              AND sfxz = '1' AND id='{lfid}'
            """,
            (new_name_cn,resolution)
        )
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        mypkg.logger.error(f"❌️ xb_data_db_update错误：{e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()



def get_hanime1_download(LFID):
    fetcher = requests_html()
    mypkg.logger.info(f"⏳ 正在获取https://hanime1.me/download?v={LFID}")
    html = fetcher.get_html(f"https://hanime1.me/download?v={LFID}")

    if html:
        if len(html) < 400:
            mypkg.logger.error("❌️"+html)
        else:
            mypkg.logger.debug("🐞 获取的html源码为：" + html)
            mypkg.logger.info("🔄 开始解析下载页html源文件")
            return html

def safe_filename_for_linux(name):
    char_map = {
        '!': '！',  # 全角感叹号 (FF01)
        '?': '？',  # 全角问号 (FF1F)
        '<': '＜',  # 全角小于号 (FF1C)
        '>': '＞',  # 全角大于号 (FF1E)
        ':': '：',  # 全角冒号 (FF1A)
        '"': '＂',  # 全角双引号 (FF02)
        '|': '｜',  # 全角竖线 (FF5C)
        '\\': '＼', # 全角反斜线 (FF3C)
        '/': '／',  # 全角斜线 (FF0F)
        '*': '＊',  # 全角星号 (FF0A)
        # ' ': '_',
    }

    for half, full in char_map.items():
        name = name.replace(half, full)

    safe_name = ''
    for char in name:
        if 0 <= ord(char) <= 31:
            safe_name += '_'
        else:
            safe_name += char

    return safe_name

def download_move_info(page):

    tree = html.fromstring(page)
    LF_NAME_XP = tree.xpath('//*[@id="content-div"]/div[1]/div[4]/div/div/h3/text()')
    LF_ZL= tree.xpath("//table[@class='download-table']/tbody/tr[contains(@style, 'text-align: center;')]/td[2]/text()")
    #LF_DOWNLOAD_URL= tree.xpath('//*[@id="content-div"]/div[1]/div[4]/div/div/table/tbody/tr[2]/td[5]/a')
    LF_DOWNLOAD_URL= tree.xpath('//a[contains(@class, "exoclick-popunder") and contains(@class, "juicyads-popunder")]')
    rq_info=[]

    data_urls = []
    for a_tag in LF_DOWNLOAD_URL:
        data_url = a_tag.get('data-url')
        if data_url:
            data_urls.append(data_url)
    return LF_NAME_XP,data_urls

#洗版删除文件
def delete_files_with_keyword(directory, keyword):
    """
    删除指定目录下文件名包含指定关键字的文件。

    Args:
        directory (str): 目录路径
        keyword (str): 关键字（默认 "中字後補"）
    """
    deleted_files = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if keyword in file:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        mypkg.logger.info(f"✅ 已删除: {file_path}")
                    except Exception as e:
                        mypkg.logger.info(f"❌ 删除失败: {file_path}, 错误: {e}")
        return deleted_files
    except Exception as e:
        mypkg.logger.error(f"❌ 程序出错: {e}")
        return []


def xb_main(NY, save_file):
    data_list = list(xb_data_db(NY))  # 先拿到所有数据，方便获取总数
    total = len(data_list)

    for idx, x in enumerate(data_list, start=1):
        try:
            pattern = r"-([^.]*)\."
            lf_id = x[0]
            download_html = get_hanime1_download(lf_id)
            download_info = download_move_info(download_html)
            lf_cn_name = safe_filename_for_linux(download_info[0][0])
            lf_cn_url = download_info[1][0]
            match = re.search(pattern, download_info[1][0])

            if match:
                resolution = match.group(1)
                if '480p' in resolution:
                    mypkg.logger.info(
                        f"⛔️ [{idx}/{total}]视频：{lf_cn_name}-分辨率：{resolution}非1080p不洗版"
                    )

                elif '720p' in resolution:
                    mypkg.logger.info(
                        f"⛔️ [{idx}/{total}]视频：{lf_cn_name}-分辨率：{resolution}非1080p不洗版"
                    )

                else:
                    if '[中字後補]' in lf_cn_name:
                        mypkg.logger.info(
                            f"⛔️ [{idx}/{total}]未找到可洗版的视频：{lf_cn_name}-分辨率：{resolution}"
                        )
                    else:
                        mypkg.logger.info(
                            f"🎬 [{idx}/{total}]开始洗版：{lf_cn_name}-{resolution}"
                        )
                        delete_files_with_keyword(save_file, lf_cn_name)
                        #xb_data_db_update(NY, lf_id, lf_cn_name, resolution)
                        try:
                            html_content = hanime1_id_info(lf_id)
                            sx_tags_db(NY, lf_id, html_content)
                        except Exception as e:
                            mypkg.logger.error(f"❌️ 更新里番id:{lf_id} tags失败,异常原因：{e}")
                        videos_nfo_jpg(NY, save_file)


            else:
                    mypkg.logger.error(
                        f"⛔️ [{idx}/{total}]洗版错误：{lf_cn_name, lf_cn_url, match}"
                    )
            time.sleep(3)
        except Exception as e:
            mypkg.logger.error(f"⚠️ [{idx}/{total}]出错：{e}")
