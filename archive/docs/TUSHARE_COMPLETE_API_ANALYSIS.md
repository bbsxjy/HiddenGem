# Tushare Pro完整API分析 - 5120积分权限（基于官方文档）

## 当前状态
- **积分数**: 5120
- **访问级别**: 可访问所有≤5000积分的API
- **调用频率**: 200次/分钟
- **特别优势**: 几乎解锁所有API，仅concept/concept_detail需要5000积分（刚好可用）

---

## ✅ 已集成的基础API

| API | 积分要求 | 状态 | 用途 |
|-----|---------|------|------|
| daily | 120 | ✅ 已集成 | 日线OHLCV - Technical Agent核心 |
| daily_basic | 2000 | ✅ 已集成 | PE/PB/换手率/市值 - Fundamental Agent |
| fina_indicator | 2000 | ✅ 已集成 | ROE/负债率 - Fundamental Agent |
| index_daily | 需积分 | ✅ 已集成 | 指数行情 - Market Agent |
| moneyflow_hsgt | 2000 | ✅ 已集成 | 沪深港通资金流向 - Market Agent |
| margin | 2000 | ✅ 已集成 | 融资融券汇总 - Market Agent |
| pledge_stat | 2000 | ✅ 已集成 | 股权质押统计 - Risk Agent |
| stk_limit | 2000 | ✅ 已集成 | 涨跌停价格 - Risk Agent |
| suspend_d | 120 | ✅ 已集成 | 停牌复牌 - Risk Agent |

---

## 🚀 第一优先级 - 立即集成（极高价值）

### 1. **moneyflow** - 个股资金流向 ⭐⭐⭐⭐⭐ (9/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日19:00
**数据起始**: 2010年

**核心字段**:
```python
buy_sm_amount: float    # 小单买入金额(万元)
buy_md_amount: float    # 中单买入金额(万元)
buy_lg_amount: float    # 大单买入金额(万元)
buy_elg_amount: float   # 特大单买入金额(万元)
net_mf_amount: float    # 净流入额(万元)
```

**应用场景** (Technical Agent + Sentiment Agent):
```python
# 主力资金流向分析
if buy_elg_amount > 5000万 and net_mf_amount > 0:
    信号 = "特大单净流入，主力吸筹"

if sell_lg_amount / total_amount > 60%:
    风险 = "大单持续流出，主力出货"

# 资金流向与价格背离
if net_mf_amount > 0 and pct_chg < 0:
    机会 = "资金流入但股价下跌，可能是洗盘"
```

**价值**:
- 识别主力行为（吸筹/出货/洗盘）
- 判断资金与价格背离
- 评估市场承接力

**集成难度**: 低
**推荐Agent**: Technical Agent, Sentiment Agent

---

### 2. **hk_hold** - 沪深股通持股明细 ⭐⭐⭐⭐⭐ (9/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 下个交易日08:00
**数据起始**: 2014年

**核心字段**:
```python
vol: float     # 持股量(股)
ratio: float   # 持股占比(%)
```

**应用场景** (Sentiment Agent + Risk Agent):
```python
# 北向资金持仓变化
if 持股占比变化 > 1% and 持股占比 > 5%:
    信号 = "外资大幅增持，看好长期价值"

if 持股占比变化 < -0.5% and 连续5日减持:
    风险 = "外资持续减持，警惕基本面变化"

# 外资持仓集中度
if 外资持股比例 > 10%:
    标签 = "外资重仓股"
```

**价值**:
- 追踪外资持仓变化（北向资金个股流向）
- 识别外资重仓股
- 与moneyflow_hsgt结合，分析外资整体+个股流向

**集成难度**: 低
**推荐Agent**: Sentiment Agent, Risk Agent

---

### 3. **stk_holdertrade** - 股东增减持 ⭐⭐⭐⭐⭐ (8/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日19:00
**数据起始**: 2007年

**核心字段**:
```python
holder_name: str      # 股东名称
holder_type: str      # 股东类型(董监高/实际控制人/高管)
in_de: str            # 增持/减持
change_vol: float     # 变动数量(万股)
change_ratio: float   # 占总股本比例
avg_price: float      # 平均价格
```

