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

#采集内容写入数据库
def db_hanime_info(NY, id, LF_NAME_JP, LF_NAME_CN, LF_ZZGS, LF_FSRQ, LF_NR, LF_IMG, LF_TAG):
    # 创建数据库连接
    conn = sqlite3.connect('./db/hanime1.db')
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
                    )'''.format(str(NY)))
    ycz=[]
    for i in range(len(LF_NAME_JP)):
        lf_id = id[i]
        name_jp = LF_NAME_JP[i]
        name_cn = LF_NAME_CN[i]
        company = LF_ZZGS[i]
        release_date = LF_FSRQ[i]
        content = LF_NR[i]
        img_url = LF_IMG[i]
        tags = ','.join(LF_TAG[i])  # 将标签列表转换为逗号分隔字符串

        # 参数化查询，防止SQL注入
        try:
            cursor.execute('''INSERT INTO '{}' 
                            (id,name_jp, name_cn, company, release_date, content, img_url, tags)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''.format(str(NY)),
                           (lf_id, name_jp, name_cn, company, release_date, content, img_url, tags))

        except sqlite3.IntegrityError:
            # 如果插入失败，说明ID已经存在，可以选择更新或跳过
            ycz.append(lf_id)


    if len(ycz) == 0:
        mypkg.logger.info(f"✅️ 刮削信息已成功入库")
    else:
        mypkg.logger.info(f"✅️ 里番ID {ycz}已存在。")

            # 提交事务
    conn.commit()

    # 关闭连接
    conn.close()

#获取当月里番预告页html
def get_hanime1_xlifan(NY):
    fetcher = requests_html()
    mypkg.logger.info(f"⏳ 正在获取https://hanime1.me/previews/{NY}")
    html = fetcher.get_html(f"https://hanime1.me/previews/{NY}")
    if html:
        if len(html) < 400:
            mypkg.logger.error("❌️ "+html)
        else:
            mypkg.logger.debug("🐞 获取的html源码为：" + html)
            mypkg.logger.info("🔄 开始解析" + str(NY) + "html源文件")
            return html
#解析html的元素并入库
def html_info_to_db(NY, html_content):
    tree = html.fromstring(html_content)
    # 使用XPath查询匹配所有具有ID属性的div元素
    div_elements = tree.xpath('//div[@id]')

    pure_digit_ids = []
    for div in div_elements:
        element_id = div.get('id')
        if element_id is not None and element_id.isdigit():
            pure_digit_ids.append(element_id)

    # 输出结果
    mypkg.logger.info(f"✅️ 已成功获取里番ID：{pure_digit_ids}")
    # 里番日文名
    LF_NAME_JP = []
    # 里番中文名
    LF_NAME_CN = []
    # 制作公司
    LF_ZZGS = []
    # 里番发行日期
    LF_FSRQ = []
    # 里番内容
    LF_NR = []
    # 里番图片
    LF_IMG = []
    # 里番标签
    LF_TAG = []

    for id in pure_digit_ids:
        # print("ID:", id)
        # 使用XPath查询匹配具有特定ID的div元素
        LF_NAME_JP_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/h3/text()')
        LF_NAME_CN_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/div/h4/text()')
        LF_ZZGS_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/div/h5[1]/a/text()')
        LF_FSRQ_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/div/h5[2]/text()')
        LF_NR_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/div/h5[3]/text()')
        LF_IMG_XP = tree.xpath(f'//*[@id="{id}"]/div/div[1]/img')
        LF_TAG_XP = tree.xpath(f'//*[@id="{id}"]/div/div[2]/div/h5[5]/div/a/text()')

        LF_NAME_JP.append(LF_NAME_JP_XP[0])
        LF_NAME_CN.append(LF_NAME_CN_XP[0])
        LF_ZZGS.append(LF_ZZGS_XP[0])
        dt = datetime.datetime.strptime(LF_FSRQ_XP[0].rstrip(), "%Y年%m月%d日")
        LF_FSRQ.append(dt.strftime("%Y-%m-%d"))
        LF_NR.append(LF_NR_XP[0])
        LF_IMG.append(LF_IMG_XP[0].get('src'))
        LF_TAG.append(LF_TAG_XP)

    db_hanime_info(NY, pure_digit_ids, LF_NAME_JP, LF_NAME_CN, LF_ZZGS, LF_FSRQ, LF_NR, LF_IMG, LF_TAG)

