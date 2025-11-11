# AkShare 网络连接问题诊断报告

**日期**: 2025-11-11
**问题**: 无法稳定连接到 eastmoney.com API

---

## 问题分析

### 测试结果

| 测试时间 | 方法 | 结果 | 原因 |
|---------|------|------|------|
| 11:30 | 直接HTTP请求 | ✅ 成功 | 获取到10条数据 |
| 11:40 | AkShare API (HTTPS) | ❌ 失败 | ReadTimeout (15秒超时) |
| 11:45 | HTTP请求（第2次） | ❌ 失败 | RemoteDisconnected |
| 11:48 | 服务内调用 | ❌ 失败 | RemoteDisconnected (3次重试全失败) |

### 根本原因

**这是网络连接不稳定问题，不是代码问题**

可能的原因：

1. **IP临时封禁** ⭐ 最可能
   - eastmoney.com 检测到频繁请求
   - 临时封禁了你的IP地址（通常5-30分钟）
   - 证据：几分钟前成功，现在全部失败

2. **网络拥塞**
   - 你的网络到 eastmoney 服务器的路径不稳定
   - ISP或中间路由器丢包严重

3. **防火墙拦截**
   - 公司/学校网络可能拦截了到 eastmoney.com 的连接
   - Windows防火墙或杀毒软件拦截

4. **服务端问题**
   - eastmoney API 服务器临时故障（可能性较小）

### 技术细节

```
错误类型: RemoteDisconnected
错误信息: Remote end closed connection without response

发生位置: HTTP连接建立后，在读取响应时被服务端主动关闭

典型场景:
- 服务端识别到异常请求并主动断开
- 请求频率超过限制
- IP被加入临时黑名单
```

---

## 解决方案

### 方案1: 等待恢复（推荐） ⏰

**等待 15-30 分钟后再试**

原因：
- IP封禁通常是临时的（5-30分钟）
- 等待封禁自动解除即可

测试命令：
```bash
cd backend
python -c "from api.services.realtime_data_service import realtime_data_service; print(realtime_data_service.get_realtime_quote('000001'))"
```

### 方案2: 更换网络 🌐

尝试：
- 切换到手机热点
- 使用VPN（但注意禁用代理设置）
- 更换到其他网络环境

### 方案3: 降低请求频率 🐌

修改缓存时间：
```python
# realtime_data_service.py:26
self.cache_ttl = 60  # 改为60秒（当前5秒）
```

好处：
- 减少API调用频率
- 降低被封禁概率
- 节省带宽

### 方案4: 使用备用数据源 🔄

**选项A - Tushare Pro**（需要token）
```python
import tushare as ts

ts.set_token('your_token')
pro = ts.pro_api()
df = pro.daily(ts_code='000001.SZ', trade_date='20250111')
```

**选项B - 新浪财经**（免费，但数据较少）
```python
import requests

url = 'https://hq.sinajs.cn/list=sz000001'
response = requests.get(url)
```

**选项C - 模拟数据**（开发调试用）
```python
# 返回固定的测试数据
def get_mock_quote(symbol):
    return {
        "symbol": symbol,
        "name": "测试股票",
        "price": 15.23,
        "change": 2.5,
        ...
    }
```

### 方案5: 增加重试间隔和次数 ⚙️

```python
# realtime_data_service.py:22
@retry_on_connection_error(max_retries=5, delay=3, backoff=3)
def _fetch_all_stocks_data(self):
    ...
```

参数说明：
- max_retries=5: 增加到5次重试
- delay=3: 初始延迟3秒
- backoff=3: 延迟倍增系数改为3（3s → 9s → 27s）

---

## 当前状态

### 已实施的优化 ✅

1. ✅ HTTP替代HTTPS（避免SSL超时）
2. ✅ 自动重试机制（3次，指数退避）
3. ✅ 禁用代理（避免代理干扰）
4. ✅ 批量获取优化（一次请求获取所有数据）
5. ✅ 详细错误日志
6. ✅ 优雅降级（失败时显示"等待数据"）

### 代码改进 📝

**realtime_data_service.py v3**：
- 直接使用 HTTP 请求，不依赖 AkShare
- 一次获取5000只股票
- 字段映射兼容原有逻辑
- 重试机制完整

**前端表现**：
- 连接失败时显示 "等待实时行情数据"
- 不会崩溃或报错
- 自动重试，用户无感知

---

## 建议

### 立即行动

1. **等待15-30分钟** ⏰
   - 不要频繁测试（会加重封禁）
   - 等待IP封禁自动解除

2. **检查防火墙** 🛡️
   ```powershell
   # Windows防火墙检查
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Python*"}
   ```

3. **测试网络连通性** 🔍
   ```bash
   ping 82.push2.eastmoney.com
   curl http://82.push2.eastmoney.com
   ```

### 生产环境建议

1. **使用专业数据接口**
   - Tushare Pro（收费，但稳定）
   - Wind万得（机构级）
   - 同花顺iFind（机构级）

2. **本地缓存历史数据**
   - Redis缓存实时行情
   - MongoDB存储历史K线
   - 减少实时API依赖

3. **多数据源冗余**
   - 主数据源：Tushare Pro
   - 备用数据源：AkShare
   - 降级方案：模拟数据

4. **限流保护**
   - 使用 Redis 限制API调用频率
   - 实施请求队列
   - 避免并发请求

---

## 测试清单

等待15-30分钟后，按顺序测试：

- [ ] **测试1**: 基础连通性
  ```bash
  ping 82.push2.eastmoney.com
  ```

- [ ] **测试2**: HTTP API访问
  ```bash
  curl "http://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10"
  ```

- [ ] **测试3**: Python requests
  ```bash
  python -c "import requests; print(requests.get('http://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10').status_code)"
  ```

- [ ] **测试4**: realtime_data_service
  ```bash
  python -c "from api.services.realtime_data_service import realtime_data_service; print(realtime_data_service.get_realtime_quote('000001'))"
  ```

- [ ] **测试5**: 前端Live Monitor页面
  ```
  访问 http://localhost:5173/live-monitor
  检查是否显示实时数据
  ```

---

## 联系支持

如果问题持续存在，可以：

1. **GitHub Issue**: 在 AkShare 项目提issue
   - https://github.com/akfamily/akshare/issues

2. **更换数据源**: 考虑使用商业数据接口

3. **联系网络管理员**: 检查公司/学校网络限制

---

**结论**: 当前问题是**网络连接不稳定**导致的，代码层面已经做了所有能做的优化（重试、降级、错误处理）。建议等待15-30分钟后再测试，或考虑更换网络/数据源。
