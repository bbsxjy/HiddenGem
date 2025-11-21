# 新闻API配置指南

本文档详细说明如何获取和配置各个新闻API的密钥。

## 🎯 推荐配置方案

根据您的使用场景，推荐以下配置：

| 场景 | 推荐API | 原因 |
|------|---------|------|
| 仅分析A股 | **AKShare** | 免费、无需API key、中文新闻 |
| A股 + 美股 | AKShare + FinnHub | AKShare免费，FinnHub美股专业 |
| 全球市场 | AKShare + FinnHub + Alpha Vantage | 全面覆盖 |
| 企业级应用 | 全部配置 | 多数据源冗余 |

---

## 1️⃣ FinnHub API (美股新闻)

### 适用场景
- ✅ 美股实时新闻
- ✅ 公司财报、分析师评级
- ✅ 市场情绪数据

### 获取步骤

**1. 注册账号**
```
访问: https://finnhub.io/
点击: "Get free API key"
```

**2. 登录方式**
- 邮箱注册
- Google账号登录（推荐，快速）
- GitHub账号登录

**3. 获取API Key**
- 登录后自动跳转到 Dashboard
- 找到 "API Key" 字段
- 点击复制按钮
- 示例格式: `c123abc456def789ghijklmn`

**4. 配置到 .env**
```bash
# 在 .env 文件中修改
FINNHUB_API_KEY=你的真实API密钥
```

**5. 免费额额度**
| 限制类型 | 免费版 | 付费版 ($49.99/月) |
|---------|-------|-------------------|
| API调用/月 | 60次 | 无限 |
| API调用/分钟 | 60次 | 300次 |
| 历史数据 | 1年 | 30年 |

**6. 验证配置**
```python
import os
from dotenv import load_dotenv
load_dotenv()

finnhub_key = os.getenv('FINNHUB_API_KEY')
print(f"FinnHub API Key: {finnhub_key[:10]}... (已配置)")
```

---

## 2️⃣ Alpha Vantage API (全球新闻)

### 适用场景
- ✅ 新闻情绪分析
- ✅ 全球股票数据
- ✅ 外汇、加密货币

### 获取步骤

**1. 访问注册页面**
```
https://www.alphavantage.co/support/#api-key
```

**2. 填写注册信息**
- First Name: 名字
- Last Name: 姓氏
- Email Address: 邮箱
- Organization: 组织（可填"Personal"）
- 勾选: "I agree to the Terms of Service"

**3. 获取API Key**
- 提交后立即显示API Key
- ⚠️ **重要**: 只显示一次，请立即保存
- 示例格式: `ABC123XYZ789`

**4. 配置到 .env**

需要在 `.env` 文件中添加：
```bash
# Alpha Vantage API密钥（新闻情绪分析）
ALPHA_VANTAGE_API_KEY=你的真实API密钥
```

**5. 免费额度**
| 限制类型 | 免费版 | Premium ($49.99/月) |
|---------|-------|---------------------|
| API调用/天 | 25次 | 75次 |
| API调用/分钟 | 5次 | 75次 |
| 并发请求 | 1个 | 无限 |

**6. 验证配置**
```bash
curl "https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL&apikey=你的API密钥"
```

---

## 3️⃣ NewsAPI (全球新闻聚合)

### 适用场景
- ✅ 全球7万+新闻源
- ✅ 多语言支持
- ✅ 按关键词搜索

### 获取步骤

**1. 访问注册页面**
```
https://newsapi.org/register
```

**2. 填写注册信息**
- First Name: 名字
- Email: 邮箱
- Password: 密码（至少8位）
- Select a plan: "Developer" (免费)

**3. 获取API Key**
- 注册后自动跳转到 Account 页面
- 找到 "API key" 字段
- 点击复制
- 示例格式: `abc123def456ghi789`

**4. 配置到 .env**

需要在 `.env` 文件中添加：
```bash
# NewsAPI 密钥（全球新闻）
NEWSAPI_KEY=你的真实API密钥
```

**5. 免费额度**
| 限制类型 | Developer (免费) | Business ($449/月) |
|---------|-----------------|-------------------|
| API调用/天 | 100次 | 250,000次/月 |
| 历史数据 | 30天 | 无限 |
| 使用环境 | 仅开发 | 生产环境 |

⚠️ **重要**: 免费版仅供开发使用，生产环境需要付费版。

**6. 验证配置**
```bash
curl "https://newsapi.org/v2/everything?q=AAPL&apiKey=你的API密钥"
```

---

## 4️⃣ AKShare (中文财经新闻 - 推荐)

### 适用场景
- ✅ 东方财富个股新闻
- ✅ 雪球股票情绪
- ✅ 千股千评

### 优势
- ✅ **完全免费**
- ✅ **无需API key**
- ✅ **已集成到项目**
- ✅ 中文财经数据

### 使用方法

**无需配置，直接使用**：
```python
from tradingagents.dataflows.akshare_utils import (
    get_stock_news_em,           # 东方财富新闻
    get_stock_comments_em,        # 千股千评
    get_xueqiu_hot_stock_info,   # 雪球热度
    get_xueqiu_stock_sentiment   # 雪球情绪
)

# 获取东方财富新闻
news = get_stock_news_em('600036', max_news=10)
print(news)
```

### AKShare可用接口
| 接口 | 说明 | 限制 |
|------|------|------|
| `stock_news_em()` | 东方财富个股新闻 | 无 |
| `stock_comment_em()` | 千股千评 | 无 |
| `stock_hot_rank_em()` | 雪球热股排行 | 无 |
| `stock_tweets_rank_em()` | 雪球讨论排行 | 无 |