**应用场景** (Risk Agent + Sentiment Agent):
```python
# 重要股东减持预警
if holder_type == "实际控制人" and in_de == "减持" and change_ratio > 1%:
    风险 = "控股股东大幅减持，警惕"

# 高管增持信号
if holder_type == "高管" and in_de == "增持" and avg_price > 当前价格 * 1.1:
    信号 = "高管高位增持，对公司有信心"

# 减持压力评估
if 近3个月累计减持比例 > 5%:
    风险 = "减持压力大"
```

**价值**:
- 监控重要股东动向（实控人/高管增减持）
- 评估内部人信心
- 减持风险预警

**集成难度**: 低
**推荐Agent**: Risk Agent, Sentiment Agent

---

### 4. **top_list** - 龙虎榜每日明细 ⭐⭐⭐⭐⭐ (8/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日20:00
**数据起始**: 2005年

**核心字段**:
```python
l_buy: float        # 龙虎榜买入额
l_sell: float       # 龙虎榜卖出额
net_amount: float   # 龙虎榜净买入
net_rate: float     # 龙虎榜净买额占比
reason: str         # 上榜原因
```

**应用场景** (Sentiment Agent + Technical Agent):
```python
# 游资炒作识别
if reason == "连续三日涨幅偏离值达20%" and net_amount > 0:
    风险 = "游资炒作，警惕短期回调"

# 机构关注度
if "机构专用" in 买方席位 and net_amount > 5000万:
    信号 = "机构介入，中长期看好"

# 一日游风险
if 昨日上龙虎榜净买入 > 1亿 and 今日跌停:
    风险 = "游资一日游"
```

**价值**:
- 识别游资/机构炒作
- 追踪热点题材
- 警示短期风险

**集成难度**: 中
**推荐Agent**: Sentiment Agent, Technical Agent

---

### 5. **top_inst** - 龙虎榜机构明细 ⭐⭐⭐⭐ (7/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日20:00
**数据起始**: 2005年

**核心字段**:
```python
exalter: str       # 营业部名称
buy: float         # 买入额(万)
sell: float        # 卖出额(万)
net_buy: float     # 净买入额(万)
```

**应用场景** (Sentiment Agent):
```python
# 机构行为分析
if 机构席位数 >= 3 and 全部买入:
    信号 = "多家机构同时买入，看好度高"

if 机构席位数 >= 2 and 全部卖出:
    风险 = "机构集体离场"
```

**价值**:
- 详细的机构交易行为
- 配合top_list使用

**集成难度**: 低
**推荐Agent**: Sentiment Agent

---

## 📊 第二优先级 - 建议集成（高价值）

### 6. **block_trade** - 大宗交易 ⭐⭐⭐⭐ (7/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日21:00

**核心字段**:
```python
price: float     # 成交价
vol: float       # 成交量(万股)
amount: float    # 成交金额
buyer: str       # 买方营业部
seller: str      # 卖方营业部
```

**应用场景** (Risk Agent):
```python
# 折价率分析
折价率 = (price - close) / close * 100

if 折价率 < -10% and amount > 5000万:
    风险 = "大幅折价减持，股价承压"

if 折价率 > 5%:
    信号 = "溢价买入，可能有重组预期"
```

**价值**: 大股东减持风险、机构接盘意图
**集成难度**: 低
**推荐Agent**: Risk Agent

---

### 7. **stk_holdernumber** - 股东户数 ⭐⭐⭐⭐ (7/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 不定期（随季报/中报/年报）

**核心字段**:
```python
holder_num: int  # 股东人数
```

**应用场景** (Fundamental Agent + Risk Agent):
```python
# 筹码集中度
人均持股 = 总股本 / holder_num

if 股东户数环比减少 > 10%:
    信号 = "筹码集中，主力吸筹"

if 股东户数环比增加 > 20%:
    风险 = "筹码分散，可能派发"
```

**价值**: 筹码集中度、主力吸筹/派发
**集成难度**: 低
**推荐Agent**: Fundamental Agent, Risk Agent

---

### 8. **margin_detail** - 融资融券明细 ⭐⭐⭐⭐ (7/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日09:00