'''
def download_jpg(url, file_name, save_path):
        """
        下载单张图片并保存到指定路径，允许自定义文件名。
        下载成功返回True，失败返回False。
        """
        try:
            # 检查并创建保存路径
            if not os.path.exists(save_path):
                os.makedirs(save_path)

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
            mypkg.logger.info(f"✅️ 成功下载图片并保存为：{save_file}")
            return True
        except requests.exceptions.RequestException as e:
            mypkg.logger.error(f"❌️ 下载图片失败：{e}")
            return False
        except Exception as e:
            mypkg.logger.error(f"❌️ 保存图片失败：{e}")
            return False
'''

def download_jpg(url, file_name, save_path):
    """
    下载单张图片并保存到指定路径，允许自定义文件名。
    下载成功返回True，失败返回False。
    支持失败重试，最多5次，每次失败间隔5秒。
    """
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
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

    # 所有重试失败

def get_table_data(table_name):
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
        cursor.execute(f"SELECT * FROM '{table_name}' Where sfxz='0'")
        # 提取所有记录
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        mypkg.logger.error(f"❌️ 错误：{e}")
        return []
    finally:
        # 确保关闭连接
        if 'conn' in locals():
            conn.close()

def get_table_data_null(table_name):
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
        cursor.execute(f"SELECT * FROM '{table_name}' Where sfxz is null")
        # 提取所有记录
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        mypkg.logger.error(f"❌️ 错误：{e}")
        return []
    finally:
        # 确保关闭连接
        if 'conn' in locals():
            conn.close()

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

def extract_from_start_to_指定内容(text, 指定内容):
  """
  提取从字符串开头到指定内容之间的内容（不包括指定内容）。

  Args:
    text: 要处理的字符串。
    指定内容: 作为结束标记的字符串。

  Returns:
    从开头到指定内容之间的内容，如果未找到指定内容，则返回整个字符串。
  """
  pattern = r"^(.*?)" + re.escape(指定内容)
  match = re.search(pattern, text)
  if match:
    return match.group(1)
  else:
    return text

def extract_before_first_space(text):
  """
  提取字符串中第一个空格之前的内容。

  Args:
    text: 要处理的字符串。

  Returns:
    第一个空格之前的内容，如果字符串中没有空格，则返回整个字符串。
  """
  match = re.search(r'^(\S*) ', text)
  if match:
    return match.group(1)
  else:
    return text

