# Typecho `permalink` Magic Property — Reproduction & Fix

## Error

```
Notice: Undefined index: permalink in /app/usr/themes/handsome/functions_mine.php on line 844
Notice: Undefined index: permalink in /app/usr/themes/handsome/functions_mine.php on line 813
```

## Root Cause

`permalink` is NOT a column in `typecho_contents` DB table. It is a **magic `__get()` property** computed by `Widget_Archive` at runtime — only available as `$widget->permalink` (object syntax), never present in arrays returned by `$db->fetchRow()` or `$widget->filter()`.

## Affected Functions (handsome theme)

### `theNext()` — "上一篇" (Previous Article)
Lines ~809–819 in `functions_mine.php`:
```php
$content = $db->fetchRow($sql);  // Returns raw DB row array
if ($content) {
    $content = $widget->filter($content);
    // $content is STILL an array, NO 'permalink' key
    $link = '<li class="previous"> ... href="' . $content['permalink'] . '" ...';
    //                          ^^^^^^^^^^^^^^^^^^^^ Undefined index
```

### `thePrev()` — "下一篇" (Next Article)
Lines ~840–850, identical pattern with different link text.

## Verified Fix

Apply after `$widget->filter($content)` in both functions:

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

**Why this works:**
- `Typecho_Widget::widget('Widget_Options')` — globally retrieves site options (unlike `$widget->options` which can be non-object)
- `Typecho_Router::url($content['type'], $content)` — uses the registered route for the content type ('post', 'page', etc.) to generate the correct URL path
- `Typecho_Common::url()` — combines the path with the site base URL

## Verification Steps

1. PHP syntax check: `php -l functions_mine.php`
2. HTTP 200 check: `curl -sS -o /dev/null -w "%{http_code}" https://yourdomain.com/archives/6/`
3. Notice check: `curl -sS https://yourdomain.com/archives/6/ 2>&1 | grep -i "Notice\|Undefined index\|Trying to get property" | grep -v "OPERATION_NOTICE\|SCREENSHOT_NOTICE\|MUSIC_NOTICE\|AUTO_PLAY"`
4. Run inside Docker: `docker exec typecho_container php -l /app/usr/themes/handsome/functions_mine.php`
