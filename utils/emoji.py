def ce(emoji_id: str, fallback: str) -> str:
    """
    Возвращает HTML-тег для custom emoji.
    Если emoji_id пустой — возвращает обычный эмодзи.
    """
    if not emoji_id:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


# Словарь с ID (заполните своими)
EMOJI = {
    "support": ce("5368324170671202286", "🆘"),
    "fire":    ce("5420315771991497307", "🔥"),
    "star":    ce("5438496463044752972", "⭐"),
    "check":   ce("", "✅"),          # без custom — просто ✅
}