def videos_nfo_jpg(NY,save_file):

    gltj = [' 後編', ' 前編', ' ＃', ' 第']
    table_name = str(NY)
    current_time = datetime.datetime.now()
    dt_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    data = get_table_data(table_name)
    if data:
        for idx, row in enumerate(data, start=1):  # idx 从 1 开始计数
            # 里番id
            LF_ID = row[0]
            # 里番日文名
            LF_NAME_JP = row[1]
            # 里番中文名
            LF_NAME_CN = row[2]
            # 制作公司
            LF_ZZGS = row[3]
            # 里番发行日期
            LF_FSRQ = row[4]
            # 里番内容
            LF_NR = row[5]
            # 里番图片
            LF_IMG = row[6]
            # 里番标签
            LF_TAG = row[8]
            # 背景缩略图
            bj_img_url = row[10]
            # 合集
            LF_HEJI = row[11].strip()

            # 标签
            tags = LF_TAG.split(',')
            hanime_genre = '\n    '.join(f'<genre>{x}</genre>' for x in tags)
            hanime_tags = '\n    '.join(f'<tag>{x}</tag>' for x in tags)
            img_filename = f"{safe_filename_for_linux(LF_NAME_CN)}".lstrip()

            HJ_NAME_JP = safe_filename_for_linux(LF_NAME_JP).lstrip()
            mypkg.logger.info(f"🔄 转换字段 {LF_NAME_JP} -> {HJ_NAME_JP}")
            if 'OVA ' in HJ_NAME_JP:
                for j in gltj:
                    GL_LF_NAME_JP = extract_from_start_to_指定内容(HJ_NAME_JP, j)
                    if GL_LF_NAME_JP != HJ_NAME_JP:
                        break

            else:
                for j in gltj:
                    GL_LF_NAME_JP = extract_from_start_to_指定内容(HJ_NAME_JP, j)
                    if GL_LF_NAME_JP != HJ_NAME_JP:
                        break
                GL_LF_NAME_JP = extract_before_first_space(GL_LF_NAME_JP)
            plot_text = LF_NR.replace("\n", "<br>\n")
            show_nfo = f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
    <movie>
     <plot><![CDATA[{plot_text}]]></plot>
    <customrating>里番</customrating>
    <mpaa>里番</mpaa>
    <lockdata>false</lockdata>
    <dateadded>{dt_str}</dateadded>
    <title>{LF_NAME_JP}</title> 
    <title_jp>{LF_NAME_JP}</title_jp> 
    <title_cn>{LF_NAME_CN}</title_cn> 
    <rating></rating> 
    <criticrating></criticrating> 
    <uncensored>True</uncensored> 
    <year>{str(LF_FSRQ[:4])}</year>
    <premiered>{LF_FSRQ.replace('年', '-').replace('月', '-').replace('日', '').replace(' ', '')}</premiered>
    <releasedate>{LF_FSRQ.replace('年', '-').replace('月', '-').replace('日', '').replace(' ', '')}</releasedate>
    {hanime_tags}
    <studio>{LF_ZZGS}</studio>
    {hanime_genre}
    <set>
    <name>{LF_HEJI}</name>
    </set>
    <art>
    <poster>{LF_NAME_JP}-poster.png</poster>
    </art>
    <maker>{LF_ZZGS}</maker>
    <label>{LF_ID}</label>
    <num>{LF_ID}</num>
    <release>{LF_FSRQ.replace('年', '-').replace('月', '-').replace('日', '').replace(' ', '')}</release>
    <website>https://hanime1.me/watch?v={LF_ID}</website>
    </movie>
    '''
            # print(show_nfo)
            nfo_filename = f"{safe_filename_for_linux(LF_NAME_CN)}".lstrip()
            mypkg.logger.info(f"🔄 转换字段 {LF_NAME_CN} -> {nfo_filename}")
            mypkg.logger.info(f"🔄 poster图片下载地址：{LF_IMG}")
            if download_jpg(LF_IMG, img_filename + "-poster.png", save_path=save_file) == False:
                continue
            time.sleep(1)
            mypkg.logger.info(f"🔄 fanart图片下载地址：{bj_img_url}")
            if download_jpg(bj_img_url, img_filename + "-fanart.jpg", save_path=save_file) == False:
                continue
            try:
                download_html =get_hanime1_download(LF_ID)
                download_info = download_move_info(download_html)
                if '新番預告' in download_info[0][0]:
                    mypkg.logger.info(f"📁 {download_info[0][0]}此片为新番預告跳过下载")
                else:
                    mypkg.logger.info(f"📁 开始下载：{download_info[0][0]}")
                    pattern = r"-([^.]*)\."


                    match = re.search(pattern, download_info[1][0])
                    if match:
                        resolution = match.group(1)
                        mypkg.logger.info(f"🎯 当前下载分辨率为：{resolution}")
                        # print(f"\033[33m{num}.选择下载视频质量： {quality}\033[0m")
                    else:
                        pass
                    download_name=f"{safe_filename_for_linux(download_info[0][0])}"
                    if download_file(str(resolution),LF_ID,NY,download_info[1][0],f'{save_file}{download_name}.mp4') == False:#下载文件
                        continue


                with open(save_file + nfo_filename + '.nfo', 'w', encoding="utf-8") as file:
                    file.write(show_nfo)
                time.sleep(1)
            except Exception as e:
                mypkg.logger.error(f"❌ 保存失败")
                mypkg.logger.debug(f"🐞 保存失败，错误代码：{e}")


    else:
        mypkg.logger.info(f"✅️ {table_name}当月已完成")

def db_insert_xzzt(LF_ID,table_name,resolution):
    try:
        # 连接数据库
        conn = sqlite3.connect("./db/hanime1.db")
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
        db_insert_xzzt(lf_id, str(NY),resolution)
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

def db_hanime_table():
    conn = sqlite3.connect("./db/hanime1.db")
    cursor = conn.cursor()

    # 查询所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    # 关闭连接
    conn.close()
    return [t[0] for t in tables]

def db_inster_tag(NY, lf_id, name_jp, name_cn,sfxz, tags,bjimg_url,LF_HEJI):
    # 创建数据库连接
    conn = sqlite3.connect('./db/hanime1.db')
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
                    )'''.format(str(NY)))
        # 参数化查询，防止SQL注入
    try:
        cursor.execute(
            """UPDATE '{}' 
               SET name_jp = ?, 
                   name_cn = ?, 
                   tags = ? ,
                   bj_img_url =? ,
                   sfxz = ? ,
                   heji = ? 
               WHERE id = ?""".format(str(NY)),
            (name_jp, name_cn, tags, bjimg_url,sfxz,LF_HEJI,lf_id)
        )



        conn.commit()
        conn.close()
        mypkg.logger.info(f"✅️ 里番id：{lf_id} 更新成功")
    except sqlite3.IntegrityError:
            mypkg.logger.error(f"❌️ 插入id：{lf_id} 失败")
            mypkg.logger.debug(f"❌️ 插入id：{lf_id} 失败,原因：{sqlite3.IntegrityError}")
            # 如果插入失败，说明ID已经存在，可以选择更新或跳过

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

