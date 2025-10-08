"# hanime1_download_linux" 

### Docker命令
```docker
docker run -dit  --name hanime1_ql \
-v /opt/qinglong/config:/ql/data/config \
-v /opt/qinglong/db:/ql/data/db \
-v /opt/qinglong/log:/ql/data/log \
-v /opt/qinglong/scripts:/ql/data/scripts \
-v /opt:/opt \
-p 5700:5700 \
hanime1_ql:latest
```

### FlareSolverr
```FlareSolverr
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```