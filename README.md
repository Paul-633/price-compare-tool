<div align="center">

# 🛒 电商商品价格采集与对比工具

[![GitHub stars](https://img.shields.io/github/stars/Paul-633/price-compare-tool?style=social)](https://github.com/Paul-633/price-compare-tool/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Paul-633/price-compare-tool?style=social)](https://github.com/Paul-633/price-compare-tool/network)
[![GitHub license](https://img.shields.io/github/license/Paul-633/price-compare-tool)](https://github.com/Paul-633/price-compare-tool/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Paul-633/price-compare-tool/pulls)

**🚀 一键采集京东/淘宝/拼多多商品价格，智能分析性价比，自动监控降价！**

[在线演示](https://paul-633.github.io/price-compare-tool/demo.html) • [使用文档](#-快速开始) • [问题反馈](https://github.com/Paul-633/price-compare-tool/issues)

</div>

---

## 📖 项目简介

这是一个功能完整的电商价格分析系统，帮助你轻松实现多平台商品数据采集、智能分析和价格监控。

### 🎯 解决什么问题？

- ❌ **手动比价费时费力？** → ✅ 自动采集多平台价格
- ❌ **不知道哪个最划算？** → ✅ 智能性价比评分系统
- ❌ **错过降价时机？** → ✅ 价格监控+降价提醒
- ❌ **需要了解价格趋势？** → ✅ 可视化价格趋势图

### 💡 技术亮点

- 🕷️ **真实爬虫架构**：代理池、Cookie池、请求头轮换
- 🛡️ **反爬机制**：自动检查 robots.txt，智能延时控制
- 💾 **数据持久化**：支持 SQLite 和 MySQL
- ⏰ **定时任务**：自动化价格监控
- 📊 **可视化报告**：HTML 报告 + Chart.js 图表

## ✨ 功能特性

### 核心功能
- **多平台采集**：支持京东、淘宝、拼多多等主流电商平台
- **智能采集**：真实爬虫模式，支持代理池、Cookie池、请求头轮换
- **数据处理**：自动清洗、去重、排序
- **性价比分析**：基于价格、销量、店铺评分的综合评分算法
- **数据可视化**：生成HTML报告和价格趋势图
- **数据持久化**：支持SQLite和MySQL数据库

### 高级功能
- **价格监控**：设置目标价格，自动监控降价商品
- **定时任务**：支持定时自动采集和价格检查
- **通知提醒**：支持控制台、邮件等多种通知方式
- **历史数据**：自动记录价格变化历史

## 📦 安装

### 1. 克隆项目
```bash
git clone <repository-url>
cd dsdb
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置文件（可选）

#### 代理配置
复制代理配置示例文件并添加你的代理：
```bash
cp proxies.example.txt proxies.txt
```
编辑 `proxies.txt`，每行一个代理：
```
http://127.0.0.1:7890
https://proxy.example.com:8080
```

#### Cookie配置
复制Cookie配置示例文件并添加你的Cookie：
```bash
cp cookies.example.json cookies.json
```
编辑 `cookies.json`，添加各平台的Cookie：
```json
{
  "jd": {
    "cookie": "你的京东Cookie"
  },
  "taobao": {
    "cookie": "你的淘宝Cookie"
  },
  "pdd": {
    "cookie": "你的拼多多Cookie"
  }
}
```

#### 主配置文件
复制配置示例文件：
```bash
cp config.example.json config.json
```
根据需要修改数据库、爬虫、监控等配置。

## 🚀 使用方法

### 基础使用

#### 1. 简单采集（模拟数据）
```bash
python price_compare.py 无线蓝牙耳机
```

#### 2. 使用真实爬虫
```bash
python price_compare.py 智能手机 --real-scraper
```

#### 3. 指定数据库
```bash
# SQLite
python price_compare.py 笔记本电脑 --db-type sqlite --db-path products.db

# MySQL
python price_compare.py 笔记本电脑 \
  --db-type mysql \
  --db-host localhost \
  --db-port 3306 \
  --db-user root \
  --db-password yourpassword \
  --db-name price_compare
```

#### 4. 不生成报告
```bash
# 不生成HTML报告
python price_compare.py 无线蓝牙耳机 --no-html

# 不生成价格趋势图
python price_compare.py 无线蓝牙耳机 --no-chart

# 不保存到数据库
python price_compare.py 无线蓝牙耳机 --no-db
```

### 价格监控

#### 1. 添加监控商品
```bash
# 添加监控，设置目标价格
python price_compare.py --add-monitor "无线蓝牙耳机:200"

# 添加监控，不设置目标价格
python price_compare.py --add-monitor "智能手机"
```

#### 2. 查看监控列表
```bash
python price_compare.py --list-monitors
```

#### 3. 移除监控商品
```bash
python price_compare.py --remove-monitor "无线蓝牙耳机"
```

#### 4. 立即执行价格检查
```bash
python price_compare.py --monitor
```

#### 5. 设置定时任务
```bash
# 每天早上9点自动检查
python price_compare.py --monitor --schedule 09:00

# 每天下午6点自动检查
python price_compare.py --monitor --schedule 18:00
```

### 演示网页

打开 `demo.html` 文件即可在浏览器中运行演示：
```bash
# 直接用浏览器打开
open demo.html  # macOS
start demo.html  # Windows
xdg-open demo.html  # Linux
```

演示网页支持：
- 输入关键词搜索
- 点击示例关键词快速体验
- 查看统计概览、性价比推荐、价格趋势图、完整商品列表

## 📊 输出说明

### 终端输出
- 商品列表表格
- 性价比推荐TOP 3
- 采集进度和统计信息

### 文件输出
- `{关键词}_data.json`：采集的原始数据
- `report.html`：HTML格式的价格对比报告
- `price_chart.html`：价格趋势图
- `products.db`：SQLite数据库（如果使用）

### 数据库表结构

#### products 表
存储商品信息：
- id: 主键
- name: 商品名称
- price: 价格
- sales: 销量
- shop_name: 店铺名称
- shop_score: 店铺评分
- url: 商品链接
- platform: 平台
- image_url: 图片链接
- category: 分类
- collected_at: 采集时间

#### price_history 表
存储价格历史：
- id: 主键
- product_id: 商品ID（外键）
- price: 价格
- recorded_at: 记录时间

#### search_logs 表
存储搜索日志：
- id: 主键
- keyword: 搜索关键词
- result_count: 结果数量
- searched_at: 搜索时间

## 🔧 配置说明

### config.json 配置项

#### database 数据库配置
```json
{
  "database": {
    "type": "sqlite",  // 或 "mysql"
    "sqlite": {
      "path": "products.db"
    },
    "mysql": {
      "host": "localhost",
      "port": 3306,
      "user": "root",
      "password": "",
      "database": "price_compare",
      "charset": "utf8mb4"
    }
  }
}
```

#### scraper 爬虫配置
```json
{
  "scraper": {
    "use_proxy": true,        // 是否使用代理
    "use_cookie": true,       // 是否使用Cookie
    "request_delay": [1, 3],  // 请求延迟范围（秒）
    "max_retries": 3,         // 最大重试次数
    "timeout": 10             // 请求超时时间（秒）
  }
}
```

#### monitor 监控配置
```json
{
  "monitor": {
    "check_interval": 3600,      // 检查间隔（秒）
    "notify_enabled": true,      // 是否启用通知
    "notify_methods": ["console"], // 通知方式：console, email
    "email": {
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "username": "",
      "password": "",
      "recipients": []
    }
  }
}
```

## ⚠️ 注意事项

### 法律合规
1. **遵守robots.txt**：程序会自动检查各平台的robots.txt规则
2. **合理采集频率**：避免过于频繁的请求，建议设置合理的延迟
3. **尊重版权**：采集的数据仅供个人学习研究使用
4. **遵守服务条款**：使用前请阅读并遵守各电商平台的服务条款

### 反爬虫
1. **代理池**：建议使用高质量代理，避免IP被封禁
2. **Cookie池**：使用真实Cookie可以提高采集成功率
3. **请求延迟**：程序内置了随机延迟，避免触发反爬机制
4. **请求头轮换**：自动轮换User-Agent，模拟真实浏览器

### 性能优化
1. **数据库索引**：已为常用查询字段创建索引
2. **批量操作**：使用批量插入提高数据库写入性能
3. **缓存机制**：robots.txt规则会缓存，避免重复请求

## 🐛 故障排除

### 常见问题

#### 1. 模块导入失败
```bash
# 确保已安装所有依赖
pip install -r requirements.txt
```

#### 2. 数据库连接失败
- 检查MySQL服务是否运行
- 检查数据库用户名和密码是否正确
- 确保数据库已创建

#### 3. 爬虫采集失败
- 检查代理是否可用
- 检查Cookie是否有效
- 查看控制台错误信息

#### 4. 定时任务不执行
- 确保程序持续运行（不要关闭终端）
- 检查系统时间是否正确
- 查看调度器日志

## 📝 开发计划

- [ ] 支持更多电商平台（苏宁、国美等）
- [ ] 添加更多通知方式（微信、钉钉、Telegram）
- [ ] 实现Web管理界面
- [ ] 添加价格预测功能
- [ ] 支持商品对比功能
- [ ] 添加数据导出功能（Excel、CSV）

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请通过Issue反馈。
