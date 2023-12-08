# -*- coding: utf-8 -*-
import configparser
import subprocess
import time
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from video_parse_conf import Video_parse


class Batch_clawer_mitm():
    def __init__(self, conf_path) -> None:
        conf = configparser.ConfigParser()
        conf.read(conf_path, encoding='UTF-8')
        # sofware_path
        self.tshark_interface_number = conf.get("sofware_path",
                                                "tshark_interface_number")  # "iphone_4g"  #tshark捕包的网络接口名字
        self.chrome_driver_path = conf.get("sofware_path", "chrome_driver_path")  # chromdriver位置
        self.tshark_path = conf.get("sofware_path", "tshark_path")  # TSHARK位置
        self.mitmproxy_path = conf.get("sofware_path", "mitmproxy_path")  # mitmdump 可执行文件位置
        self.mitm_py = conf.get("sofware_path", "mitm_py")  # mitm.py文件存放位置
        self.chrome_user_data_path = conf.get("sofware_path", "chrome_user_data_path")
        # record_path
        self.root_path = conf.get("record_path", "root_path")  # 记录根目录
        self.mitm_record_path = conf.get("record_path", "mitm_record_path")  # mitm记录的文件位置
        self.ping_record_path = conf.get("record_path", "ping_record_path")  # ping文件记录位置
        # clawer
        self.video_parse_conf_file_path = conf.get("clawer", "video_parse_conf_file_path")
        self.clawer_type = int(conf.get("clawer", "clawer_type"))
        self.time_duration = int(conf.get("clawer", "time_duration"))  # 每一个视频播放时长，单位秒
        self.batch_size = int(conf.get("clawer", "batch_size"))  # 每一个pcap文件中包含的视频个数,称为一个batch
        self.batch_count = int(conf.get("clawer", "batch_count"))  # 总共播放多少个batch
        self.player_click = int(conf.get("clawer", "player_click"))
        self.ping_record_flag = int(conf.get("ping", "ping_record_flag"))  # 是否采集时延信息
        self.mitm_flag = int(conf.get("clawer", "mitm_flag"))  # 是否记录mitm解密后的信息
        self.tshark_flag = int(conf.get("clawer", "tshark_flag"))  # 是否记录流量数据
        self.screenshot_flag = int(conf.get("clawer", "screenshot_flag"))  # 是否记录截图
        self.url_csv_path = conf.get("clawer", "url_csv_path")
        self.clawer_video_resolution = str(conf.get("clawer", "clawer_video_resolution")).split(',')
        # 初始化视频解析类
        self.video_parse = Video_parse(self.video_parse_conf_file_path)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        self.driver = self.chrome_driver_init()
        self.video_url = []  # 一批视频爬取URL

    def __del__(self):
        self.driver.close()

    # 初始化chrom driver
    def chrome_driver_init(self):
        options = webdriver.ChromeOptions()
        service = Service(self.chrome_driver_path)
        options.add_argument("--user-data-dir=" + self.chrome_user_data_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_window_size(1000, 30000)
        wait = WebDriverWait(driver, 100)
        return driver

    # 持续访问URL直到成功
    def loop_get_url(self, video_url):
        loop_count = 10
        for i in range(0, loop_count):
            try:
                time.sleep(3)
                self.driver.get(video_url)
                return 1
            except:
                continue
        return 0

    # 点击视频开始播放
    def player_click_fun(self):
        if self.player_click != 1:
            return
        player_xpath = self.video_parse.video_player_button
        try:
            if player_xpath != '':
                self.driver.find_element_by_class_name(player_xpath).click()
        except:
            print("player click error")

    # 获取视频时长
    def get_video_duration(self):
        duration_xpath = self.video_parse.duration_xpath
        try:
            if duration_xpath != '':
                html = self.driver.page_source.encode("utf-8", "ignore")
                parseHtml = etree.HTML(html)
                video_duration = parseHtml.xpath(duration_xpath)
        except:
            video_duration = -1
            print('get video duration error')

        return video_duration

    # 确定视频实际播放时长
    def clawer_video_duration(self, video_duration):
        video_duration_s = -1
        if len(video_duration) > 0 and video_duration != -1:
            time_data = str(video_duration[0]).split(':')
            if len(time_data) == 2:
                video_duration_s = int(time_data[0]) * 60 + int(time_data[1])
            else:
                video_duration_s = int(time_data[0]) * 3600 + int(time_data[1]) * 60 + int(time_data[2])
        duration_of_the_video = video_duration_s
        return duration_of_the_video

    # 从csv文件中读取url并依次访问
    def clawer_from_csv(self):
        if self.clawer_type == 0:
            batch_size = 1
        else:
            batch_size = self.batch_size
        batch_count = self.batch_count
        csv_file = open(self.url_csv_path, mode='r', encoding='utf-8')
        csv_data = csv_file.read()
        video_urls = csv_data.split('\n')[1:]

        if int(len(video_urls) / batch_size) < batch_count:
            batch_count = int(len(video_urls) / batch_size)

        with open('C:/Shrink/data/temp/10m_720p_url.csv', 'a+') as f:
            f.write('\n')
        for i in range(0, batch_count):
            self.video_url.clear()
            self.video_url = video_urls[i * batch_size:((i + 1) * batch_size)]
            url = self.get_url_duration()
            if url != None:
                with open('C:/Shrink/data/temp/10m_720p_url.csv', 'a+') as f:
                    f.write(url + '\n')

    # 从主页面获取待爬取的视频URL
    def get_url(self, video_class, main_url):
        if self.clawer_type == 0:
            batch_size = 1
        else:
            batch_size = self.batch_size
        batch_count = self.batch_count
        # 受局域网代理不会自动开启关闭影响，每次浏览时都应保证mitmproxy已运行
        if self.mitm_flag == 1:
            mitmCall = [self.mitmproxy_path]
            mitmProc = subprocess.Popen(mitmCall, executable=self.mitmproxy_path)
        self.loop_get_url(main_url)
        time.sleep(5)
        for i in range(0, 100):
            self.driver.execute_script('window.scrollBy(0,1000)')
            time.sleep(1)

        # 从索引页批量获取视频URL
        video_urls = []
        html = self.driver.page_source.encode("utf-8", "ignore")
        parseHtml = etree.HTML(html)
        index_page_xpath = self.video_parse.index_page_xpath
        if self.video_parse.video_server_name == 'bilibili':
            raw_video_urls = parseHtml.xpath(index_page_xpath)
            for url in raw_video_urls:
                video_urls.append("https:" + str(url))
        elif self.video_parse.video_server_name == 'youtube':
            raw_video_urls = parseHtml.xpath(index_page_xpath)
            # 跳过短视频
            for url in raw_video_urls:
                if str(url).__contains__('watch'):
                    video_urls.append("https://www.youtube.com/" + str(url))
        else:
            video_urls = parseHtml.xpath(index_page_xpath)

        return video_urls

    # 获取视频分辨率信息
    def get_video_resolution(self):
        video_resolution = []
        try:
            if self.video_parse.video_server_name == 'youtube':
                # 点击设置
                self.driver.find_element(By.XPATH, '//*[@class="ytp-button ytp-settings-button"]').click()
                # 点击画质
                self.driver.find_element(By.XPATH,
                                         '//*[@class="ytp-popup ytp-settings-menu"]//*[@class="ytp-menu-label-secondary"]').click()
                time.sleep(0.5)
                # 获取分辨率信息
                html = self.driver.page_source.encode("utf-8", "ignore")
                parseHtml = etree.HTML(html)
                video_resolution = parseHtml.xpath(
                    '//*[@class="ytp-popup ytp-settings-menu"]//*[@class="ytp-menuitem-label"]/div/span/text()')
                # 复原
                self.driver.find_element(By.XPATH, '//*[@class="ytp-button ytp-settings-button"]').click()
            else:
                pass
        except:
            print('get resolution error')

        return video_resolution

    # 目标分辨率与存在视频本身包含的分辨率取交集，作为最后的捕获分辨率
    def clawer_resolution_intersection(self, online_video_resolution):
        target_resolution = []
        res = []
        for i in range(0, len(self.clawer_video_resolution)):
            resolution_val = int(self.clawer_video_resolution[i])
            if resolution_val == 0:
                target_resolution = []
                target_resolution = online_video_resolution[0:-1]
                break
            elif resolution_val == 1:
                target_resolution.append('360')
            elif resolution_val == 2:
                target_resolution.append('480')
            elif resolution_val == 3:
                target_resolution.append('720')
            elif resolution_val == 4:
                target_resolution.append('1080')
        for k in range(0, len(online_video_resolution)):
            for j in range(0, len(target_resolution)):
                if str(online_video_resolution[k]).__contains__(str(target_resolution[j])):
                    res.append(str(online_video_resolution[k]).strip())
                    break
        return res

    # 指定分辨率地播放单个播放视频URL，并记录pcap、ping、指纹、截图信息
    def get_url_duration(self):
        print('get_url_duration')

        if self.mitm_flag == 1:
            mitmCall = [self.mitmproxy_path]
            mitmProc = subprocess.Popen(mitmCall, executable=self.mitmproxy_path)

        # 获取视频时长以及分辨率信息
        video_url = self.video_url[0]
        if self.loop_get_url(video_url) == 0:
            print('get URL error')
            if self.mitm_flag == 1:
                mitmProc.kill()
            return

        time.sleep(3)
        self.player_click_fun()

        video_duration = -1
        # 循环访问loop_count次，直至成功
        loop_count = 10
        # 获取视频的播放时长
        for i1 in range(0, loop_count):
            if video_duration == -1 or len(video_duration) == 0:
                video_duration = self.get_video_duration()
                time.sleep(1)
            else:
                print(video_duration[0])
                break
        # 获取视频的分辨率信息
        video_resolution = []
        for i2 in range(0, loop_count):
            if len(video_resolution) == 0:
                video_resolution = self.get_video_resolution()
                time.sleep(1)
        print(video_resolution)
        if self.mitm_flag == 1:
            mitmProc.kill()
        if video_duration == -1 or len(video_resolution) == 0:
            print('duration or resolution error')
            return
        # 确定视频采集的分辨率
        target_resolution = self.clawer_resolution_intersection(video_resolution)
        print(target_resolution)
        if target_resolution == []:
            return
        # 确定视频实际播放时长
        duration_of_the_video = self.clawer_video_duration(video_duration)
        if duration_of_the_video < self.time_duration or duration_of_the_video > 2 * self.time_duration:
            return
        else:
            return video_url


if __name__ == '__main__':
    conf_path = "C:/Shrink/bin/video_title_clawer.conf"
    clawer = Batch_clawer_mitm(conf_path)
    clawer.clawer_from_csv()

    # urldir = {}
    # urldir['liuxing'] = clawer.get_url("liuxing", "https://www.youtube.com/feed/trending?bp=6gQJRkVleHBsb3Jl")
    # urldir['shishang'] = clawer.get_url("shishang","https://www.youtube.com/channel/UCrpQ4p1Ql_hG8rKXIKM1MOQ")
    # urldir['xuexi'] = clawer.get_url("xuexi","https://www.youtube.com/channel/UCtFRv9O2AHqOZjjynzrv-xg")
    # urldir['tiyu'] = clawer.get_url("tiyu","https://www.youtube.com/channel/UCEgdi0XIXXZ-qJOFPf4JSKw")
    # urldir['game'] = clawer.get_url("game","https://www.youtube.com/gaming/trending")
    # urldir['xinwen'] = clawer.get_url("xinwen","https://www.youtube.com/channel/UCEl0qh9X3kuL1RdFHng497Q")
    # urldir['lvyou'] = clawer.get_url("lvyou","https://www.youtube.com/results?search_query=%E6%97%85%E6%B8%B8")
    # urldir['shuma'] = clawer.get_url("shuma","https://www.youtube.com/results?search_query=%E6%95%B0%E7%A0%81")
    # urldir['wudao'] = clawer.get_url("wudao","https://www.youtube.com/results?search_query=%E8%88%9E%E8%B9%88")
    # urldir['dongman'] = clawer.get_url("dongman","https://www.youtube.com/results?search_query=%E5%8A%A8%E6%BC%AB")
    # urldir['meishi'] = clawer.get_url("meishi", "https://www.youtube.com/results?search_query=meishi")
    # urldir['wangqiu'] = clawer.get_url("wangqiu", "https://www.youtube.com/results?search_query=wangqiu")
    # urldir['yumaoqiu'] = clawer.get_url("yumaoqiu", "https://www.youtube.com/results?search_query=yumaoqiu")
    # urldir['zuqiu'] = clawer.get_url("zuqiu", "https://www.youtube.com/results?search_query=zuqiu")
    # urldir['lanqiu'] = clawer.get_url("lanqiu", "https://www.youtube.com/results?search_query=lanqiu")
    # urldir['dianjing'] = clawer.get_url("dianjing", "https://www.youtube.com/results?search_query=dianjing")
    # urllist = []
    # for i in urldir.keys():
    #     urllist = urllist + urldir[i]
    # urllist = list(set(urllist))
    # with open('C:/Shrink/data/temp/url.csv', 'w') as f:
    #     f.write('\n')
    #     for url in urllist:
    #         f.write(url + '\n')
