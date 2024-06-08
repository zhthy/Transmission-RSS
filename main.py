import feedparser
import transmission_rpc
import time
import os

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

# 检查间隔时间（秒）
CHECK_INTERVAL = 3600  # 每小时检查一次

# 已添加的种子链接文件
ADDED_TORRENTS_FILE = 'added_torrents.txt'

# 配置文件
CONFIG_FILE = 'config.txt'

# 日志文件
LOG_FILE = 'log.txt'

def log_message(message):
    """
    记录日志信息。
    """
    with open(LOG_FILE, 'a') as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def load_added_torrents(file_path):
    """
    从文件中加载已添加的种子链接。
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return set(line.strip() for line in file)
    return set()

def save_added_torrent(file_path, torrent_link):
    """
    将新的种子链接保存到文件中。
    """
    with open(file_path, 'a') as file:
        file.write(f"{torrent_link}\n")

def load_config(file_path):
    """
    从文件中加载配置。
    """
    config = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                key, value = line.strip().split('=')
                config[key] = value
    return config

def save_config(file_path, config):
    """
    将配置保存到文件中。
    """
    with open(file_path, 'w') as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")

def get_user_input():
    """
    获取用户输入的过滤条件和最大做种体积。
    """
    max_size_gb = float(input("请输入最大种子体积（单位为GB，输入0表示无限制）："))
    keywords = input("请输入过滤关键字（多个关键字用逗号分隔）：").split(',')
    keywords = [kw.strip() for kw in keywords]  # 去除多余空格
    max_seeding_size_gb = float(input("请输入可供Transmission做种的最大体积（单位为GB）："))

    config = {
        'max_size_gb': max_size_gb,
        'keywords': ','.join(keywords),
        'max_seeding_size_gb': max_seeding_size_gb
    }

    save_config(CONFIG_FILE, config)
    return max_size_gb, keywords, max_seeding_size_gb

def add_torrent(url, client):
    """
    将种子链接添加到Transmission中，并返回种子ID。
    """
    try:
        torrent = client.add_torrent(url)
        log_message(f'Added torrent: {url}')
        return torrent.id
    except Exception as e:
        log_message(f'Failed to add torrent: {url}, Error: {e}')
        return None

def get_current_seeding_size(client):
    """
    获取Transmission占用的磁盘空间（GB）。
    """
    total_space_used = 0
    for torrent in client.get_torrents():
        if torrent.status in ['seeding', 'downloading']:
            total_space_used += torrent.have_valid / (1024 ** 3)  # 转换为GB
    return total_space_used

def wait_for_downloads_to_complete(client):
    """
    等待所有下载完成。
    """
    while True:
        all_complete = True
        for torrent in client.get_torrents():
            if torrent.status == 'downloading':
                all_complete = False
                break
        if all_complete:
            log_message("所有下载已完成。")
            return
        log_message("等待下载完成...")
        time.sleep(60)  # 每1分钟检查一次

def check_feeds(max_size_gb, filter_keywords, max_seeding_size_gb, added_torrents):
    """
    检查所有RSS源，并根据过滤器条件添加新的种子。
    """
    try:
        client = transmission_rpc.Client(
            host=TRANSMISSION_HOST,
            port=TRANSMISSION_PORT,
            username=TRANSMISSION_USER,
            password=TRANSMISSION_PASSWORD
        )

        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            log_message(f'Checking feed: {feed_url} with {len(feed.entries)} entries')
            for entry in feed.entries:
                # 提取 enclosure URL
                enclosure_url = None
                if 'enclosures' in entry:
                    for enclosure in entry.enclosures:
                        if enclosure['type'] == 'application/x-bittorrent':
                            enclosure_url = enclosure['url']
                            break

                if enclosure_url:
                    torrent_link = enclosure_url
                    torrent_title = entry.title

                    # 检查种子标题是否包含任何过滤关键字
                    if any(keyword.lower() in torrent_title.lower() for keyword in filter_keywords):
                        # 检查种子大小是否符合要求
                        if torrent_link not in added_torrents:
                            current_seeding_size = get_current_seeding_size(client)
                            torrent_id = add_torrent(torrent_link, client)
                            if torrent_id:
                                torrent = client.get_torrent(torrent_id)
                                torrent_size = torrent.total_size / (1024 ** 3)  # 转换为GB

                                if max_size_gb == 0 or torrent_size <= max_size_gb:
                                    if current_seeding_size + torrent_size <= max_seeding_size_gb:
                                        added_torrents.add(torrent_link)
                                        save_added_torrent(ADDED_TORRENTS_FILE, torrent_link)
                                        current_seeding_size = get_current_seeding_size(client)
                                        log_message(f"种子标题: {torrent_title}, 当前Transmission占用空间: {current_seeding_size:.2f} GB, 添加种子体积: {torrent_size:.2f} GB, 总体积: {current_seeding_size + torrent_size:.2f} GB")
                                        wait_for_downloads_to_complete(client)  # 等待所有下载完成
                                    else:
                                        log_message(f"种子标题: {torrent_title}, 当前Transmission占用空间: {current_seeding_size:.2f} GB, 添加种子体积: {torrent_size:.2f} GB, 超过最大做种体积: {max_seeding_size_gb:.2f} GB。停止添加新种子。")
                                        return
    except Exception as e:
        log_message(f'Failed to check feeds: {e}')

def main():
    """
    主函数，定期检查RSS源。
    """
    # 检查Transmission配置是否正确
    try:
        client = transmission_rpc.Client(
            host=TRANSMISSION_HOST,
            port=TRANSMISSION_PORT,
            username=TRANSMISSION_USER,
            password=TRANSMISSION_PASSWORD
        )
        client.session_stats()  # 尝试获取会话统计信息
        log_message("Transmission连接成功。")
    except Exception as e:
        log_message(f"Transmission连接失败: {e}")
        print(f"Transmission连接失败: {e}")
        return

    # 检查配置文件是否存在且格式正确
    config = load_config(CONFIG_FILE)
    if not config or 'max_size_gb' not in config or 'keywords' not in config or 'max_seeding_size_gb' not in config:
        max_size_gb, filter_keywords, max_seeding_size_gb = get_user_input()  # 获取用户输入的过滤条件和最大做种体积
    else:
        max_size_gb = float(config['max_size_gb'])
        filter_keywords = config['keywords'].split(',')
        max_seeding_size_gb = float(config['max_seeding_size_gb'])

    added_torrents = load_added_torrents(ADDED_TORRENTS_FILE)  # 加载已添加的种子链接

    while True:
        check_feeds(max_size_gb, filter_keywords, max_seeding_size_gb, added_torrents)
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
