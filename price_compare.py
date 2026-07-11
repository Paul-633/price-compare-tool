#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商商品价格自动化采集与对比工具
支持京东、淘宝、拼多多等主流电商平台

功能特性：
- 真实爬虫采集（支持代理池、Cookie池、请求头轮换）
- 数据持久化（SQLite/MySQL）
- 价格监控与定时任务
- 数据清洗、去重、排序
- 性价比分析与推荐
- HTML报告与价格趋势图生成
"""

import argparse
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

# 导入新模块
try:
    from database import DatabaseConfig, create_database
    from real_scraper import RealScraperManager
    from scheduler import PriceMonitor, TaskScheduler
    ADVANCED_FEATURES = True
except ImportError as e:
    print(f"⚠️  高级功能模块导入失败: {e}")
    print("   请安装依赖: pip install -r requirements.txt")
    ADVANCED_FEATURES = False


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
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'Product':
        return Product(**data)


class BaseScraper:
    """采集器基类"""
    platform_name = "Unknown"

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        raise NotImplementedError


class MockScraper(BaseScraper):
    """模拟采集器 - 用于演示和测试"""
    platform_name = "模拟平台"

    # 模拟商品数据模板
    TEMPLATES = [
        {"name": "{} 无线蓝牙耳机 降噪入耳式", "price_range": (99, 599), "category": "数码"},
        {"name": "{} 智能手机 5G全网通", "price_range": (999, 5999), "category": "手机"},
        {"name": "{} 笔记本电脑 轻薄本", "price_range": (2999, 8999), "category": "电脑"},
        {"name": "{} 机械键盘 游戏电竞", "price_range": (199, 799), "category": "外设"},
        {"name": "{} 显示器 27寸4K", "price_range": (899, 2999), "category": "显示器"},
        {"name": "{} 运动鞋 男女同款", "price_range": (199, 899), "category": "运动"},
        {"name": "{} 保温杯 316不锈钢", "price_range": (59, 199), "category": "家居"},
        {"name": "{} 充电宝 20000mAh", "price_range": (79, 299), "category": "配件"},
    ]

    SHOP_NAMES = [
        "官方旗舰店", "品牌专卖店", "数码旗舰店", "官方直营店",
        "品质优选店", "正品保证店", "工厂直销店", "品牌授权店"
    ]

    def search(self, keyword: str, page: int = 1) -> List[Product]:
        """模拟搜索商品"""
        products = []
        num_products = random.randint(8, 15)

        for i in range(num_products):
            template = random.choice(self.TEMPLATES)
            name = template["name"].format(keyword)
            price = round(random.uniform(*template["price_range"]), 2)
            sales = random.randint(100, 50000)
            shop_name = random.choice(self.SHOP_NAMES)
            shop_score = round(random.uniform(4.0, 5.0), 1)
            url = f"https://mock.example.com/product/{hashlib.md5(name.encode()).hexdigest()[:12]}"
            image_url = f"https://via.placeholder.com/200x200?text={keyword}"

            products.append(Product(
                name=name,
                price=price,
                sales=sales,
                shop_name=shop_name,
                shop_score=shop_score,
                url=url,
                platform=self.platform_name,
                image_url=image_url,
                category=template["category"],
            ))

        return products


class JDScraper(MockScraper):
    """京东采集器（模拟实现）"""
    platform_name = "京东"


class TaobaoScraper(MockScraper):
    """淘宝采集器（模拟实现）"""
    platform_name = "淘宝"


class PDDScraper(MockScraper):
    """拼多多采集器（模拟实现）"""
    platform_name = "拼多多"


class DataCleaner:
    """数据清洗器"""

    @staticmethod
    def clean(products: List[Product]) -> List[Product]:
        """清洗数据：去除无效数据"""
        cleaned = []
        for p in products:
            # 过滤无效价格
            if p.price <= 0:
                continue
            # 过滤无效销量
            if p.sales < 0:
                continue
            # 过滤无效评分
            if p.shop_score < 0 or p.shop_score > 5:
                continue
            cleaned.append(p)
        return cleaned


class Deduplicator:
    """去重处理器"""

    @staticmethod
    def deduplicate(products: List[Product]) -> List[Product]:
        """基于商品名称和平台去重"""
        seen = set()
        unique = []
        for p in products:
            key = f"{p.name}_{p.platform}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique


class RankingAnalyzer:
    """排序分析器"""

    @staticmethod
    def sort_by_price(products: List[Product], reverse: bool = False) -> List[Product]:
        """按价格排序"""
        return sorted(products, key=lambda x: x.price, reverse=reverse)

    @staticmethod
    def sort_by_sales(products: List[Product], reverse: bool = True) -> List[Product]:
        """按销量排序"""
        return sorted(products, key=lambda x: x.sales, reverse=reverse)

    @staticmethod
    def sort_by_score(products: List[Product], reverse: bool = True) -> List[Product]:
        """按店铺评分排序"""
        return sorted(products, key=lambda x: x.shop_score, reverse=reverse)

    @staticmethod
    def calculate_value_score(product: Product) -> float:
        """
        计算性价比评分
        综合考虑价格、销量、评分
        """
        # 销量权重 0.4，评分权重 0.3，价格倒数权重 0.3
        sales_score = min(product.sales / 10000, 1.0)  # 归一化到0-1
        shop_score = product.shop_score / 5.0  # 归一化到0-1
        price_score = 1.0 / (1.0 + product.price / 1000)  # 价格越低分越高

        value_score = (sales_score * 0.4 + shop_score * 0.3 + price_score * 0.3) * 100
        return round(value_score, 2)

    @staticmethod
    def recommend_best(products: List[Product], top_n: int = 3) -> List[Dict]:
        """推荐性价比最高的商品"""
        scored = []
        for p in products:
            score = RankingAnalyzer.calculate_value_score(p)
            scored.append({
                "product": p,
                "value_score": score
            })
        scored.sort(key=lambda x: x["value_score"], reverse=True)
        return scored[:top_n]


class PriceHistoryGenerator:
    """价格历史数据生成器（模拟）"""

    @staticmethod
    def generate(product_name: str, days: int = 30) -> List[Dict]:
        """生成模拟的价格历史数据"""
        history = []
        base_price = random.uniform(100, 5000)

        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
            # 价格在基准价上下浮动10%
            fluctuation = random.uniform(-0.1, 0.1)
            price = round(base_price * (1 + fluctuation), 2)
            history.append({
                "date": date,
                "price": price,
                "product": product_name
            })

        return history


class TerminalPresenter:
    """终端展示器"""

    @staticmethod
    def print_table(products: List[Product], title: str = "商品列表"):
        """打印表格到终端"""
        print(f"\n{'='*100}")
        print(f" {title} ".center(100, '='))
        print(f"{'='*100}")
        print(f"{'序号':<6} {'商品名称':<30} {'价格':<10} {'销量':<10} {'店铺':<15} {'评分':<6} {'平台':<8}")
        print(f"{'-'*100}")

        for i, p in enumerate(products, 1):
            name = p.name[:28] + ".." if len(p.name) > 30 else p.name
            shop = p.shop_name[:13] + ".." if len(p.shop_name) > 15 else p.shop_name
            print(f"{i:<6} {name:<30} ¥{p.price:<9.2f} {p.sales:<10} {shop:<15} {p.shop_score:<6} {p.platform:<8}")

        print(f"{'='*100}\n")

    @staticmethod
    def print_recommendations(recommendations: List[Dict]):
        """打印推荐结果"""
        print(f"\n{'*'*100}")
        print(" 性价比推荐 TOP 3 ".center(100, '*'))
        print(f"{'*'*100}")

        for i, rec in enumerate(recommendations, 1):
            p = rec["product"]
            score = rec["value_score"]
            print(f"\n  第{i}名 - 性价比评分: {score}")
            print(f"  商品: {p.name}")
            print(f"  价格: ¥{p.price:.2f}")
            print(f"  销量: {p.sales}")
            print(f"  店铺: {p.shop_name} (评分: {p.shop_score})")
            print(f"  平台: {p.platform}")

        print(f"\n{'*'*100}\n")


class HTMLReporter:
    """HTML报告生成器"""

    @staticmethod
    def generate_report(products: List[Product], keyword: str, output_path: str = "report.html"):
        """生成HTML报告"""
        recommendations = RankingAnalyzer.recommend_best(products)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{keyword} - 价格对比报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}
        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .stat-item {{ text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #6c757d; margin-top: 5px; }}
        .recommendations {{
            padding: 40px;
            background: #fff3cd;
        }}
        .recommendations h2 {{
            color: #856404;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .rec-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .rec-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-left: 4px solid #ffc107;
        }}
        .rec-rank {{
            display: inline-block;
            background: #ffc107;
            color: #856404;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .rec-score {{
            font-size: 1.5em;
            font-weight: bold;
            color: #28a745;
            margin: 10px 0;
        }}
        .products {{ padding: 40px; }}
        .products h2 {{ margin-bottom: 20px; color: #333; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .price {{ color: #dc3545; font-weight: bold; font-size: 1.1em; }}
        .platform {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .platform-jd {{ background: #e3f2fd; color: #1976d2; }}
        .platform-taobao {{ background: #fff3e0; color: #f57c00; }}
        .platform-pdd {{ background: #fce4ec; color: #c2185b; }}
        .platform-mock {{ background: #f3e5f5; color: #7b1fa2; }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛍️ {keyword}</h1>
            <p>价格对比报告 - 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{len(products)}</div>
                <div class="stat-label">商品总数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">¥{min(p.price for p in products):.2f}</div>
                <div class="stat-label">最低价格</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">¥{max(p.price for p in products):.2f}</div>
                <div class="stat-label">最高价格</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">¥{sum(p.price for p in products)/len(products):.2f}</div>
                <div class="stat-label">平均价格</div>
            </div>
        </div>

        <div class="recommendations">
            <h2>🏆 性价比推荐</h2>
            <div class="rec-grid">
"""

        for i, rec in enumerate(recommendations, 1):
            p = rec["product"]
            platform_class = f"platform-{p.platform.lower()}"
            html += f"""
                <div class="rec-card">
                    <span class="rec-rank">第{i}名</span>
                    <div class="rec-score">性价比评分: {rec["value_score"]}</div>
                    <h3>{p.name}</h3>
                    <p class="price">¥{p.price:.2f}</p>
                    <p>销量: {p.sales} | 店铺: {p.shop_name}</p>
                    <p>评分: {p.shop_score} | <span class="platform {platform_class}">{p.platform}</span></p>
                </div>
"""

        html += """
            </div>
        </div>

        <div class="products">
            <h2>📊 全部商品列表（按价格排序）</h2>
            <table>
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>商品名称</th>
                        <th>价格</th>
                        <th>销量</th>
                        <th>店铺</th>
                        <th>评分</th>
                        <th>平台</th>
                    </tr>
                </thead>
                <tbody>
"""

        for i, p in enumerate(products, 1):
            platform_class = f"platform-{p.platform.lower()}"
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{p.name}</td>
                        <td class="price">¥{p.price:.2f}</td>
                        <td>{p.sales}</td>
                        <td>{p.shop_name}</td>
                        <td>{p.shop_score}</td>
                        <td><span class="platform {platform_class}">{p.platform}</span></td>
                    </tr>
