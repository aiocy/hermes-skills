# Typecho Handsome Theme: Undefined index `permalink` in theNext/thePrev

## Error

```
Notice: Undefined index: permalink in /app/usr/themes/handsome/functions_mine.php on line 844
Notice: Undefined index: permalink in /app/usr/themes/handsome/functions_mine.php on line 813
```

## Root Cause

`permalink` is NOT a database column in Typecho's `table.contents`. It's a magic `__get()` property computed by the `Widget_Archive` object from the routing system.

The `theNext()` and `thePrev()` functions do:

```php
$content = $db->fetchRow($sql);        // returns raw DB row array
$content = $widget->filter($content);  // returns processed array -- still no 'permalink' key
// $content['permalink'] ← UNDEFINED!
```

`$widget->filter()` processes fields like date formatting and excerpt generation, but does **NOT** inject `permalink` into the returned array.

## Fix

After `$widget->filter($content)`, check for `permalink` and build it via the router:

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

## Pitfall: `$widget->options` May Be Non-Object

First attempt used `$widget->options->index`, but `$widget->options` can be non-object depending on the calling context (e.g., when `theNext`/`thePrev` is called from a different widget type).

**Always use** `Typecho_Widget::widget('Widget_Options')` to get a reliable Options singleton.

## Verification

1. `docker exec <container> php -l <file>` — check PHP syntax
2. `curl -sS <blog-url> 2>&1 | grep -i "Notice"` — check no more notices appear
3. Check status code: `curl -sS -o /dev/null -w "%{http_code}" <blog-url>`

## File Location (Docker)

```bash
docker exec typecho_blog sed -n 'LINES' /app/usr/themes/handsome/functions_mine.php
docker cp typecho_blog:/app/usr/themes/handsome/functions_mine.php /tmp/
# edit locally, then:
docker cp /tmp/functions_mine.php typecho_blog:/app/usr/themes/handsome/functions_mine.php
```
