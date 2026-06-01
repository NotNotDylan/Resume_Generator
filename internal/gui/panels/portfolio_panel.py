"""Portfolio panel — view and edit the master portfolio Markdown file."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from internal.gui.app import MainWindow


class PortfolioPanel(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._portfolio_path: Path | None = None
        self._dirty = False
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.title_label = QLabel("master_portfolio.md")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #c4b5fd;")
        toolbar.addWidget(self.title_label)
        toolbar.addStretch()

        self.btn_reload = QPushButton("↺  Reload")
        self.btn_reload.setFixedHeight(32)
        self.btn_reload.clicked.connect(self._load_file)

        self.btn_save = QPushButton("💾  Save")
        self.btn_save.setFixedHeight(32)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_file)

        toolbar.addWidget(self.btn_reload)
        toolbar.addWidget(self.btn_save)
        root.addLayout(toolbar)

        # ── Splitter: editor | preview ────────────────────────────────────────
        splitter = QSplitter()

        self.editor = QPlainTextEdit()
        mono = QFont("Monospace", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(mono)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.textChanged.connect(self._on_text_changed)
        splitter.addWidget(self.editor)

        preview_container = QWidget()
        pv_layout = QVBoxLayout(preview_container)
        pv_layout.setContentsMargins(0, 0, 0, 0)
        pv_header = QLabel("Preview")
        pv_header.setStyleSheet("font-weight: 600; font-size: 12px; color: #a78bfa; padding: 2px 4px;")
        pv_layout.addWidget(pv_header)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        pv_layout.addWidget(self.preview)
        splitter.addWidget(preview_container)

        splitter.setSizes([600, 400])
        root.addWidget(splitter, 1)

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _resolve_path(self) -> Path:
        return Path(__file__).parent.parent.parent / "data" / "master_portfolio.md"

    def _load_file(self) -> None:
        self._portfolio_path = self._resolve_path()
        if self._portfolio_path.exists():
            text = self._portfolio_path.read_text(encoding="utf-8")
        else:
            text = "# Master Portfolio\n\n_Start adding your work history here._\n"
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self._dirty = False
        self._update_title()
        self._update_preview()

    def _save_file(self) -> None:
        if not self._portfolio_path:
            self._portfolio_path = self._resolve_path()
        self._portfolio_path.parent.mkdir(parents=True, exist_ok=True)
        self._portfolio_path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self._dirty = False
        self._update_title()

    def _on_text_changed(self) -> None:
        self._dirty = True
        self._update_title()
        self._preview_timer.start(600)  # debounce preview update

    def _update_title(self) -> None:
        indicator = " *" if self._dirty else ""
        self.title_label.setText(f"master_portfolio.md{indicator}")
        self.btn_save.setEnabled(self._dirty)

    def _update_preview(self) -> None:
        """Render markdown to HTML for preview pane."""
        try:
            import markdown
            html = markdown.markdown(
                self.editor.toPlainText(),
                extensions=["fenced_code", "tables"],
            )
        except ImportError:
            # Fallback: plain text wrapped in <pre>
            text = self.editor.toPlainText()
            escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html = f"<pre style='font-family:monospace;'>{escaped}</pre>"
        self.preview.setHtml(f"<body style='background:#1e1e2e;color:#cdd6f4;font-family:sans-serif;padding:8px'>{html}</body>")

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._portfolio_path is None:
            self._load_file()
