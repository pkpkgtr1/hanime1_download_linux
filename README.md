"# hanime1_download_linux" 

### Docker命令
```docker
docker run -dit  --name hanime1_ql \
-v /opt/qinglong/config:/ql/data/config \
-v /opt/qinglong/db:/ql/data/db \
-v /opt/qinglong/log:/ql/data/log \
-v /opt/qinglong/scripts:/ql/data/scripts \
-v /opt/qinglong/hanime1_db:/ql/data/scripts/hanime1_download_linux/db \
-v /opt:/opt \
-p 5700:5700 \
hanime1_ql:latest
```