**核心字段**:
```python
rzye: float      # 融资余额(元)
rqye: float      # 融券余额(元)
rzmre: float     # 融资买入额(元)
```

**应用场景** (Market Agent + Sentiment Agent):
```python
# 个股杠杆情绪
if 融资余额 / 流通市值 > 10%:
    标签 = "高杠杆股"

if 融资余额环比增长 > 20% and 连续5日:
    信号 = "融资盘持续加杠杆，看多情绪强"

if 融资余额 / 流通市值 > 15% and 股价连续下跌:
    风险 = "高杠杆+下跌 = 强平风险"
```

**价值**: 个股杠杆情绪、强平风险
**集成难度**: 低
**推荐Agent**: Market Agent, Sentiment Agent

---

### 9. **share_float** - 限售股解禁 ⭐⭐⭐⭐ (7/10)

**积分要求**: 3000 ✅ 可用
**更新频率**: 定期更新

**核心字段**:
```python
float_date: str      # 解禁日期
float_share: float   # 解禁数量(万股)
float_ratio: float   # 解禁占总股本比例
holder_name: str     # 股东名称
```

**应用场景** (Risk Agent):
```python
# 大规模解禁预警
if float_ratio > 10% and 距离解禁日 < 30天:
    风险 = "大规模解禁临近，警惕抛压"

if float_ratio > 30%:
    风险 = "特大解禁，高风险"
```

**价值**: 解禁抛压预警
**集成难度**: 低
**推荐Agent**: Risk Agent

---

### 10. **pledge_detail** - 股权质押明细 ⭐⭐⭐ (6/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 每日21:00
**数据起始**: 2004年

**核心字段**:
```python
holder_name: str       # 股东名称
pledge_amount: float   # 质押数量(万股)
is_release: str        # 是否已解押
pledgor: str           # 质押方(券商/银行)
p_total_ratio: float   # 本次质押占总股本比例
```

**应用场景** (Risk Agent):
```python
# 重要股东质押风险
if holder_name == "实际控制人" and p_total_ratio > 5%:
    风险 = "控股股东大比例质押"

# 质押爆仓风险
if 质押价格 < 当前价格 * 0.6:
    风险 = "接近平仓线"
```

**价值**: 比pledge_stat更详细的质押明细
**集成难度**: 低
**推荐Agent**: Risk Agent

---

## 🎯 第三优先级 - 可选集成

### 11. **concept** + **concept_detail** - 概念题材 ⭐⭐⭐ (6/10)

**积分要求**: 5000 ⚠️ 刚好可用
**更新频率**: 定期更新

**应用场景** (Policy Agent + Sentiment Agent):
```python
# 热门题材识别
if "新能源" in 今日涨幅前5概念:
    关注 = concept_detail("新能源")

# 题材轮动
跟踪概念板块涨幅排名
```

**价值**: 题材炒作、板块轮动
**集成难度**: 低
**推荐Agent**: Policy Agent, Sentiment Agent

---

### 12. **repurchase** - 股票回购 ⭐⭐⭐ (5/10)

**积分要求**: 2000 ✅ 可用
**更新频率**: 定时更新
**数据起始**: 2011年

**核心字段**:
```python
proc: str           # 进度(董事会预案/股东大会通过/实施中)
vol: float          # 回购数量(万股)
amount: float       # 回购金额(万元)
high_limit: float   # 回购最高价
low_limit: float    # 回购最低价
```

**应用场景** (Sentiment Agent):
```python
if proc == "实施中" and amount > 1亿:
    信号 = "大额回购实施中，公司看好自身价值"
```

**价值**: 公司回购意图
**集成难度**: 低
**推荐Agent**: Sentiment Agent

---

### 13. **new_share** - IPO新股列表 ⭐⭐ (4/10)

**积分要求**: 120 ✅ 可用
**更新频率**: 每日19:00

**核心字段**:
```python
ipo_date: str      # 上网发行日期
issue_date: str    # 上市日期
price: float       # 发行价格
pe: float          # 市盈率
ballot: float      # 中签率
```

**应用场景** (Market Agent):
```python
# 新股上市情绪
if 本月新股数量 > 10:
    市场情绪 = "IPO密集，分流资金"
```

