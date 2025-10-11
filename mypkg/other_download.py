import sqlite3
import os
import time
from tqdm import tqdm
import requests
import mypkg
import re
import datetime
from mypkg.playwright_html import playwright_html
from lxml import html
import json
from opencc import OpenCC
from mypkg.requests_html import requests_html

def traditional_to_simplified(text: str) -> str:
    cc = OpenCC('t2s')
    """将繁体中文转换为简体中文"""
    return cc.convert(text)

def db_insert_xzzt(LF_ID,table_name,resolution):
    table_name = table_name.replace(' ', '_')
    try:
        # 连接数据库
        conn = sqlite3.connect(f"./db/{table_name}.db")
        # 创建游标对象
        cursor = conn.cursor()
        # 执行插入操作
        cursor.execute(f"UPDATE '{table_name}' SET sfxz='1' ,resolution='{resolution}' WHERE id='{LF_ID}'")
        # 提交更改
        conn.commit()
    except sqlite3.Error as e:
        mypkg.logger.error(f"❌️ 错误：{e}")
    finally:
        # 确保关闭连接
        if 'conn' in locals():
            conn.close()
'''
def download_file(resolution,lf_id, NY, url, filename=None):
    """
    下载文件并显示进度条
    :param url: 文件的URL地址
    :param filename: 保存的文件名，若None则使用URL中的文件名
    """
    try:
        # 发送HTTP GET请求
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()  # 如果响应状态码不是2xx，会抛出异常

        # 获取文件总大小
        file_size = int(response.headers.get('Content-Length', 0))

        # 如果没有指定文件名，从URL中提取
        if filename is None:
            filename = url.split('/')[-1]

        # 创建tqdm进度条
        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=filename)

        # 写入文件
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive chunks
                    file.write(chunk)
                    progress_bar.update(len(chunk))

        progress_bar.close()
        mypkg.logger.info(f"🖼️ 下载完成，文件已保存为：{filename}")
        #db_insert_xzzt(lf_id, str(NY),resolution)
        return True
    except requests.exceptions.RequestException as e:
        mypkg.logger.error(f"✅️ 下载失败：{e}")
        return False
    except Exception as e:
        mypkg.logger.error(f"❌️ 发生错误：{e}")
        return False
    except KeyboardInterrupt:
        mypkg.logger.error(f"❌️ 下载已取消")
        return False
'''

def download_file(url, filepath, chunk_size=1024*1024):
    """
    支持断点续传的下载函数（修复已下载完成时再次执行报错的问题）

    :param url: 下载链接
    :param filepath: 本地保存路径
    :param chunk_size: 每次写入的块大小 (默认 1MB)
    """
    try:
        # 获取远程文件大小
        head = requests.head(url, allow_redirects=True)
        head.raise_for_status()
        total_size = int(head.headers.get('Content-Length', 0))

        # 已下载大小
        local_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        # 如果已下载完成，直接返回
        if local_size >= total_size and total_size > 0:
            mypkg.logger.info(f"✅ 文件已完整存在，无需重新下载: {filepath}")
            return True

        # 设置 Range 请求头
        headers = {}
        if local_size > 0:
            headers['Range'] = f'bytes={local_size}-'

        # 发送请求
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()

        # 打开模式
        mode = 'ab' if local_size > 0 else 'wb'
        mypkg.logger.info(f"开始下载: {url}")
        mypkg.logger.info(f"目标文件: {filepath}")
        mypkg.logger.info(f"总大小: {total_size/1024/1024:.2f} MB (已下载 {local_size/1024/1024:.2f} MB)")

        # 写文件
        with open(filepath, mode) as f:
            downloaded = local_size
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = downloaded * 100 / total_size
                    print(f"\r进度: {percent:.2f}% ({downloaded/1024/1024:.2f} MB)", end="")
        print()
        mypkg.logger.info(f"{filepath},下载完成！")
        return True
    except Exception as e:
        mypkg.logger.error(f"❌ {filepath},下载失败{e}")
        mypkg.logger.debug(f"🐞 {filepath},下载失败，错误代码：{e}")
        return False


