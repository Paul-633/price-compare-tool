#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实电商平台爬虫模块
支持京东、淘宝、拼多多
包含反爬机制：代理池、Cookie池、请求头轮换、延时控制
"""

import random
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import json
import hashlib
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Product:
    """商品数据模型"""
    name: str
    price: float
    sales: int
    shop_name: str
    shop_score: float
    url: str
    platform: str
    image_url: str = ""
    category: str = ""
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "price": self.price,
            "sales": self.sales,
            "shop_name": self.shop_name,
            "shop_score": self.shop_score,
            "url": self.url,
            "platform": self.platform,
            "image_url": self.image_url,
            "category": self.category,
            "collected_at": self.collected_at
        }


class ProxyPool:
    """代理池管理器"""

    def __init__(self, proxy_file: str = "proxies.txt"):
        self.proxies = []
        self.current_index = 0
        self.proxy_file = proxy_file
        self._load_proxies()

    def _load_proxies(self):
        """从文件加载代理列表"""
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(line)
        except FileNotFoundError:
            print(f"⚠️  代理文件 {self.proxy_file} 不存在，使用直连模式")
            self.proxies = []

    def get_proxy(self) -> Optional[Dict]:
        """获取一个代理"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1

        return {
            "http": proxy,
            "https": proxy
        }

    def add_proxy(self, proxy: str):
        """添加代理"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)

    def remove_proxy(self, proxy: str):
        """移除代理"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)


class CookiePool:
    """Cookie池管理器"""

    def __init__(self, cookie_file: str = "cookies.json"):
        self.cookies = {}
        self.cookie_file = cookie_file
        self._load_cookies()

    def _load_cookies(self):
        """从文件加载Cookie"""
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                self.cookies = json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Cookie文件 {self.cookie_file} 不存在")
            self.cookies = {}

    def get_cookie(self, platform: str) -> Optional[Dict]:
        """获取指定平台的Cookie"""
        return self.cookies.get(platform)

    def set_cookie(self, platform: str, cookie: Dict):
        """设置平台Cookie"""
        self.cookies[platform] = cookie
        self._save_cookies()

    def _save_cookies(self):
        """保存Cookie到文件"""
        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump(self.cookies, f, ensure_ascii=False, indent=2)


class UserAgentPool:
    """User-Agent池"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    @classmethod
    def get_random_ua(cls) -> str:
        """获取随机User-Agent"""
        return random.choice(cls.USER_AGENTS)


class RobotsChecker:
    """robots.txt检查器"""

    def __init__(self):
        self.robots_cache = {}

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """检查是否允许抓取"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url not in self.robots_cache:
            robots_url = urljoin(base_url, "/robots.txt")
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                self.robots_cache[base_url] = rp
            except Exception as e:
                print(f"⚠️  无法读取 {robots_url}: {e}")
                return True  # 如果无法读取robots.txt，默认允许

        rp = self.robots_cache[base_url]
        return rp.can_fetch(user_agent, url)


