# 案例：Rate Limit 验证 — "别说如果，先查了再说"

## 场景

用户问 /position 实时更新从 10s 改为 1s 是否可行，问会不会超交易所 API 限额。

## 错误的做法（一夏最初犯的错）

```
一夏说：改成1秒技术上很简单，但如果通过代理中转，每次多一路延迟
        如果price_service用的是公开REST API...
```

**问题：** 用了"如果"推测，没有**实际去查代码**就下结论。

## 正确的做法

### 1. 先查 `price_service.get_current_price()` 的实现

```bash
# 找到方法定义
search_files("def get_current_price", path="bot_core/", file_glob="*.py")
```

### 2. 查到了什么（实际代码验证）

- 方法内部有**缓存机制**：`cache_expiry = 10` 秒（`trading.price_cache_ttl` 配置）
- 缓存命中的话**不走交易所 API**，直接返回缓存值
- 即使 `update_interval = 1`，每 10 秒内多次调同一个币种也只打 1 次 API

### 3. 查交易所回退链和限频

- 优先级：`bybit → binance → okx → gateio`
- ccxt 初始化带了 `enableRateLimit: True`
- 每个交易所的公开 ticker API 限频远高于 1 次/10 秒

### 4. 给出结论

**确定改成 1s 不会增加限额消耗**，因为缓存已确保实际 API 请求频率不变。

## 教训

- 任何时候被问到"如果……会不会超限/会不会有问题"，**不要回答"如果"**
- **应该**：查代码 → 看实际逻辑 → 看配置 → 看文档 → 给出确定的答案
- 查代码路径要确定：`price_service.get_current_price()` → 有缓存 → 找 `cache_expiry` 值 → 找 `_fetch_ticker_with_fallback` → 确认限频策略
- 用户特别反感推测性回答，必须用工具输出来支撑每一个结论