def db_hanime_init(db, id_list):
    # 创建数据库连接
    db=db.replace(' ', '_')
    conn = sqlite3.connect(f'./db/{db}.db')
    cursor = conn.cursor()
    # 创建表
    cursor.execute('''CREATE TABLE IF NOT EXISTS '{}'
                    (ID INT PRIMARY KEY NOT NULL, -- 里番ID
                    name_jp TEXT COMMENT '日文名称',
                    name_cn TEXT COMMENT '中文名称',
                    company TEXT COMMENT '制作公司',
                    release_date TEXT COMMENT '发行日期',
                    content TEXT COMMENT '内容',
                    img_url TEXT COMMENT '图片URL',    
                    resolution TEXT COMMENT '分辨率',             
                    tags TEXT COMMENT '标签',
                    sfxz TEXT COMMENT '是否下载',
                    bj_img_url TEXT COMMENT '背景图url',
                    heji TEXT COMMENT '合集'
                    )'''.format(str(db)))
    # 参数化查询，防止SQL注入
    conn.commit()
    placeholders = ",".join("?" * len(id_list))
    try:
        query = f"SELECT id FROM '{db}' WHERE id IN ({placeholders})"
        cursor.execute(query, id_list)
        db_ids = [row[0] for row in cursor.fetchall()]
        missing_ids = list(set(id_list) - set(db_ids))
        conn.close()
        return missing_ids
    except Exception as e:
        mypkg.logger.error("❌️ 查询"+f'./db/{db}.db'+'失败')

def db_inster_tag(db, lf_id, name_jp, name_cn, company, content,sfxz, tags,bjimg_url,LF_HEJI,resolution):
    # 创建数据库连接
    db = db.replace(' ', '_')
    conn = sqlite3.connect(f'./db/{db}.db')
    cursor = conn.cursor()
    # 创建表
    cursor.execute('''CREATE TABLE IF NOT EXISTS '{}'
                    (ID INT PRIMARY KEY NOT NULL, -- 里番ID
                    name_jp TEXT COMMENT '日文名称',
                    name_cn TEXT COMMENT '中文名称',
                    company TEXT COMMENT '制作公司',
                    release_date TEXT COMMENT '发行日期',
                    content TEXT COMMENT '内容',
                    img_url TEXT COMMENT '图片URL',    
                    resolution TEXT COMMENT '分辨率',             
                    tags TEXT COMMENT '标签',
                    sfxz TEXT COMMENT '是否下载',
                    bj_img_url TEXT COMMENT '背景图url',
                    heji TEXT COMMENT '合集'
                    )'''.format(str(db)))
        # 参数化查询，防止SQL注入
    conn.commit()
    try:
        cursor.execute(
            """INSERT OR REPLACE INTO '{}' 
               (id, name_jp, name_cn, company, content, tags, bj_img_url, sfxz, heji, resolution)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""".format(str(db)),
            (lf_id, name_jp, name_cn, company, content, tags, bjimg_url, sfxz, LF_HEJI,resolution)
        )



        conn.commit()
        mypkg.logger.info(f"✅️ 里番id：{lf_id} 更新{cursor.rowcount}条成功")
    except sqlite3.IntegrityError:
            mypkg.logger.error(f"❌️ 插入id：{lf_id} 失败")
            mypkg.logger.debug(f"❌️ 插入id：{lf_id} 失败,原因：{sqlite3.IntegrityError}")
            # 如果插入失败，说明ID已经存在，可以选择更新或跳过
    conn.close()

def get_hanime1_page_html(CX,page):
    fetcher = requests_html()
    mypkg.logger.info(f"⏳ 正在查询https://hanime1.me/search?genre={CX}&page={page}")
    html = fetcher.get_html(f"https://hanime1.me/search?genre={CX}&page={page}")
    if html:
        if len(html) < 400:
            mypkg.logger.error("❌️ "+html)
        else:
            mypkg.logger.debug("🐞 获取的html源码为：" + html)
            mypkg.logger.info("🔄 开始解析" + str(CX) + "html源文件")
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

def download_jpg(url, file_name, save_path):
    """
    下载单张图片并保存到指定路径，允许自定义文件名。
    下载成功返回True，失败返回False。
    支持失败重试，最多5次，每次失败间隔5秒。
    """

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            # 检查并创建保存路径
            # 发送HTTP GET请求获取图片数据
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()  # 检查HTTP请求是否成功

            # 如果未提供自定义文件名，提取URL中的文件名
            if not file_name:
                file_name = url.split("/")[-1]

            # 确保文件路径的完整性
            save_file = os.path.join(save_path, file_name)

            # 以二进制写入模式保存图片
            with open(save_file, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)

            mypkg.logger.info(f"✅ [第{attempt}/{max_retries}次尝试]成功下载图片并保存为：{save_file} ")
            return True

        except requests.exceptions.RequestException as e:
            mypkg.logger.error(f"❌ [第{attempt}/{max_retries}次尝试]下载图片失败：{e} ")
        except Exception as e:
            mypkg.logger.error(f"❌ [第{attempt}/{max_retries}次尝试]保存图片失败：{e} ")
            return False

        time.sleep(8)

