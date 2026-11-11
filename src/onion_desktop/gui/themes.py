"""Light, dark, Dracula-inspired and system themes."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

_PALETTES: dict[str, dict[str, str]] = {
    "light": dict(window="#f5f5f7", base="#ffffff", alt="#eef0f3", text="#1d1d1f", button="#e9e9ed",
                  highlight="#2f6fde", htext="#ffffff", link="#1a5fd0", mid="#c8c8cc", disabled="#8e8e93",
                  accent="#2f6fde", sidebar="#e8e9ee"),
    "dark": dict(window="#202124", base="#17181a", alt="#26272b", text="#e8eaed", button="#2d2e31",
                 highlight="#4b8bf5", htext="#ffffff", link="#8ab4f8", mid="#3c4043", disabled="#80868b",
                 accent="#8ab4f8", sidebar="#191a1c"),
    "dracula": dict(window="#282a36", base="#21222c", alt="#2f3241", text="#f8f8f2", button="#343746",
                    highlight="#bd93f9", htext="#282a36", link="#8be9fd", mid="#44475a", disabled="#6272a4",
                    accent="#ff79c6", sidebar="#1e1f29"),
}

_SYSTEM_STYLE: str | None = None


def apply_theme(app: QApplication, name: str) -> None:
    global _SYSTEM_STYLE
    if _SYSTEM_STYLE is None:
        _SYSTEM_STYLE = app.style().name()
    if name not in _PALETTES:
        if _SYSTEM_STYLE:
            app.setStyle(QStyleFactory.create(_SYSTEM_STYLE) or app.style())
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet(_qss(None))
        return
    c = _PALETTES[name]
    app.setStyle(QStyleFactory.create("Fusion"))
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: c["window"], QPalette.ColorRole.WindowText: c["text"],
        QPalette.ColorRole.Base: c["base"], QPalette.ColorRole.AlternateBase: c["alt"],
        QPalette.ColorRole.Text: c["text"], QPalette.ColorRole.Button: c["button"],
        QPalette.ColorRole.ButtonText: c["text"], QPalette.ColorRole.Highlight: c["highlight"],
        QPalette.ColorRole.HighlightedText: c["htext"], QPalette.ColorRole.Link: c["link"],
        QPalette.ColorRole.ToolTipBase: c["alt"], QPalette.ColorRole.ToolTipText: c["text"],
        QPalette.ColorRole.PlaceholderText: c["disabled"], QPalette.ColorRole.Mid: c["mid"],
    }
    for role, col in roles.items():
        pal.setColor(role, QColor(col))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(c["disabled"]))
    app.setPalette(pal)
    app.setStyleSheet(_qss(c))


def _qss(c: dict[str, str] | None) -> str:
    sidebar = f"background:{c['sidebar']};" if c else ""
    accent = c["accent"] if c else "palette(highlight)"
    return f"""
    QListWidget#sidebar {{ {sidebar} border: none; padding: 6px; font-size: 11pt; }}
    QListWidget#sidebar::item {{ padding: 9px 10px; border-radius: 6px; }}
    QListWidget#sidebar::item:selected {{ background: {accent}; color: palette(highlighted-text); }}
    QLabel#pageTitle {{ font-size: 17pt; font-weight: 600; }}
    QLabel#subtle {{ color: palette(placeholder-text); }}
    QFrame#card {{ border: 1px solid palette(mid); border-radius: 8px; }}
    QLabel#warning {{ color: #d9822b; font-weight: 600; }}
    QLabel#danger {{ color: #e5484d; font-weight: 600; }}
    QLabel#ok {{ color: #30a46c; font-weight: 600; }}
    QPushButton#danger {{ color: #e5484d; font-weight: 600; }}
    QPushButton#primary {{ font-weight: 600; }}
    """