"""

        html += f"""
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>本报告由电商价格采集对比工具自动生成 | 数据仅供参考</p>
        </div>
    </div>
</body>
</html>
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path


class PriceChartGenerator:
    """价格趋势图生成器"""

    @staticmethod
    def generate_chart(products: List[Product], output_path: str = "price_chart.html"):
        """生成价格趋势图（使用Chart.js）"""
        # 为每个平台生成价格历史
        platforms = set(p.platform for p in products)
        datasets = []
        colors = ['#667eea', '#f57c00', '#c2185b', '#28a745']

        for i, platform in enumerate(platforms):
            platform_products = [p for p in products if p.platform == platform]
            if platform_products:
                avg_price = sum(p.price for p in platform_products) / len(platform_products)
                history = PriceHistoryGenerator.generate(platform, 30)
                datasets.append({
                    "label": platform,
                    "data": [h["price"] for h in history],
                    "borderColor": colors[i % len(colors)],
                    "backgroundColor": colors[i % len(colors)] + "33",
                    "tension": 0.4
                })

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>价格趋势图</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
        .chart-container {{
            position: relative;
            height: 500px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 价格趋势分析（近30天）</h1>
        <div class="chart-container">
            <canvas id="priceChart"></canvas>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('priceChart').getContext('2d');

        const labels = Array.from({{length: 30}}, (_, i) => {{
            const date = new Date();
            date.setDate(date.getDate() - (29 - i));
            return date.toLocaleDateString('zh-CN', {{month: 'short', day: 'numeric'}});
        }});

        const data = {{
            labels: labels,
            datasets: {json.dumps(datasets)}
        }};

        new Chart(ctx, {{
            type: 'line',
            data: data,
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '各平台价格趋势对比',
                        font: {{ size: 18 }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ¥' + context.parsed.y.toFixed(2);
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{
                            callback: function(value) {{
                                return '¥' + value.toFixed(0);
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path


class PriceCompareTool:
    """价格对比工具主类"""

    def __init__(self, use_real_scraper: bool = False, db_config: DatabaseConfig = None):
        """
        初始化工具
        
        Args:
            use_real_scraper: 是否使用真实爬虫（默认False，使用模拟数据）
            db_config: 数据库配置（可选）
        """
        self.use_real_scraper = use_real_scraper and ADVANCED_FEATURES
        self.db = None
        
        if db_config and ADVANCED_FEATURES:
            try:
                self.db = create_database(db_config)
                print("✅ 数据库连接成功")
            except Exception as e:
                print(f"⚠️  数据库初始化失败: {e}")
        
        if not self.use_real_scraper:
            # 使用模拟采集器
            self.scrapers = [
                JDScraper(),
                TaobaoScraper(),
                PDDScraper(),
                MockScraper()
            ]
        else:
            # 使用真实爬虫管理器
            self.scraper_manager = RealScraperManager(use_proxy=True, use_cookie=True)

    def collect(self, keyword: str) -> List[Product]:
        """采集商品数据"""
        print(f"\n🔍 正在采集关键词: {keyword}")
        all_products = []

        if self.use_real_scraper:
            # 使用真实爬虫
            print("  使用真实爬虫采集...")
            try:
                products = self.scraper_manager.search_all(keyword, max_pages=1)
                all_products = products
            except Exception as e:
                print(f"❌ 真实爬虫采集失败: {e}")
                print("  回退到模拟数据...")
                self.use_real_scraper = False
                return self.collect(keyword)
        else:
            # 使用模拟采集器
            for scraper in self.scrapers:
                print(f"  正在从 {scraper.platform_name} 采集...")
                products = scraper.search(keyword)
                all_products.extend(products)
                time.sleep(0.5)  # 模拟请求延迟

        print(f"✅ 共采集到 {len(all_products)} 条商品数据")
        return all_products

    def process(self, products: List[Product]) -> List[Product]:
        """处理数据：清洗、去重、排序"""
        print("\n🧹 正在清洗数据...")
        cleaned = DataCleaner.clean(products)
        print(f"  清洗后剩余 {len(cleaned)} 条")

        print("🔄 正在去重...")
        unique = Deduplicator.deduplicate(cleaned)
        print(f"  去重后剩余 {len(unique)} 条")

        print("📊 正在按价格排序...")
        sorted_products = RankingAnalyzer.sort_by_price(unique)

        return sorted_products

    def analyze(self, products: List[Product]) -> List[Dict]:
        """分析数据：计算性价比并推荐"""
        return RankingAnalyzer.recommend_best(products)

    def save_to_database(self, products: List[Product], keyword: str):
        """保存数据到数据库"""
        if not self.db:
            return
        
        try:
            product_dicts = [p.to_dict() for p in products]
            saved_count = self.db.save_products(product_dicts)
            self.db.log_search(keyword, len(products))
            print(f"💾 已保存 {saved_count} 条数据到数据库")
        except Exception as e:
            print(f"⚠️  保存数据库失败: {e}")

    def run(self, keyword: str, output_html: bool = True, output_chart: bool = True, 
            save_db: bool = True):
        """运行完整流程"""
        print("\n" + "="*100)
        print(f" 电商商品价格采集与对比工具 ".center(100, '='))
        print("="*100)

        # 1. 采集
        products = self.collect(keyword)

        # 2. 处理
        processed = self.process(products)

        # 3. 展示
        TerminalPresenter.print_table(processed, f"{keyword} - 商品列表")

        # 4. 分析
        recommendations = self.analyze(processed)
        TerminalPresenter.print_recommendations(recommendations)

        # 5. 保存到数据库
        if save_db:
            self.save_to_database(processed, keyword)

        # 6. 生成报告
        if output_html:
            report_path = HTMLReporter.generate_report(processed, keyword)
            print(f"📄 HTML报告已生成: {report_path}")

        if output_chart:
            chart_path = PriceChartGenerator.generate_chart(processed)
            print(f"📈 价格趋势图已生成: {chart_path}")

        # 7. 导出数据
        data_path = f"{keyword}_data.json"
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump([p.to_dict() for p in processed], f, ensure_ascii=False, indent=2)
        print(f"💾 数据已导出: {data_path}")

        print("\n✨ 采集分析完成！")
        return processed, recommendations


def main():
    parser = argparse.ArgumentParser(
        description='电商商品价格自动化采集与对比工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础采集（模拟数据）
  python price_compare.py 无线蓝牙耳机
  
  # 使用真实爬虫
  python price_compare.py 智能手机 --real-scraper
  
  # 指定数据库
  python price_compare.py 笔记本电脑 --db-type sqlite --db-path products.db
  
  # 价格监控模式
  python price_compare.py --monitor --add-monitor "无线蓝牙耳机:200"
  
  # 查看监控列表
  python price_compare.py --list-monitors
        """
    )

    # 基础参数
    parser.add_argument('keyword', nargs='?', help='搜索关键词')
    parser.add_argument('--no-html', action='store_true', help='不生成HTML报告')
    parser.add_argument('--no-chart', action='store_true', help='不生成价格趋势图')
    parser.add_argument('--no-db', action='store_true', help='不保存到数据库')
    
    # 高级功能参数
    if ADVANCED_FEATURES:
        parser.add_argument('--real-scraper', action='store_true', 
                          help='使用真实爬虫（默认使用模拟数据）')
        parser.add_argument('--db-type', choices=['sqlite', 'mysql'], 
                          default='sqlite', help='数据库类型（默认sqlite）')
        parser.add_argument('--db-path', default='products.db',
                          help='SQLite数据库路径（默认products.db）')
        parser.add_argument('--db-host', default='localhost',
                          help='MySQL主机地址（默认localhost）')
        parser.add_argument('--db-port', type=int, default=3306,
                          help='MySQL端口（默认3306）')
        parser.add_argument('--db-user', default='root',
                          help='MySQL用户名（默认root）')
        parser.add_argument('--db-password', default='',
                          help='MySQL密码')
        parser.add_argument('--db-name', default='price_compare',
                          help='MySQL数据库名（默认price_compare）')
        
        # 价格监控参数
        parser.add_argument('--monitor', action='store_true',
                          help='启动价格监控模式')
        parser.add_argument('--add-monitor', metavar='KEYWORD:PRICE',
                          help='添加监控商品，格式：关键词:目标价格')
        parser.add_argument('--remove-monitor', metavar='KEYWORD',
                          help='移除监控商品')
        parser.add_argument('--list-monitors', action='store_true',
                          help='列出所有监控商品')
        parser.add_argument('--schedule', metavar='TIME',
                          help='设置定时检查时间，格式：HH:MM（如09:00）')

    args = parser.parse_args()

    # 处理监控相关命令
    if ADVANCED_FEATURES and (args.list_monitors or args.add_monitor or 
                               args.remove_monitor or args.monitor):
        handle_monitor_commands(args)
        return

    # 检查是否有关键词
    if not args.keyword:
        parser.error("请提供搜索关键词或使用监控命令")

    # 配置数据库
    db_config = None
    if not args.no_db and ADVANCED_FEATURES:
        if args.db_type == 'sqlite':
            db_config = DatabaseConfig(
                db_type='sqlite',
                db_path=args.db_path
            )
        elif args.db_type == 'mysql':
            db_config = DatabaseConfig(
                db_type='mysql',
                host=args.db_host,
                port=args.db_port,
                user=args.db_user,
                password=args.db_password,
                database=args.db_name
            )

    # 创建工具实例
    tool = PriceCompareTool(
        use_real_scraper=getattr(args, 'real_scraper', False),
        db_config=db_config
    )

    # 运行采集
    tool.run(
        keyword=args.keyword,
        output_html=not args.no_html,
        output_chart=not args.no_chart,
        save_db=not args.no_db
    )


def handle_monitor_commands(args):
    """处理监控相关命令"""
    if not ADVANCED_FEATURES:
        print("❌ 高级功能未启用，请安装依赖: pip install -r requirements.txt")
        return

    # 配置数据库
    if args.db_type == 'sqlite':
        db_config = DatabaseConfig(db_type='sqlite', db_path=args.db_path)
    else:
        db_config = DatabaseConfig(
            db_type='mysql',
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name
        )

    monitor = PriceMonitor(db_config)

    # 列出监控
    if args.list_monitors:
        monitors = monitor.list_monitors()
        if not monitors:
            print("\n📋 当前没有监控商品")
        else:
            print(f"\n📋 监控列表（共 {len(monitors)} 个）:")
            for i, item in enumerate(monitors, 1):
                price_info = f"目标价: ¥{item.get('max_price')}" if item.get('max_price') else "无目标价"
                platforms = ", ".join(item.get('platforms', []))
                print(f"  {i}. {item['keyword']} ({price_info})")
                print(f"     平台: {platforms}")
                print(f"     添加时间: {item.get('added_at', '未知')}")
        return

    # 添加监控
    if args.add_monitor:
        try:
            parts = args.add_monitor.split(':')
            keyword = parts[0].strip()
            max_price = float(parts[1]) if len(parts) > 1 else None
            
            monitor.add_monitor(keyword, max_price=max_price)
        except Exception as e:
            print(f"❌ 添加监控失败: {e}")
            print("   格式示例: --add-monitor '无线蓝牙耳机:200'")
        return

    # 移除监控
    if args.remove_monitor:
        monitor.remove_monitor(args.remove_monitor)
        return

    # 启动监控模式
    if args.monitor:
        scheduler = TaskScheduler(monitor)
        
        # 如果指定了定时时间
        if args.schedule:
            scheduler.schedule_price_check(args.schedule)
            print(f"\n⏰ 已设置每日 {args.schedule} 自动检查")
            print("   按 Ctrl+C 停止调度器\n")
            scheduler.run()
        else:
            # 立即执行一次检查
            monitor.check_prices()


if __name__ == '__main__':
    main()