'''
def sx_tags_db(NY):
    data = get_table_data_null(NY)
    if data:
        for idx, row in enumerate(data, start=1):  # idx 从 1 开始计数
            LF_ID = row[0]
            html =hanime1_id_info(LF_ID)
            tree = html.fromstring(str(html))
            # 日文名
            jp_name = tree.xpath('//*[@id="shareBtn-title"]/text()')[0]
            # 中文名
            cn_name = tree.xpath('//*[@id="player-div-wrapper"]/div[6]/div/div[2]/text()')[0]
            # 标签
            tags = tree.xpath('//*[@id="player-div-wrapper"]/div[7]/div/a/text()')
            tags_cleaned = ', '.join([t.replace('\xa0', '').strip() for t in tags])
            # 内容
            LF_NR = tree.xpath('//*[@id="player-div-wrapper"]/div[6]/div/div[3]/text()')[0].replace("\n", "<br>\n")
            # 制作公司
            LF_ZZGS = tree.xpath('//*[@id="video-artist-name"]/text()')[0].replace("\n", "").replace(" ", "")
            # 播放缩略图
            LF_SLT = json.loads(tree.xpath('//script[@type="application/ld+json"]/text()')[0].replace("\n", ""))['thumbnailUrl'][0]
            print(jp_name)
            print(cn_name)
            print(tags_cleaned)
            print(LF_NR)
            print(LF_ZZGS)
            print(LF_SLT)

'''


