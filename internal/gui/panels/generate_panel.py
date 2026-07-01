"""Generate panel — primary workflow tab."""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from internal.generate_resume import GeneratorSettings, discover_jobs, run_batch
from internal.gui.widgets.job_card import JobCard
from internal.gui.widgets.log_view import LogView

if TYPE_CHECKING:
    from internal.gui.app import MainWindow


class _GeneratorWorker(QThread):
    progress = pyqtSignal(str, str)
    finished = pyqtSignal(bool)

    def __init__(
        self,
        settings: GeneratorSettings,
        api_key: str,
        job_names: list[str],
        force_regenerate: bool,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._api_key = api_key
        self._job_names = job_names
        self._force_regenerate = force_regenerate
        self._cancel_flag: list[bool] = [False]

    def request_cancel(self) -> None:
        self._cancel_flag[0] = True

    def run(self) -> None:
        try:
            run_batch(
                settings=self._settings,
                api_key=self._api_key,
                job_names=self._job_names,
                force_regenerate=self._force_regenerate,
                progress_callback=lambda m, l: self.progress.emit(m, l),
                cancel_flag=self._cancel_flag,
            )
            self.finished.emit(True)
        except Exception as exc:
            self.progress.emit(str(exc), "error")
            self.finished.emit(False)


class GeneratePanel(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._worker: _GeneratorWorker | None = None
        self._cards: list[JobCard] = []
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_job_list_panel())
        splitter.addWidget(self._build_controls_panel())
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

    def _build_job_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        lbl = QLabel("Applications")
        lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #c4b5fd;")
        toolbar.addWidget(lbl)
        toolbar.addStretch()

        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_refresh = QPushButton("↻ Refresh")
        for btn in (btn_all, btn_none, btn_refresh):
            btn.setFixedHeight(28)
            toolbar.addWidget(btn)

        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        btn_refresh.clicked.connect(self.refresh_jobs)

        layout.addLayout(toolbar)

        # Scroll area for job cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._jobs_container = QWidget()
        self._jobs_layout = QVBoxLayout(self._jobs_container)
        self._jobs_layout.setContentsMargins(0, 0, 0, 0)
        self._jobs_layout.setSpacing(4)
        self._jobs_layout.addStretch()

        scroll.setWidget(self._jobs_container)
        layout.addWidget(scroll, 1)

        return panel

    def _build_controls_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── API Key ──────────────────────────────────────────────────────────
        key_lbl = QLabel("Gemini API Key")
        key_lbl.setStyleSheet("font-weight: 600; color: #c4b5fd;")
        layout.addWidget(key_lbl)

        self.api_key_field = QLineEdit()
        self.api_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_field.setPlaceholderText("Paste your API key here — never saved to disk")
        # Pre-populate from environment variable if available
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            self.api_key_field.setText(env_key)
        self.api_key_field.textChanged.connect(self._update_generate_button_state)
        layout.addWidget(self.api_key_field)

        key_note = QLabel("Session only · cleared when you close the window")
        key_note.setObjectName("label_muted")
        layout.addWidget(key_note)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep1)

        # ── Options ──────────────────────────────────────────────────────────
        self.force_regen_cb = QCheckBox("Force Regenerate (ignore cached sections.json)")
        layout.addWidget(self.force_regen_cb)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        # ── Generate / Cancel buttons ─────────────────────────────────────────
        self.btn_generate = QPushButton("Generate Resumes")
        self.btn_generate.setObjectName("btn_generate")
        self.btn_generate.setFixedHeight(44)
        self.btn_generate.clicked.connect(self._start_generation)
        layout.addWidget(self.btn_generate)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_generation)
        layout.addWidget(self.btn_cancel)

        # ── Log ───────────────────────────────────────────────────────────────
        log_header = QHBoxLayout()
        log_lbl = QLabel("Log")
        log_lbl.setStyleSheet("font-weight: 600; color: #c4b5fd;")
        log_header.addWidget(log_lbl)
        log_header.addStretch()
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(24)
        btn_clear.clicked.connect(self._clear_log)
        log_header.addWidget(btn_clear)
        layout.addLayout(log_header)

        self.log_view = LogView()
        self.log_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_view, 1)

        self._update_generate_button_state()
        return panel

    # ── Job list management ──────────────────────────────────────────────────

    def refresh_jobs(self) -> None:
        """Re-scan the applications folder and rebuild the job card list."""
        settings = self._main.build_settings()
        apps_root = settings.applications_root
        if not apps_root.exists():
            return

        # Clear existing cards
        for card in self._cards:
            card.setParent(None)
        self._cards.clear()

        try:
            jobs = discover_jobs(apps_root)
        except Exception:
            return

        # Insert before the stretch at the end
        stretch_item = self._jobs_layout.takeAt(self._jobs_layout.count() - 1)
        for job in jobs:
            card = JobCard(job.job_name, job.company_name, job.role_hint, job.folder)
            self._jobs_layout.addWidget(card)
            self._cards.append(card)
        self._jobs_layout.addStretch()

        self._update_generate_button_state()

    def _set_all_checked(self, checked: bool) -> None:
        for card in self._cards:
            card.set_checked(checked)
        self._update_generate_button_state()

    def _selected_job_names(self) -> list[str]:
        return [card.job_name for card in self._cards if card.is_checked]

    # ── Generation ───────────────────────────────────────────────────────────

    def _update_generate_button_state(self) -> None:
        has_key = bool(self.api_key_field.text().strip())
        has_jobs = any(card.is_checked for card in self._cards)
        self.btn_generate.setEnabled(has_key and has_jobs)

    def _start_generation(self) -> None:
        api_key = self.api_key_field.text().strip()
        if not api_key:
            self.log_view.append_message("No API key entered.", "error")
            return
        selected = self._selected_job_names()
        if not selected:
            self.log_view.append_message("No jobs selected.", "error")
            return

        settings = self._main.build_settings()
        force = self.force_regen_cb.isChecked()

        self._worker = _GeneratorWorker(settings, api_key, selected, force)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)

        self.btn_generate.setVisible(False)
        self.btn_cancel.setVisible(True)
        self._main.statusBar().showMessage("Running…")
        self._worker.start()

    def _cancel_generation(self) -> None:
        if self._worker:
            self._worker.request_cancel()
        self.log_view.append_message("Cancellation requested…", "warning")

    def _on_progress(self, message: str, level: str) -> None:
        self.log_view.append_message(message, level)
        self._main.statusBar().showMessage(message[:80])

    def _on_finished(self, success: bool) -> None:
        self.btn_generate.setVisible(True)
        self.btn_cancel.setVisible(False)
        status = "Batch complete." if success else "Batch finished with errors."
        self._main.statusBar().showMessage(status)
        self._worker = None
        self.refresh_jobs()

    def _clear_log(self) -> None:
        self.log_view.clear()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self.refresh_jobs()