def get_hanime1_download(LFID):
    fetcher = requests_html()
    mypkg.logger.info(f"⏳ 正在获取https://hanime1.me/download?v={LFID}")
    html = fetcher.get_html(f"https://hanime1.me/download?v={LFID}")

    if html:
        if len(html) < 400:
            mypkg.logger.error("❌️ "+html)
        else:
            mypkg.logger.debug("🐞 获取的html源码为：" + html)
            mypkg.logger.info("🔄 开始解析下载页html源文件")
            return html

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


def filter_text(arr):
    # 匹配中文、日文、英文
    pattern = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\uFF66-\uFF9F\u3400-\u4dbfA-Za-z]")
    return [s for s in arr if pattern.search(s)]
def cj_html_ys_download(db, lf_id, html_content,save_file,idx,idy):

        tree = html.fromstring(html_content)
        # 使用XPath查询匹配所有具有ID属性的div元素
        # 日文名
        jp_name = tree.xpath('//*[@id="shareBtn-title"]/text()')[0]
        jp_name =jp_name.replace("", " ")
        # 中文名
        #cn_name = tree.xpath('//*[@id="player-div-wrapper"]/div/div/div[2]/text()')
        #cn_name = [s for s in cn_name if re.search(r'[\u4e00-\u9fff]', s)][0]
        # 制作公司
        #LF_ZZGS = tree.xpath('//*[@id="player-div-wrapper"]/div/div/div[3]/text()')
        #LF_ZZGS = [s for s in LF_ZZGS if re.search(r'[\u4e00-\u9fff]', s)][0].replace("\n", "<br>\n")
        # 标签
        tags = tree.xpath('//*[@id="player-div-wrapper"]/div/div/a/text()')
        tags = filter_text(tags)
        hanime_genre = '\n    '.join(f'<genre>{traditional_to_simplified(x)}</genre>' for x in tags).replace('\xa0', '')
        hanime_tags = '\n    '.join(f'<tag>{traditional_to_simplified(x)}</tag>' for x in tags).replace('\xa0', '')
        tags_cleaned = ','.join([
            traditional_to_simplified(''.join(t.replace('\xa0', '').split()))
            for t in tags if t.strip()
        ])        # 内容
        LF_NR = tree.xpath('//*[@id="player-div-wrapper"]/div/div/div[3]/text()')#[0].replace("\n", "").replace(" ", "")
        LF_NR =filter_text(LF_NR)
        plot_text = LF_NR[0].replace("\n", "<br>\n")        #里番日期
        LF_RQ= tree.xpath('//*[@id="player-div-wrapper"]/div[6]/div/div/text()')[0].replace("\n", "").replace(" ", "")
        if len(LF_RQ) < 7 :
            LF_RQ = tree.xpath('//*[@id="player-div-wrapper"]/div[7]/div/div/text()')[0].replace("\n", "").replace(" ",                                                                                                                   "")
        LF_RQ=LF_RQ.replace('\xa0', '-')
        print(LF_RQ)
        LFGKS,LF_RQ = LF_RQ.split('--')
        # 播放缩略图
        LF_SLT =  json.loads(tree.xpath('//script[@type="application/ld+json"]/text()')[0].replace("\n", ""))['thumbnailUrl'][0]
        # 合集
        LF_HEJI = tree.xpath('//*[@id="video-playlist-wrapper"]/div/h4[1]/text()')[0]
        show_nfo = f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
            <movie>
             <plot><![CDATA[{plot_text}]]></plot>
            <customrating>{db}</customrating>
            <mpaa>{db}</mpaa>
            <lockdata>false</lockdata>
            <title>{jp_name}</title> 
            <title_jp>{jp_name}</title_jp> 
            <rating></rating> 
            <criticrating></criticrating> 
            <uncensored>True</uncensored> 
            <year>{str(LF_RQ[:4])}</year>
            <premiered>{LF_RQ}</premiered>
            <releasedate>{LF_RQ}</releasedate>
            {hanime_tags}
            <studio>{LF_HEJI}</studio>
            {hanime_genre}
            <set>
            <name>{LF_HEJI}</name>
            </set>
            <art>
            <poster>{jp_name}-poster.png</poster>
            </art>
            <maker>{LF_HEJI}</maker>
            <label>{lf_id}</label>
            <num>{lf_id}</num>
            <release>{LF_RQ}</release>
            <website>https://hanime1.me/watch?v={lf_id}</website>
            </movie>
            '''
        mypkg.logger.info(f"🎬️ [{idx}/{idy}]番剧详细信息 \n📺️ 标题：{jp_name}\n🆔 ID：{lf_id}\n🔗 URL：https://hanime1.me/watch?v={lf_id}\n🖼️ 缩略图URL：{LF_SLT}\n✍️ 作者：{LF_HEJI}\n🔗 下载链接:\n📅 日期：{LF_RQ}\n👁️ {LFGKS}\n📋️ 描述：{LF_NR}\n🔖 标签：{tags_cleaned}")
        gl_jp_name= safe_filename_for_linux(jp_name)
        mypkg.logger.info(f"🔄 转换字段 {jp_name} -> {gl_jp_name}")
        bclj=db.replace(' ', '_')
        if download_jpg(LF_SLT, bclj + '/' + str(lf_id) + "-poster.png", save_path=save_file) == False:
            return False
        if download_jpg(LF_SLT, bclj + '/' + str(lf_id) + "-fanart.jpg", save_path=save_file) == False:
            return False
        try:
            if not os.path.exists(f'{save_file}{bclj}'):
                os.makedirs(f'{save_file}{bclj}')
            download_html = get_hanime1_download(lf_id)
            download_info = download_move_info(download_html)
            if '新番預告' in download_info[0][0]:
                mypkg.logger.info(f"📁 {download_info[0][0]}此片为新番預告跳过下载")
            else:
                mypkg.logger.info(f"📁 开始下载：{download_info[1][0]}")
                pattern = r'-(\d{3,4}p)\.mp4'

                match = re.search(pattern, download_info[1][0])
                if match:
                    resolution = match.group(1)
                    mypkg.logger.info(f"🎯 当前下载分辨率为：{resolution}")
                    # print(f"\033[33m{num}.选择下载视频质量： {quality}\033[0m")
                else:
                    pass

                download_name = f"{safe_filename_for_linux(download_info[0][0])}"
                if download_file(download_info[1][0],f'{save_file}{bclj}/{str(lf_id)}.mp4') ==False:
                    return False
                with open(save_file+bclj+'/'+ str(lf_id) + '.nfo', 'w', encoding="utf-8") as file:
                    file.write(show_nfo)
                time.sleep(1)
                db_inster_tag(db, lf_id, gl_jp_name, None, LF_HEJI, plot_text, '1', tags_cleaned, LF_SLT, LF_HEJI,
                              resolution)
        except Exception as e:
            mypkg.logger.error(f"❌ 保存失败{e}")
            mypkg.logger.debug(f"🐞 保存失败，错误代码：{e}")



def hanime1_id_info(lf_id):
    fetcher = requests_html()
    mypkg.logger.info(f"⏳ 正在获取https://hanime1.me/watch?v={lf_id}")
    html = fetcher.get_html(f"https://hanime1.me/watch?v={lf_id}")
    if html:
        if len(html) < 400:
            mypkg.logger.error("❌️ "+html)
        else:
            mypkg.logger.debug("🐞 获取的html源码为：" + html)
            mypkg.logger.info("🔄 开始解析里番id:" + str(lf_id) + " html源文件")
            return html
def gl_id(db, html_content):
    tree = html.fromstring(html_content)
    url_list = tree.xpath('//*[@id="home-rows-wrapper"]/div/div/div/a/@href')
    url_list = list(set(url_list))

    id_list = []
    for url in  url_list:
        if 'https://hanime1.me/watch?v=' in url :

            match = re.search(r'v=(\d+)', url)
            if match:
                id_list.append(int(match.group(1)))

    id_list=db_hanime_init(db,id_list)

    del  html_content
    return id_list





def qtfl_plxz(db,save_file,page=1):
    html_content = get_hanime1_page_html(db,page)         #获取html
    id_list=gl_id(db,html_content)
    if id_list == []:
        mypkg.logger.info(f'📁 {db} 分类,未发现更新')
    else:
        for idx, lf_id in enumerate(id_list, start=1):
            html_content = hanime1_id_info(lf_id)
            try:
                if cj_html_ys_download(db, lf_id, html_content,save_file,idx,len(id_list)) ==False:
                    continue
                time.sleep(1)
            except Exception as e:
                mypkg.logger.error(f"❌️ 刮削{db},id:{lf_id}失败，原因：" + e)


#单个里番id下载
def dg_id_download(db,lf_id,idx,id_list,save_file):
    html_content = hanime1_id_info(lf_id)
    try:
        cj_html_ys_download(db, lf_id, html_content, save_file, idx, len(id_list))
    except Exception as e:
        mypkg.logger.error(f"❌️ 刮削{db},id:{lf_id}失败，原因：" + e)

