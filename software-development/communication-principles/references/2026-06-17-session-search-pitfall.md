# 复盘：session_search FTS5 搜不到时的 fallback

**日期：** 2026-06-17
**触发场景：** Master让一夏"阅读这个session"找话题链，一夏反复调用 session_search 都说"搜不到"

## 根因

1. 长对话的中间段会被 **context compaction** 压缩成一条摘要消息（role=assistant）
2. **FTS5 不索引压缩后的摘要文本内容**——所以 session_search 按关键词搜不到
3. session_search 的 browse 模式也只索引了数据库的 FTS5 索引，搜不到 compaction 消息的内容

## 正确做法

当 session_search 在当前 session 搜不到结果时：

```bash
sqlite3 ~/.hermes/state.db "
SELECT id, role, length(content), substr(content,1,80)
FROM messages
WHERE session_id='当前session的ID'
AND content LIKE '%[CONTEXT COMPACTION]%'
ORDER BY id;
"
```

找到 compaction 消息后，直接用 sqlite3 读取其完整 content 字段：

```bash
sqlite3 ~/.hermes/state.db "
SELECT content FROM messages
WHERE id=<compaction消息的id>;
"
```

这样就能看到那条被压缩掉的完整摘要，里面包含 Active Task、Completed Actions、Key Decisions 等结构化信息。

## 如何知道当前 session ID

从 system prompt 通常看不到 session ID。可以直接查最新 session：

```bash
sqlite3 ~/.hermes/state.db "
SELECT DISTINCT session_id, COUNT(*) as msgs
FROM messages
GROUP BY session_id
ORDER BY MAX(id) DESC
LIMIT 5;
"
```

## 关键教训

- session_search 说"搜不到"不等于"不存在"——消息可能被 compaction 压掉了
- 被 compaction 压掉的消息内容**没有丢失**，只是不在 FTS5 索引里
- 直接查 state.db 是最终的 fallback 方案
- 读 compaction 摘要时，**不要只看第一行**——完整摘要可能有几千字符，包含整个被压掉段的来龙去脉
- Master给你的关键词（如"域名 oce ocy 读音"）是追溯线索，用这些关键词搜 compaction 摘要的内容来找连接点

## 进阶：session ID 陷阱 (2026-06-17 补充)

在 `20260615_184628_107636e6` 事件中发现：

1. **system prompt 里的 session ID 可能是错的**。当时显示的 `20260612_035008_d75343` 是 parent session，实际消息在 child `20260615_184628_107636e6`
2. 在 parent session ID 上做 `session_search(session_id=...)` 会报 `around_message_id not in session_id`——因为消息全在 child 里
3. **正确做法：** 不依赖 system prompt 的 session ID。先用 sqlite3 查最近消息确定真实 session：
   ```bash
   sqlite3 ~/.hermes/state.db "
   SELECT session_id, COUNT(*) FROM messages
   GROUP BY session_id ORDER BY MAX(id) DESC LIMIT 5;
   "
   ```
   然后用最新的那个 session_id 去查消息和 compaction 摘要