**价值**: 新股发行节奏监控
**集成难度**: 低
**推荐Agent**: Market Agent

---

## 💰 财务数据深化（可选）

当前已有fina_indicator（财务指标）提供了大部分关键指标。以下API提供更详细的财务报表：

| API | 积分 | 价值 | 建议 |
|-----|------|------|------|
| income (利润表) | 2000 | ⭐⭐ (4/10) | fina_indicator已够用 |
| balancesheet (资产负债表) | 2000 | ⭐⭐ (4/10) | fina_indicator已够用 |
| cashflow (现金流量表) | 2000 | ⭐⭐⭐ (5/10) | 可选，现金流详细分析 |
| forecast (业绩预告) | 2000 | ⭐⭐ (4/10) | 滞后性强 |
| express (业绩快报) | 2000 | ⭐⭐ (4/10) | 滞后性强 |
| dividend (分红送股) | 2000 | ⭐⭐ (3/10) | 对中低频交易影响小 |
| fina_mainbz (主营业务构成) | 2000 | ⭐⭐ (3/10) | 可选 |

**建议**: 当前fina_indicator已经足够，除非需要非常详细的财务分析。

---

## 📋 集成优先级总结

### 🚀 第一批 - 立即集成（必需）
**预期完成时间**: 本周
**预期价值提升**: 系统得分 60→80

1. **moneyflow** ⭐⭐⭐⭐⭐ (9/10) - 个股资金流向
   - Technical Agent: 主力行为识别
   - Sentiment Agent: 资金情绪分析

2. **hk_hold** ⭐⭐⭐⭐⭐ (9/10) - 北向资金个股持仓
   - Sentiment Agent: 外资动向
   - Risk Agent: 外资撤离预警

3. **stk_holdertrade** ⭐⭐⭐⭐⭐ (8/10) - 股东增减持
   - Risk Agent: 重要股东减持预警
   - Sentiment Agent: 内部人信心

4. **top_list** + **top_inst** ⭐⭐⭐⭐⭐ (8/10) - 龙虎榜
   - Sentiment Agent: 游资/机构行为
   - Technical Agent: 短期强势股

### 📅 第二批 - 推荐集成（重要）
**预期完成时间**: 下周
**预期价值提升**: 系统得分 80→85

5. **block_trade** ⭐⭐⭐⭐ (7/10) - 大宗交易
6. **stk_holdernumber** ⭐⭐⭐⭐ (7/10) - 股东户数
7. **margin_detail** ⭐⭐⭐⭐ (7/10) - 个股融资融券
8. **share_float** ⭐⭐⭐⭐ (7/10) - 限售股解禁
9. **pledge_detail** ⭐⭐⭐ (6/10) - 质押明细

### 🔮 第三批 - 可选集成（增强）
**预期完成时间**: 后续
**预期价值提升**: 系统得分 85→90

10. **concept** + **concept_detail** ⭐⭐⭐ (6/10) - 概念题材
11. **repurchase** ⭐⭐⭐ (5/10) - 股票回购
12. **new_share** ⭐⭐ (4/10) - IPO新股
13. **cashflow** ⭐⭐⭐ (5/10) - 现金流量表（可选）

---

## 🎯 Agent功能增强路线图

### Technical Agent增强
- ✅ 已有: RSI, MACD, MA, KDJ等技术指标
- 🆕 新增:
  - **moneyflow** - 大单/特大单资金流向
  - **top_list** - 龙虎榜强势股识别

### Market Agent增强
- ✅ 已有: 指数趋势, 北向资金汇总, 融资融券汇总
- 🆕 新增:
  - **margin_detail** - 个股融资融券情绪
  - **new_share** - IPO发行节奏

### Sentiment Agent增强 🆕 (当前空功能)
- ❌ 当前: 未实现
- 🆕 核心功能:
  - **hk_hold** - 外资持仓变化
  - **top_list** + **top_inst** - 龙虎榜游资/机构动向
  - **stk_holdertrade** - 股东增减持
  - **repurchase** - 公司回购
  - **moneyflow** - 资金流向情绪

