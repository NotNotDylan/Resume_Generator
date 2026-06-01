"""Main application window."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from internal.generate_resume import GeneratorSettings
from internal.gui.panels.generate_panel import GeneratePanel
from internal.gui.panels.jobs_panel import JobsPanel
from internal.gui.panels.portfolio_panel import PortfolioPanel
from internal.gui.panels.settings_panel import SettingsPanel

_REPO_ROOT = Path(__file__).parent.parent.parent
_SETTINGS_FILE = _REPO_ROOT / "settings.json"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Resume Generator")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)

        # Build panels
        self._settings_panel = SettingsPanel(self)
        self._jobs_panel = JobsPanel(self)
        self._portfolio_panel = PortfolioPanel(self)
        self._generate_panel = GeneratePanel(self)

        # Tab bar
        tabs = QTabWidget()
        tabs.addTab(self._generate_panel, "⚡  Generate")
        tabs.addTab(self._jobs_panel, "📁  Jobs")
        tabs.addTab(self._portfolio_panel, "📄  Portfolio")
        tabs.addTab(self._settings_panel, "⚙  Settings")
        self.setCentralWidget(tabs)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel()
        self._status.addWidget(self._status_label)
        self._update_status()

    def build_settings(self) -> GeneratorSettings:
        """Build a GeneratorSettings from the current settings panel values."""
        data = self._settings_panel.to_dict()
        templates_root = _REPO_ROOT / "internal" / "templates"
        outputs_raw = data.get("output_dir", "outputs") or "outputs"
        outputs_root = Path(outputs_raw) if Path(outputs_raw).is_absolute() else _REPO_ROOT / outputs_raw

        photo_raw = data.get("photo_path", "")
        photo_file: Path | None = None
        if photo_raw:
            p = Path(photo_raw)
            if not p.is_absolute():
                p = _REPO_ROOT / p
            if p.exists():
                photo_file = p

        return GeneratorSettings(
            applications_root=_REPO_ROOT / "applications",
            outputs_root=outputs_root,
            templates_root=templates_root,
            selected_template_name=data.get("template", "modern.typ"),
            master_portfolio_file=_REPO_ROOT / "internal" / "data" / "master_portfolio.md",
            model_name=data.get("model_name", "gemini-2.5-pro"),
            research_model_name=data.get("research_model", "gemini-2.5-flash"),
            compile_pdf=bool(data.get("compile_pdf", True)),
            typst_binary_path=data.get("typst_binary", ""),
            enable_company_research=bool(data.get("use_google_search", False)),
            api_call_delay_seconds=float(data.get("api_delay", 4.0)),
            resume_title=data.get("resume_title", "Resume"),
            profile_photo_file=photo_file,
            profile_photo_rotation_degrees=int(data.get("photo_rotation", 0)),
        )

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _update_status(self) -> None:
        settings = self.build_settings()
        self._status_label.setText(f"Output → {settings.outputs_root}")
