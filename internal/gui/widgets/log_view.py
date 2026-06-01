"""Log view widget — colour-coded, auto-scrolling, monospaced."""
from __future__ import annotations

from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit


LEVEL_COLOURS: dict[str, str] = {
    "info":    "#e2e8f0",
    "warning": "#f59e0b",
    "error":   "#ef4444",
    "success": "#22c55e",
}


class LogView(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("log_view")
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)

    def append_message(self, message: str, level: str = "info") -> None:
        colour = LEVEL_COLOURS.get(level, LEVEL_COLOURS["info"])
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.toPlainText():
            cursor.insertText(message, fmt)
        else:
            cursor.insertText("\n" + message, fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
