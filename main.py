import mypkg
import os
from mypkg.hanime_info import get_hanime1_xlifan,html_info_to_db,db_hanime_table,sx_tags_db,hanime1_id_info,sx_xf_yg_tag
from mypkg import Page
from datetime import datetime
from mypkg.xiban import xb_main
from mypkg.other_download import qtfl_plxz
import time
# 刮削页数,里番,同人作品,3D动画等都会采用此配置
Pages = Page("1").to_list()  # [1,2,3]
#取当月格式202508（默认是上月）
now = datetime.now()
year = now.year
month = now.month - 1
NY = f"{year}{month:02d}"
#NY = datetime.now().strftime("%Y%m")
# 采集分类可选分类 ['新番预告','里番洗版','Motion Anime','3D动画','同人作品','MMD']
CJFL=['新番预告','里番洗版','Motion Anime']
#CJFL=['同人作品']
#nfo、jpg、video文件保存路径,路径最后需要带/ （如./tmp/）
#默认保存当前目录的年月文件夹中
#里番保存路径
#save_file=f"./Download/里番/{NY}/"
save_file=f"/opt/里番/Hentai/2025/{NY}/"
#同人作品保存路径
TR_3D_save_file=f"/opt/"


if __name__ == "__main__":
    if not os.path.exists(save_file):
        os.makedirs(save_file)
    else:
        pass
    for CD in CJFL:
        match CD:
            case '新番预告':
                mypkg.logger.info(f"🎬 正在刮削{NY}月新番")
                if not os.path.exists('./db/hanime1.db'):
                    html_content = get_hanime1_xlifan(NY)         #获取html
                    html_info_to_db(NY, html_content)             #解析html元素并入库
                    sx_xf_yg_tag(NY)
                else:
                    tables=db_hanime_table()
                    if NY in tables:
                        mypkg.logger.info(f"🎬 {NY}月新番数据库已存在跳过数据库采集.")
                        sx_xf_yg_tag(NY)
                    else:
                        html_content = get_hanime1_xlifan(NY)         #获取html
                        html_info_to_db(NY, html_content)             #解析html元素并入库
                        sx_xf_yg_tag(NY)
                mypkg.hanime_info.videos_nfo_jpg(NY,save_file)                 #生成NOF和JPG
                mypkg.logger.info(f"✅️ {NY}新番预告刮削已完成")
            case '里番洗版':
                mypkg.logger.info(f"🔄 开始{NY}里番洗版")#用于自动洗版无字幕的里番、高分辨率洗版.
                xb_main(NY,save_file)
                mypkg.logger.info(f"✅️ {NY}里番洗版已完成")
            case 'Motion Anime':
                for x in  Pages:
                    qtfl_plxz(CD,TR_3D_save_file,x)
                mypkg.logger.info(f"✅️ {CD} 完成")
            case '同人作品':
                for x in Pages:
                    qtfl_plxz(CD, TR_3D_save_file, x)
                mypkg.logger.info(f"✅️ {CD} 完成")
            case '3D动画':
                for x in Pages:
                    qtfl_plxz(CD, TR_3D_save_file, x)
                mypkg.logger.info(f"✅️ {CD} 完成")
            case 'MMD':
                for x in Pages:
                    qtfl_plxz(CD, TR_3D_save_file, x)
                mypkg.logger.info(f"✅️ {CD} 完成")
            case _:
                print(f"{CD} 参数问题请检查CJFL变量")


