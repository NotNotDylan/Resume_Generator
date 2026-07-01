"""Settings panel — edit and persist all non-secret configuration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from internal.gui.app import MainWindow

SETTINGS_FILE = Path(__file__).parent.parent.parent.parent / "settings.json"


class SettingsPanel(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._save)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── API Settings ──────────────────────────────────────────────────────
        api_group = QGroupBox("API Settings")
        api_form = QFormLayout(api_group)
        api_form.setSpacing(8)

        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("gemini-2.5-pro")
        api_form.addRow("Generation Model:", self.model_name)

        self.research_model = QLineEdit()
        self.research_model.setPlaceholderText("gemini-2.5-flash")
        api_form.addRow("Research Model:", self.research_model)

        self.api_delay = QDoubleSpinBox()
        self.api_delay.setRange(0.0, 60.0)
        self.api_delay.setSingleStep(0.5)
        self.api_delay.setSuffix(" s")
        self.api_delay.setDecimals(1)
        api_form.addRow("Delay Between Calls:", self.api_delay)

        self.use_google_search = QCheckBox("Enable Google Search for company research")
        api_form.addRow("", self.use_google_search)

        layout.addWidget(api_group)

        # ── Generation Settings ───────────────────────────────────────────────
        gen_group = QGroupBox("Generation Settings")
        gen_form = QFormLayout(gen_group)
        gen_form.setSpacing(8)

        self.template_combo = QComboBox()
        gen_form.addRow("Typst Template:", self.template_combo)
        self._populate_templates()

        self.resume_title = QLineEdit()
        self.resume_title.setPlaceholderText("Resume")
        gen_form.addRow("Output File Name:", self.resume_title)

        self.force_regen_default = QCheckBox("Force regenerate by default (ignore AI cache)")
        gen_form.addRow("", self.force_regen_default)

        layout.addWidget(gen_group)

        # ── Output Settings ───────────────────────────────────────────────────
        out_group = QGroupBox("Output Settings")
        out_form = QFormLayout(out_group)
        out_form.setSpacing(8)

        out_path_row = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("outputs/")
        out_path_row.addWidget(self.output_dir)
        btn_browse_out = QPushButton("Browse…")
        btn_browse_out.setFixedWidth(80)
        btn_browse_out.clicked.connect(self._browse_output_dir)
        out_path_row.addWidget(btn_browse_out)
        out_form.addRow("Output Folder:", out_path_row)

        self.compile_pdf = QCheckBox("Compile Typst to PDF after generation")
        out_form.addRow("", self.compile_pdf)

        typst_row = QHBoxLayout()
        self.typst_binary = QLineEdit()
        self.typst_binary.setPlaceholderText("typst  (leave blank to auto-detect from PATH)")
        typst_row.addWidget(self.typst_binary)
        btn_browse_typst = QPushButton("Browse…")
        btn_browse_typst.setFixedWidth(80)
        btn_browse_typst.clicked.connect(self._browse_typst)
        typst_row.addWidget(btn_browse_typst)
        out_form.addRow("Typst Binary:", typst_row)

        layout.addWidget(out_group)

        # ── Profile Photo Settings ────────────────────────────────────────────
        photo_group = QGroupBox("Profile Photo")
        photo_form = QFormLayout(photo_group)
        photo_form.setSpacing(8)

        photo_row = QHBoxLayout()
        self.photo_path = QLineEdit()
        self.photo_path.setPlaceholderText("internal/profile_photo/photo.jpg")
        photo_row.addWidget(self.photo_path)
        btn_browse_photo = QPushButton("Browse…")
        btn_browse_photo.setFixedWidth(80)
        btn_browse_photo.clicked.connect(self._browse_photo)
        photo_row.addWidget(btn_browse_photo)
        photo_form.addRow("Photo File:", photo_row)

        self.photo_rotation = QComboBox()
        self.photo_rotation.addItems(["0°", "90°", "180°", "270°"])
        photo_form.addRow("Rotation:", self.photo_rotation)

        layout.addWidget(photo_group)

        layout.addStretch()

        # Wire all change signals to debounced save
        for widget in (
            self.model_name, self.research_model, self.output_dir,
            self.resume_title, self.typst_binary, self.photo_path,
        ):
            widget.textChanged.connect(self._schedule_save)
        for widget in (
            self.use_google_search, self.compile_pdf, self.force_regen_default,
        ):
            widget.stateChanged.connect(self._schedule_save)
        for widget in (self.template_combo, self.photo_rotation):
            widget.currentIndexChanged.connect(self._schedule_save)
        self.api_delay.valueChanged.connect(self._schedule_save)

    # ── Template discovery ────────────────────────────────────────────────────

    def _populate_templates(self) -> None:
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.template_combo.clear()
        if templates_dir.exists():
            for f in sorted(templates_dir.glob("*.typ")):
                self.template_combo.addItem(f.name, f.name)
        if self.template_combo.count() == 0:
            self.template_combo.addItem("modern.typ", "modern.typ")

    # ── File browser helpers ──────────────────────────────────────────────────

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_dir.setText(path)

    def _browse_typst(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Typst Binary")
        if path:
            self.typst_binary.setText(path)

    def _browse_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Photo", "", "Images (*.jpg *.jpeg *.png *.webp)"
        )
        if path:
            self.photo_path.setText(path)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _schedule_save(self, *_) -> None:
        self._debounce.start(500)

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name.text().strip() or "gemini-2.5-pro",
            "research_model": self.research_model.text().strip() or "gemini-2.5-flash",
            "api_delay": self.api_delay.value(),
            "use_google_search": self.use_google_search.isChecked(),
            "template": self.template_combo.currentData() or "modern.typ",
            "resume_title": self.resume_title.text().strip() or "Resume",
            "force_regen_default": self.force_regen_default.isChecked(),
            "output_dir": self.output_dir.text().strip() or "outputs",
            "compile_pdf": self.compile_pdf.isChecked(),
            "typst_binary": self.typst_binary.text().strip(),
            "photo_path": self.photo_path.text().strip(),
            "photo_rotation": self.photo_rotation.currentIndex() * 90,
        }

    def _save(self) -> None:
        data = self.to_dict()
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not SETTINGS_FILE.exists():
            return
        try:
            data: dict = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        _set = lambda w, v: (w.blockSignals(True), w.setText(str(v)), w.blockSignals(False))

        if "model_name" in data:
            _set(self.model_name, data["model_name"])
        if "research_model" in data:
            _set(self.research_model, data["research_model"])
        if "api_delay" in data:
            self.api_delay.setValue(float(data["api_delay"]))
        if "use_google_search" in data:
            self.use_google_search.setChecked(bool(data["use_google_search"]))
        if "template" in data:
            idx = self.template_combo.findData(data["template"])
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        if "resume_title" in data:
            _set(self.resume_title, data["resume_title"])
        if "force_regen_default" in data:
            self.force_regen_default.setChecked(bool(data["force_regen_default"]))
        if "output_dir" in data:
            _set(self.output_dir, data["output_dir"])
        if "compile_pdf" in data:
            self.compile_pdf.setChecked(bool(data["compile_pdf"]))
        if "typst_binary" in data:
            _set(self.typst_binary, data["typst_binary"])
        if "photo_path" in data:
            _set(self.photo_path, data["photo_path"])
        if "photo_rotation" in data:
            deg = int(data.get("photo_rotation", 0))
            idx = {0: 0, 90: 1, 180: 2, 270: 3}.get(deg, 0)
            self.photo_rotation.setCurrentIndex(idx)