### Risk Agent增强
- ✅ 已有: 质押统计, ST状态, 停牌, 波动率
- 🆕 新增:
  - **share_float** - 限售股解禁预警
  - **pledge_detail** - 详细质押明细
  - **block_trade** - 大宗交易折价减持
  - **stk_holdertrade** - 重要股东减持
  - **stk_holdernumber** - 筹码集中度

### Fundamental Agent增强
- ✅ 已有: PE/PB/ROE/负债率, 市值
- 🆕 新增:
  - **stk_holdernumber** - 筹码分析
  - **cashflow** (可选) - 现金流详细分析

### Policy Agent增强
- ❌ 当前: 未实现
- 🆕 核心功能:
  - **concept** + **concept_detail** - 政策受益股
  - LLM分析政策新闻（需要集成DeepSeek）

---

## 🚀 实施计划

### 阶段1: 激活Sentiment Agent (本周)
**目标**: 让Sentiment Agent从空功能变为核心Agent

**步骤**:
1. 集成 **moneyflow** API
2. 集成 **hk_hold** API
3. 集成 **stk_holdertrade** API
4. 集成 **top_list** + **top_inst** API
5. 创建Sentiment Agent分析逻辑

**预期效果**:
- 识别主力吸筹/出货
- 追踪外资动向
- 监控重要股东减持
- 识别游资炒作

**对系统的提升**:
- 从纯基本面+技术面，增加"市场情绪"维度
- 买卖建议质量: 60分 → 80分

---

### 阶段2: 强化Risk Agent (下周)
**目标**: 完善A股特有风险识别

**步骤**:
1. 集成 **share_float** API (解禁)
2. 集成 **pledge_detail** API (质押明细)
3. 集成 **block_trade** API (大宗交易)
4. 集成 **margin_detail** API (个股杠杆)
5. 更新Risk Agent增加新风险指标

**预期效果**:
- 解禁抛压预警
- 质押爆仓风险
- 大股东折价减持
- 高杠杆强平风险

**对系统的提升**:
- A股特有风险全覆盖
- 买卖建议质量: 80分 → 85分

---

### 阶段3: 增强其他Agent (后续)
**目标**: 系统全面完善

**步骤**:
1. 集成 **stk_holdernumber** 到Fundamental Agent
2. 集成 **concept** 到Policy Agent
3. 集成 **margin_detail** 到Market Agent
4. 集成DeepSeek LLM到Sentiment/Policy Agent

**预期效果**:
- 筹码集中度分析
- 题材炒作识别
- LLM驱动的情绪/政策分析

**对系统的提升**:
- 全面完善
- 买卖建议质量: 85分 → 90分+

---

## 💡 关键洞察

### 您的5120积分优势
1. ✅ 可访问所有2000-3000积分API（大部分高价值API）
2. ✅ 可访问5000积分的concept API（刚好满足）
3. ✅ 只有极少数5000+积分的特殊API无法访问（对系统影响小）

### 最高ROI的投资
**第一批4个API**（moneyflow/hk_hold/stk_holdertrade/top_list）集成后，系统将从：
- ❌ 缺失市场情绪维度
- ✅ 拥有完整的"技术+基本面+风险+情绪"四维分析

这是性价比最高的升级路径！

---

## 📊 数据使用成本估算

**已集成API调用频率**（每日）:
- 基础行情: ~100次/天
- 财务数据: ~20次/天
- 市场监控: ~10次/天

**新增API调用频率**（每日）:
- moneyflow: ~50次/天
- hk_hold: ~50次/天
- stk_holdertrade: ~10次/天
- top_list: ~5次/天

**总计**: ~245次/天，远低于200次/分钟的限制 ✅

---

## 下一步行动

**现在应该做什么？**

1. ✅ Fundamental Agent已完成
2. 🔄 选择路径:
   - **路径A**: 继续完成Risk Agent更新（使用已有pledge_stat等API）
   - **路径B**: 立即集成第一批高价值API（moneyflow等）激活Sentiment Agent

**我的建议**:
先完成**路径A（Risk Agent）**，确保所有基础Agent都用上真实数据，然后再**路径B**集成新API激活Sentiment Agent。

这样可以：
1. 稳扎稳打，确保基础功能完善
2. 然后通过新API实现质的飞跃

您想先做哪个？