def sx_tags_db(NY, lf_id,html_content):
    hj_gl = [' THE ANIMATION']
    tree = html.fromstring(html_content)
    # 使用XPath查询匹配所有具有ID属性的div元素
    # 日文名
    jp_name = tree.xpath('//*[@id="shareBtn-title"]/text()')[0]
    # 中文名
    cn_name = tree.xpath('//*[@id="player-div-wrapper"]/div/div/div[2]/text()')
    clean_list = [
        s for s in cn_name
        if s.strip() != "" and not re.match(r'^\d{2}:\d{2}$', s)
    ]
    cn_name = [s for s in clean_list if re.search(r'[\u4e00-\u9fff]', s)][0]
    # 制作公司
    LF_ZZGS = tree.xpath('//*[@id="player-div-wrapper"]/div/div/div[3]/text()')
    LF_ZZGS = [s for s in LF_ZZGS if re.search(r'[\u4e00-\u9fff]', s)][0].replace("\n", "<br>\n")
    # 标签
    tags = tree.xpath('//*[@id="player-div-wrapper"]/div/div/a/text()')
    tags_cleaned = ','.join([
        traditional_to_simplified(''.join(t.replace('\xa0', '').split()))
        for t in tags if t.strip()
    ])
    # 内容
    LF_NR = ''
    # 播放缩略图
    #LF_SLT = json.loads(tree.xpath('//script[@type="application/ld+json"]/text()')[0].replace("\n", ""))['thumbnailUrl'][0]
    LF_SLT = tree.xpath("//meta[@property='og:image']/@content")[0]
    # 合集
    LF_HEJI = tree.xpath('//*[@id="video-playlist-wrapper"]/div/h4[1]/text()')[0]
    for j in hj_gl:
        LF_HEJI=re.sub(j, '', LF_HEJI, flags=re.IGNORECASE)
    if '[新番預告]' in cn_name:
        db_inster_tag(NY,lf_id,jp_name,cn_name,None,tags_cleaned,LF_SLT,LF_HEJI)
    elif '[中字後補]' in cn_name:
        db_inster_tag(NY, lf_id, jp_name, cn_name, '0', tags_cleaned, LF_SLT,LF_HEJI)
    else:
        db_inster_tag(NY, lf_id, jp_name, cn_name, '0', tags_cleaned, LF_SLT,LF_HEJI)



def sx_xf_yg_tag(NY):
    data = get_table_data_null(NY)
    if data:
        for idx, row in enumerate(data, start=1):  # idx 从 1 开始计数
            # 里番id
            LF_ID = row[0]
            try:
                html_content = hanime1_id_info(LF_ID)
                sx_tags_db(NY, LF_ID,html_content)
            except Exception as e:
                mypkg.logger.error(f"❌️ 更新里番id:{LF_ID} tags失败,异常原因：{e}" )


def db_update_url(NY, id, LF_IMG):
    # 创建数据库连接
    conn = sqlite3.connect('./db/hanime1.db')
    cursor = conn.cursor()
    ycz=[]
    for i in range(len(LF_IMG)):
        lf_id = id[i]
        img_url = LF_IMG[i]
        mypkg.logger.info(f"✅️ 里番ID：{lf_id},image_url已更新url为：{img_url}")
        try:
            cursor.execute('''update '{}'  SET 
                            img_url =?
                           where id= ? '''.format(str(NY)),
                           (img_url,lf_id))

        except sqlite3.IntegrityError:
            # 如果插入失败，说明ID已经存在，可以选择更新或跳过
            ycz.append(lf_id)

            # 提交事务
    conn.commit()

    # 关闭连接
    conn.close()

def update_img_url_to_db(NY, html_content):
    tree = html.fromstring(html_content)
    # 使用XPath查询匹配所有具有ID属性的div元素
    div_elements = tree.xpath('//div[@id]')

    pure_digit_ids = []
    for div in div_elements:
        element_id = div.get('id')
        if element_id is not None and element_id.isdigit():
            pure_digit_ids.append(element_id)

    # 输出结果
    #mypkg.logger.info(f"✅️ 已成功更新image_url,里番ID：{pure_digit_ids}")
    # 里番日文名

    LF_IMG = []

    for id in pure_digit_ids:
        LF_IMG_XP = tree.xpath(f'//*[@id="{id}"]/div/div[1]/img')
        LF_IMG.append(LF_IMG_XP[0].get('src'))


    db_update_url(NY, pure_digit_ids, LF_IMG)