---

## 5️⃣ 财联社RSS (中文财经快讯)

### 当前状态
```
⚠️ RSS源未返回有效内容
```

### 问题分析
1. 财联社可能限制了免费RSS访问
2. 需要登录或会员权限
3. RSS格式可能变更

### 解决方案

**方案A: 使用财联社官方API**（付费）
- 访问: https://www.cls.cn/
- 联系客服申请接口权限
- 价格: 需咨询（通常面向机构）

**方案B: 使用AKShare替代**（推荐）
```python
# 使用东方财富新闻替代财联社
from tradingagents.dataflows.akshare_utils import get_stock_news_em
news = get_stock_news_em('600036', max_news=10)
```

**方案C: 手动订阅财联社**
- 下载财联社APP
- 购买会员（电报功能）
- 无API接口，仅供阅读

---

## 🔧 完整配置示例

### 编辑 `.env` 文件

```bash
# ===== 新闻API配置 =====

# 📊 FinnHub API 密钥 (美股新闻)
# 获取地址: https://finnhub.io/
FINNHUB_API_KEY=你的FinnHub API密钥

# 📈 Alpha Vantage API密钥 (新闻情绪分析)
# 获取地址: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=你的Alpha Vantage API密钥

# 📰 NewsAPI 密钥 (全球新闻)
# 获取地址: https://newsapi.org/register
NEWSAPI_KEY=你的NewsAPI密钥

# ===== 已有配置 =====

# 🇨🇳 Tushare API Token (A股数据 - 已配置)
TUSHARE_TOKEN=672ef55b7846478d7e294b5090b948c6780a2653617816fb5539cb21

# 💡 提示：AKShare无需配置，已自动集成
```

---

## ✅ 验证配置

### 运行测试脚本

创建测试脚本 `scripts/test_news_apis.py`:

```python
#!/usr/bin/env python3
"""测试所有新闻API配置"""

import os
from dotenv import load_dotenv
load_dotenv()

def test_finnhub():
    key = os.getenv('FINNHUB_API_KEY')
    if key and key != 'your_finnhub_api_key_here':
        print("✅ FinnHub API Key: 已配置")
        return True
    else:
        print("❌ FinnHub API Key: 未配置")
        return False

def test_alpha_vantage():
    key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if key:
        print("✅ Alpha Vantage API Key: 已配置")
        return True
    else:
        print("❌ Alpha Vantage API Key: 未配置")
        return False

def test_newsapi():
    key = os.getenv('NEWSAPI_KEY')
    if key:
        print("✅ NewsAPI Key: 已配置")
        return True
    else:
        print("❌ NewsAPI Key: 未配置")
        return False

def test_akshare():
    try:
        import akshare as ak
        print("✅ AKShare: 已安装")
        return True
    except ImportError:
        print("❌ AKShare: 未安装")
        return False

if __name__ == "__main__":
    print("="*60)
    print("新闻API配置检查")
    print("="*60)

    results = {
        "FinnHub": test_finnhub(),
        "Alpha Vantage": test_alpha_vantage(),
        "NewsAPI": test_newsapi(),
        "AKShare": test_akshare()
    }

    print("\n" + "="*60)
    print(f"配置完成度: {sum(results.values())}/4")
    print("="*60)

    if sum(results.values()) == 4:
        print("\n🎉 所有API都已配置！")
    elif results['AKShare']:
        print("\n💡 AKShare已可用，建议配置其他API以获得更全面的新闻覆盖")
    else:
        print("\n⚠️ 请按照文档配置API密钥")
```

运行测试：
```bash
python scripts/test_news_apis.py
```

---

## 📊 API对比总结

| API | 成本 | 配置难度 | 覆盖范围 | 推荐场景 |
|-----|------|---------|---------|---------|
| **AKShare** | 免费 | ⭐ 无需配置 | 中文市场 | A股分析（强烈推荐） |
| **FinnHub** | 免费60次/月 | ⭐⭐ 简单注册 | 美股 | 美股分析 |
| **Alpha Vantage** | 免费25次/天 | ⭐⭐ 简单注册 | 全球 | 情绪分析 |
| **NewsAPI** | 免费100次/天 | ⭐⭐ 简单注册 | 全球 | 开发测试 |
| **财联社** | 付费 | ⭐⭐⭐⭐⭐ 需商务洽谈 | 中国市场 | 机构用户 |

---

## 💡 最佳实践

### 1. 仅分析A股（推荐配置）
```bash
# 只需配置 Tushare（已有）
TUSHARE_TOKEN=你的token

# AKShare自动工作，无需配置
```

### 2. A股 + 美股
```bash
# Tushare用于A股价格数据
TUSHARE_TOKEN=你的token

# FinnHub用于美股新闻
FINNHUB_API_KEY=你的FinnHub密钥

# AKShare用于中文新闻（无需配置）
```

### 3. 全球市场
```bash
# 配置所有API
TUSHARE_TOKEN=你的token
FINNHUB_API_KEY=你的FinnHub密钥
ALPHA_VANTAGE_API_KEY=你的Alpha Vantage密钥
NEWSAPI_KEY=你的NewsAPI密钥
```

---

## 🚀 下一步

1. **选择合适的API** - 根据分析需求选择
2. **注册获取密钥** - 按照上述步骤操作
3. **配置.env文件** - 填入真实API密钥
4. **运行验证脚本** - 确认配置成功
5. **开始使用** - 运行分析系统

---

**文档版本**: v1.0
**最后更新**: 2025-11-21
**维护者**: Claude Code
