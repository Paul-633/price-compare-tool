#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务模块
支持价格监控和定期采集
"""

import schedule
import time
import json
from datetime import datetime
from typing import List, Dict
from database import DatabaseConfig, create_database
from real_scraper import RealScraperManager


class PriceMonitor:
    """价格监控器"""

    def __init__(self, db_config: DatabaseConfig, config_file: str = "monitor_config.json"):
        self.db_config = db_config
        self.db = create_database(db_config)
        self.config_file = config_file
        self.monitor_list = self._load_monitor_list()

    def _load_monitor_list(self) -> List[Dict]:
        """加载监控列表"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save_monitor_list(self):
        """保存监控列表"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.monitor_list, f, ensure_ascii=False, indent=2)

    def add_monitor(self, keyword: str, platforms: List[str] = None,
                    max_price: float = None, notify: bool = True):
        """添加监控商品"""
        monitor_item = {
            "keyword": keyword,
            "platforms": platforms or ["京东", "淘宝", "拼多多"],
            "max_price": max_price,
            "notify": notify,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 检查是否已存在
        for item in self.monitor_list:
            if item["keyword"] == keyword:
                print(f"⚠️  监控已存在: {keyword}")
                return

        self.monitor_list.append(monitor_item)
        self._save_monitor_list()
        print(f"✅ 已添加监控: {keyword}")

    def remove_monitor(self, keyword: str):
        """移除监控商品"""
        self.monitor_list = [item for item in self.monitor_list if item["keyword"] != keyword]
        self._save_monitor_list()
        print(f"✅ 已移除监控: {keyword}")

    def list_monitors(self) -> List[Dict]:
        """列出所有监控"""
        return self.monitor_list

    def check_prices(self):
        """检查所有监控商品的价格"""
        print(f"\n{'='*80}")
        print(f" 价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ".center(80, '='))
        print(f"{'='*80}\n")

        scraper_manager = RealScraperManager(use_proxy=True, use_cookie=True)
        alerts = []

        for monitor in self.monitor_list:
            keyword = monitor["keyword"]
            platforms = monitor["platforms"]
            max_price = monitor.get("max_price")

            print(f"🔍 检查: {keyword}")

            for platform in platforms:
                try:
                    products = scraper_manager.search_platform(platform, keyword, max_pages=1)

                    if not products:
                        continue

                    # 保存到数据库
                    product_dicts = [p.to_dict() for p in products]
                    self.db.save_products(product_dicts)

                    # 检查价格
                    if max_price:
                        low_price_products = [p for p in products if p.price <= max_price]

                        if low_price_products:
                            for p in low_price_products:
                                alert = {
                                    "keyword": keyword,
                                    "platform": p.platform,
                                    "product": p.name,
                                    "price": p.price,
                                    "target_price": max_price,
                                    "url": p.url
                                }
                                alerts.append(alert)
                                print(f"  💰 低价提醒: {p.name}")
                                print(f"     价格: ¥{p.price} (目标: ¥{max_price})")
                                print(f"     平台: {p.platform}")
                                print(f"     链接: {p.url}\n")

                    # 显示最低价
                    min_price_product = min(products, key=lambda x: x.price)
                    print(f"  📊 最低价: ¥{min_price_product.price} ({min_price_product.platform})")

                except Exception as e:
                    print(f"  ❌ 检查失败: {e}")

        # 发送通知
        if alerts and any(m.get("notify") for m in self.monitor_list):
            self._send_notification(alerts)

        # 记录搜索日志
        self.db.log_search("价格监控", len(alerts))

        print(f"\n{'='*80}")
        print(f" 监控完成，共发现 {len(alerts)} 个低价商品 ".center(80, '='))
        print(f"{'='*80}\n")

    def _send_notification(self, alerts: List[Dict]):
        """发送价格提醒通知"""
        print("\n📢 价格提醒通知:")
        for alert in alerts:
            print(f"  - {alert['product']}")
            print(f"    价格: ¥{alert['price']} (目标: ¥{alert['target_price']})")
            print(f"    平台: {alert['platform']}")
            print(f"    链接: {alert['url']}")

        # 这里可以集成邮件、微信、钉钉等通知方式
        # 示例：发送邮件
        # self._send_email_notification(alerts)

    def _send_email_notification(self, alerts: List[Dict]):
        """发送邮件通知（示例）"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # 配置邮件服务器
        smtp_server = "smtp.example.com"
        smtp_port = 587
        smtp_user = "your_email@example.com"
        smtp_password = "your_password"

        # 构建邮件内容
        subject = f"价格提醒 - {len(alerts)} 个商品降价"
        body = "以下商品已降价至目标价格以下:\n\n"

        for alert in alerts:
            body += f"商品: {alert['product']}\n"
            body += f"价格: ¥{alert['price']} (目标: ¥{alert['target_price']})\n"
            body += f"平台: {alert['platform']}\n"
            body += f"链接: {alert['url']}\n\n"

        # 发送邮件
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = smtp_user
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()

            print("✅ 邮件通知已发送")
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")


class TaskScheduler:
    """任务调度器"""

    def __init__(self, price_monitor: PriceMonitor):
        self.price_monitor = price_monitor

    def schedule_price_check(self, time_str: str = "09:00"):
        """设置每日价格检查任务"""
        schedule.every().day.at(time_str).do(self.price_monitor.check_prices)
        print(f"✅ 已设置每日 {time_str} 价格检查任务")

    def schedule_price_check_interval(self, minutes: int = 60):
        """设置价格检查间隔（分钟）"""
        schedule.every(minutes).minutes.do(self.price_monitor.check_prices)
        print(f"✅ 已设置每 {minutes} 分钟价格检查任务")

    def run(self):
        """运行调度器"""
        print("\n🚀 任务调度器已启动")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  任务调度器已停止")


if __name__ == '__main__':
    # 测试定时任务
    db_config = DatabaseConfig(db_type="sqlite", db_path="products.db")
    monitor = PriceMonitor(db_config)

    # 添加监控
    monitor.add_monitor("无线蓝牙耳机", max_price=200)
    monitor.add_monitor("智能手机", max_price=2000)

    # 查看监控列表
    print("\n监控列表:")
    for item in monitor.list_monitors():
        print(f"  - {item['keyword']} (目标价: ¥{item.get('max_price', '无')})")

    # 立即检查一次
    monitor.check_prices()

    # 设置定时任务
    scheduler = TaskScheduler(monitor)
    scheduler.schedule_price_check("09:00")
    scheduler.schedule_price_check("21:00")

    # 运行调度器
    # scheduler.run()
