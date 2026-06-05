---
name: typecho
description: "Debug and maintain Typecho CMS — theme quirks, magic properties, routing, widget system, common PHP Notice pitfalls."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [typecho, cms, php, debugging, theme]
    related_skills: [systematic-debugging, ocr-and-documents]
---

# Typecho CMS Debugging & Maintenance

## Overview

Typecho is a PHP blogging platform. Its theme and widget system has several gotchas that differ from typical PHP applications. This skill covers common pitfalls found when debugging Typecho theme issues, especially in the popular `handsome` theme.

## Key Architecture Insights

### `permalink` is a Magic Property, NOT a Database Column

**This is the #1 source of `Undefined index: permalink` PHP Notices in Typecho themes.**

- The `typecho_contents` database table has **no `permalink` column**
- `permalink` is a **magic `__get()` property** on `Widget_Archive` — only accessible as `$widget->permalink` (object syntax), never as `$content['permalink']` (array syntax)
- When you fetch a row via `$db->fetchRow($sql)`, then process it through `$widget->filter()`, the returned array still won't have `permalink`

**Correct ways to construct a permalink from a database row:**

```php
// Method 1 (reliable, works in any context — use this for fallbacks):
$options = Typecho_Widget::widget('Widget_Options');
$permalink = Typecho_Common::url(
    Typecho_Router::url($content['type'], $content),
    $options->index
);

// Method 2 (from the current widget object):
$permalink = $widget->permalink;  // Magic property on the current article widget
```

### `$widget->options` is NOT Always Available

- In theme functions like `theNext()` / `thePrev()`, `$widget` is the current `Widget_Archive` — but `$widget->options` may be a **non-object** depending on the calling context
- **Always use** `Typecho_Widget::widget('Widget_Options')` as a fallback when you need site options outside of a full controller context

### Typecho Router

- Routes are registered by content type (e.g., `'post'`, `'page'`, `'attachment'`)
- `Typecho_Router::url($routeName, $rowData)` generates the path component
- `Typecho_Router::get($routeName)` returns the route regex pattern (useful for checking existence)
- Combine with `Typecho_Common::url()` + options index for a full URL

## Common Theme Pitfalls

### 1. `theNext()` / `thePrev()` — "上一篇/下一篇" Navigation (handsome theme)

**Symptoms:**
- `Notice: Undefined index: permalink` at lines ~813 and ~844
- Navigation still renders, but PHP logs fill with notices

**Root cause:**
The SQL query fetches the next/prev article row via `$db->fetchRow()`, then `$widget->filter()` processes it — but the result array lacks `permalink` because it's a magic property, not a DB column.

**Fix:**
After `$widget->filter($content)`, check and supply the permalink:

```php
$content = $widget->filter($content);
if (!isset($content['permalink'])) {
    $options = Typecho_Widget::widget('Widget_Options');
    $content['permalink'] = Typecho_Common::url(
        Typecho_Router::url($content['type'], $content),
        $options->index
    );
}
```

### 2. URL Routing & Apache Rewrite

- For clean URLs (e.g., `/archives/6/`), Apache needs `mod_rewrite` enabled
- Place rewrite rules in the `<VirtualHost>` — use absolute path `/index.php` to avoid 400 errors
- Correct rule:
  ```apache
  RewriteEngine On
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule ^(.*)$ /index.php [L,E=PATH_INFO:$1]
  ```

## Debugging Workflow for Typecho Theme Issues

1. **Read the error message carefully** — Note the exact line number, file path, and notice type
2. **Read the source code** at the reported line and surrounding context
3. **Identify whether the offending key is a DB column or a magic property**
   - DB columns: `cid`, `title`, `slug`, `created`, `type`, `status`, `password`, `text`, etc.
   - Magic properties: `permalink`, `date`, `category`, `tags`, etc.
4. **Trace the data flow** — How does the value get set? Is it from `$db->fetchRow()` or from a widget?
5. **Present findings to the user** — Show the exact code, explain the root cause
6. **Fix only after user confirmation** — Production infrastructure changes need user sign-off

### 3. Markdown 表格中的管道符 `|` 被错误拆分

**症状：**
- Markdown 表格中，包含 `|` 的行被拆成多列
- 例如 `| 查看网卡 | \`lspci | grep -i net\` |` 渲染成 3 列而非 2 列
- 输出的 HTML 变成 `<code>lspci</td><td>grep -i net</code>`

**根因：**
Typecho 的 Markdown 解析器在处理表格时，**先按 `|` 拆分列，再处理行内格式**。所以：
- 反引号 `` ` `` 内的 `|` 不能保护管道符
- HTML `<code>` 标签内的 `|` 也不能保护
- Markdown 转义 `\|` 同样无效

**终极解决方案（实测有效）：**
使用 **HTML 原生 `<table>`** + **HTML 实体 `&#x7C;`** 代替管道符：

```php
// 在数据库内容中替换
$old_markdown_table = "| 目的 | 命令 |
|------|------|
| 查看网卡PCI信息 | \`lspci | grep -i net\` |";

$new_html_table = <<<HTML
<table>
<thead><tr><th>目的</th><th>命令</th></tr></thead>
<tbody>
<tr><td>查看网卡PCI信息</td><td><code>lspci &#x7C; grep -i net</code></td></tr>
</tbody>
</table>
HTML;
```

**原理：**
- `&#x7C;` 在 Markdown 解析阶段不被识别为 `|` → 表格不会被拆列
- 浏览器渲染时将 `&#x7C;` 显示为 `|` → 用户看到正常管道符
- 复制粘贴时浏览器复制渲染后的 `|` → 命令可用

**PHP 更新数据库示例：**
```php
$db = new PDO("mysql:host=mariadb;dbname=typecho;charset=utf8", "user", "pass");
$res = $db->query("SELECT text FROM typecho_contents WHERE cid=XXX");
$row = $res->fetch(PDO::FETCH_ASSOC);
$text = str_replace($old_table, $new_table, $row['text']);
$stmt = $db->prepare("UPDATE typecho_contents SET text=? WHERE cid=XXX");
$stmt->execute([$text]);
```

## Related Skills

- `systematic-debugging` — General 4-phase debugging process
- `ocr-and-documents` — For extracting text from Typecho documentation PDFs
