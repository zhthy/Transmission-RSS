# Transmission-RSS

vps transmission-daemon RSS自动订阅工具，可以自动添加种子到transmission-daemon，并且可以傻瓜式设置过滤器

# 使用方法

#安装环境

```python
pip install feedparser transmission-rpc
```

#修改配置

```python
# Transmission配置
TRANSMISSION_HOST = 'localhost'  # Transmission守护进程的主机地址
TRANSMISSION_PORT = 9091  # Transmission守护进程的端口
TRANSMISSION_USER = 'your_username'  # Transmission用户名
TRANSMISSION_PASSWORD = 'your_password'  # Transmission密码

# RSS源列表
RSS_FEEDS = [
    'https://example.com/rss-feed-1.xml',  # 第一个RSS源
    'https://example.com/rss-feed-2.xml'   # 第二个RSS源
]
```

#后台运行

```sh
sudo nohup python3 main.py &
```



# 已测试的站点

FSM、CarPT（选结尾带linktype的RSS链接）