class BaseRealScraper:
    """真实爬虫基类"""

    platform_name = "Unknown"
    base_url = ""

    def __init__(self, proxy_pool: ProxyPool = None, cookie_pool: CookiePool = None):
        self.proxy_pool = proxy_pool or ProxyPool()
        self.cookie_pool = cookie_pool or CookiePool()
        self.robots_checker = RobotsChecker()
        self.session = requests.Session()
        self.request_delay = (1, 3)  # 请求延迟范围（秒）

    def _get_headers(self) -> Dict:
        """获取请求头"""
        return {
            "User-Agent": UserAgentPool.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _make_request(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        """发送HTTP请求"""
        # 检查robots.txt
        if not self.robots_checker.can_fetch(url):
            print(f"⚠️  robots.txt禁止抓取: {url}")
            return None

        # 随机延迟
        delay = random.uniform(*self.request_delay)
        time.sleep(delay)

        headers = self._get_headers()
        cookies = self.cookie_pool.get_cookie(self.platform_name)
        proxy = self.proxy_pool.get_proxy()

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                proxies=proxy,
                timeout=10
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"❌ 请求失败: {e}")
            if proxy:
                proxy_str = list(proxy.values())[0]
                self.proxy_pool.remove_proxy(proxy_str)
                print(f"🗑️  已移除失效代理: {proxy_str}")
            return None

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        """搜索商品（子类实现）"""
        raise NotImplementedError


class JDRealScraper(BaseRealScraper):
    """京东真实爬虫"""

    platform_name = "京东"
    base_url = "https://search.jd.com"

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        """搜索京东商品"""
        print(f"  🔍 正在从京东搜索: {keyword}")

        url = f"{self.base_url}/Search"
        params = {
            "keyword": keyword,
            "page": page,
            "s": 1,
            "click": 0
        }

        response = self._make_request(url, params)
        if not response:
            return []

        return self._parse_response(response.text, keyword)

    def _parse_response(self, html: str, keyword: str) -> List[Product]:
        """解析京东搜索结果"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')

        # 京东商品列表选择器
        items = soup.select('.gl-item')

        for item in items[:20]:  # 限制数量
            try:
                # 商品名称
                name_elem = item.select_one('.p-name a em')
                if not name_elem:
                    continue
                name = name_elem.get_text().strip()

                # 价格
                price_elem = item.select_one('.p-price strong i')
                price = float(price_elem.get_text()) if price_elem else 0.0

                # 评论数（作为销量参考）
                comment_elem = item.select_one('.p-commit strong a')
                sales_text = comment_elem.get_text() if comment_elem else "0"
                sales = self._parse_sales(sales_text)

                # 店铺名称
                shop_elem = item.select_one('.p-shop a')
                shop_name = shop_elem.get_text().strip() if shop_elem else "未知店铺"

                # 店铺评分（京东默认显示，这里用随机值模拟）
                shop_score = round(random.uniform(4.5, 5.0), 1)

                # 商品链接
                link_elem = item.select_one('.p-name a')
                url = link_elem.get('href', '') if link_elem else ""
                if url and not url.startswith('http'):
                    url = urljoin('https://item.jd.com', url)

                # 图片
                img_elem = item.select_one('.p-img img')
                image_url = img_elem.get('data-lazy-img') or img_elem.get('src', '') if img_elem else ""

                products.append(Product(
                    name=name,
                    price=price,
                    sales=sales,
                    shop_name=shop_name,
                    shop_score=shop_score,
                    url=url,
                    platform=self.platform_name,
                    image_url=image_url,
                    category=keyword
                ))

            except Exception as e:
                print(f"⚠️  解析商品失败: {e}")
                continue

        print(f"  ✅ 京东采集到 {len(products)} 件商品")
        return products

    def _parse_sales(self, text: str) -> int:
        """解析销量文本"""
        text = text.replace('+', '').replace('万', '0000').replace('评', '')
        try:
            return int(float(text))
        except:
            return 0


class TaobaoRealScraper(BaseRealScraper):
    """淘宝真实爬虫"""

    platform_name = "淘宝"
    base_url = "https://s.taobao.com"

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        """搜索淘宝商品"""
        print(f"  🔍 正在从淘宝搜索: {keyword}")

        url = f"{self.base_url}/search"
        params = {
            "q": keyword,
            "s": (page - 1) * 44,
            "initiative_id": "tbindexz_20170306"
        }

        response = self._make_request(url, params)
        if not response:
            return []

        return self._parse_response(response.text, keyword)

    def _parse_response(self, html: str, keyword: str) -> List[Product]:
        """解析淘宝搜索结果"""
        products = []

        # 淘宝使用JSON数据
        try:
            # 尝试提取JSON数据
            import re
            json_match = re.search(r'g_page_config\s*=\s*({.*?});', html, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                items = data.get('mods', {}).get('itemlist', {}).get('data', {}).get('auctions', [])

                for item in items[:20]:
                    try:
                        name = item.get('raw_title', '')
                        price = float(item.get('view_price', 0))
                        sales = int(item.get('view_sales', '0').replace('人付款', ''))
                        shop_name = item.get('nick', '')
                        shop_score = float(item.get('seller_rate', 0)) / 100
                        url = item.get('detail_url', '')
                        image_url = item.get('pic_url', '')

                        if url and not url.startswith('http'):
                            url = urljoin('https://item.taobao.com', url)

                        products.append(Product(
                            name=name,
                            price=price,
                            sales=sales,
                            shop_name=shop_name,
                            shop_score=min(shop_score, 5.0),
                            url=url,
                            platform=self.platform_name,
                            image_url=image_url,
                            category=keyword
                        ))
                    except Exception as e:
                        print(f"⚠️  解析淘宝商品失败: {e}")
                        continue

        except Exception as e:
            print(f"⚠️  解析淘宝数据失败: {e}")

        print(f"  ✅ 淘宝采集到 {len(products)} 件商品")
        return products


class PDDRealScraper(BaseRealScraper):
    """拼多多真实爬虫"""

    platform_name = "拼多多"
    base_url = "https://mobile.yangkeduo.com"

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        """搜索拼多多商品"""
        print(f"  🔍 正在从拼多多搜索: {keyword}")

        # 拼多多移动端搜索接口
        url = f"{self.base_url}/search_result"
        params = {
            "search_key": keyword,
            "page": page,
            "size": 20
        }

        response = self._make_request(url, params)
        if not response:
            return []

        return self._parse_response(response.text, keyword)

    def _parse_response(self, html: str, keyword: str) -> List[Product]:
        """解析拼多多搜索结果"""
        products = []

        try:
            # 拼多多也使用JSON数据
            import re
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                items = data.get('searchResult', {}).get('items', [])

                for item in items[:20]:
                    try:
                        name = item.get('goodsName', '')
                        price = float(item.get('minNormalPrice', 0)) / 100  # 拼多多价格单位是分
                        sales = int(item.get('salesTip', '0').replace('万+', '0000'))
                        shop_name = item.get('mallName', '')
                        shop_score = float(item.get('mallServiceScore', 0))
                        url = f"https://mobile.yangkeduo.com/goods.html?goods_id={item.get('goodsId', '')}"
                        image_url = item.get('thumbUrl', '')

                        products.append(Product(
                            name=name,
                            price=price,
                            sales=sales,
                            shop_name=shop_name,
                            shop_score=min(shop_score, 5.0),
                            url=url,
                            platform=self.platform_name,
                            image_url=image_url,
                            category=keyword
                        ))
                    except Exception as e:
                        print(f"⚠️  解析拼多多商品失败: {e}")
                        continue

        except Exception as e:
            print(f"⚠️  解析拼多多数据失败: {e}")

        print(f"  ✅ 拼多多采集到 {len(products)} 件商品")
        return products


class RealScraperManager:
    """真实爬虫管理器"""

    def __init__(self, use_proxy: bool = True, use_cookie: bool = True):
        self.proxy_pool = ProxyPool() if use_proxy else None
        self.cookie_pool = CookiePool() if use_cookie else None

        self.scrapers = [
            JDRealScraper(self.proxy_pool, self.cookie_pool),
            TaobaoRealScraper(self.proxy_pool, self.cookie_pool),
            PDDRealScraper(self.proxy_pool, self.cookie_pool),
        ]

    def search_all(self, keyword: str, max_pages: int = 1) -> List[Product]:
        """从所有平台搜索"""
        all_products = []

        for scraper in self.scrapers:
            for page in range(1, max_pages + 1):
                products = scraper.search(keyword, page)
                all_products.extend(products)

        return all_products

    def search_platform(self, platform: str, keyword: str, max_pages: int = 1) -> List[Product]:
        """从指定平台搜索"""
        platform_map = {
            "京东": JDRealScraper,
            "淘宝": TaobaoRealScraper,
            "拼多多": PDDRealScraper,
        }

        scraper_class = platform_map.get(platform)
        if not scraper_class:
            print(f"❌ 不支持的平台: {platform}")
            return []

        scraper = scraper_class(self.proxy_pool, self.cookie_pool)
        all_products = []

        for page in range(1, max_pages + 1):
            products = scraper.search(keyword, page)
            all_products.extend(products)

        return all_products


if __name__ == '__main__':
    # 测试真实爬虫
    manager = RealScraperManager(use_proxy=False, use_cookie=False)
    products = manager.search_all("无线蓝牙耳机", max_pages=1)

    print(f"\n共采集到 {len(products)} 件商品")
    for p in products[:5]:
        print(f"  {p.platform}: {p.name} - ¥{p.price}")
