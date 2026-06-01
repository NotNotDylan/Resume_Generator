"""Jobs panel — browse and manage application folders."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from internal.generate_resume import discover_jobs

if TYPE_CHECKING:
    from internal.gui.app import MainWindow


def _open_in_file_manager(path: Path) -> None:
    """Open a folder in the system file manager."""
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _open_in_editor(path: Path) -> None:
    """Open a file in the default system editor."""
    if sys.platform == "win32":
        subprocess.Popen(["notepad", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class _NewJobDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Application")
        self.setMinimumWidth(360)
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.company_field = QLineEdit()
        self.company_field.setPlaceholderText("e.g. Google")
        layout.addRow("Company Name:", self.company_field)

        self.role_field = QLineEdit()
        self.role_field.setPlaceholderText("e.g. Software Engineering Intern")
        layout.addRow("Role:", self.role_field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def folder_name(self) -> str:
        company = self.company_field.text().strip()
        role = self.role_field.text().strip()
        if company and role:
            return f"{company} - {role}"
        return company or role


class JobsPanel(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._jobs: list = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Left: job list ────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        title = QLabel("Job Applications")
        title.setStyleSheet("font-weight: 700; font-size: 14px; color: #c4b5fd;")
        left.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        left.addWidget(self.list_widget, 1)

        btn_new = QPushButton("+ New Application")
        btn_new.clicked.connect(self._new_job)
        left.addWidget(btn_new)

        root.addLayout(left, 1)

        # ── Right: action buttons ─────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        title_r = QLabel("Actions")
        title_r.setStyleSheet("font-weight: 700; font-size: 14px; color: #c4b5fd;")
        right.addWidget(title_r)

        self.btn_open_folder = QPushButton("📁  Open in File Manager")
        self.btn_edit_jd = QPushButton("✏  Edit Job Description")
        self.btn_edit_research = QPushButton("🔍  Edit Company Research")
        self.btn_view_cache = QPushButton("📄  View AI Cache (sections.json)")
        self.btn_delete_cache = QPushButton("🗑  Delete AI Cache")
        self.btn_archive = QPushButton("📦  Archive Application")

        for btn in (
            self.btn_open_folder,
            self.btn_edit_jd,
            self.btn_edit_research,
            self.btn_view_cache,
            self.btn_delete_cache,
            self.btn_archive,
        ):
            btn.setFixedHeight(36)
            btn.setEnabled(False)
            right.addWidget(btn)

        right.addStretch()

        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_edit_jd.clicked.connect(self._edit_jd)
        self.btn_edit_research.clicked.connect(self._edit_research)
        self.btn_view_cache.clicked.connect(self._view_cache)
        self.btn_delete_cache.clicked.connect(self._delete_cache)
        self.btn_archive.clicked.connect(self._archive_job)

        root.addLayout(right)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _selected_job(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self._jobs):
            return self._jobs[idx]
        return None

    def _on_selection_changed(self, row: int) -> None:
        has_sel = 0 <= row < len(self._jobs)
        for btn in (
            self.btn_open_folder,
            self.btn_edit_jd,
            self.btn_edit_research,
            self.btn_view_cache,
            self.btn_delete_cache,
            self.btn_archive,
        ):
            btn.setEnabled(has_sel)

    def refresh_jobs(self) -> None:
        self.list_widget.clear()
        self._jobs = []
        try:
            settings = self._main.build_settings()
            self._jobs = discover_jobs(settings.applications_root)
        except Exception:
            return
        for job in self._jobs:
            cache = (settings.outputs_root).glob(f"*{job.job_name}/sections.json")
            has_cache = any(True for _ in cache)
            icon = "✓ " if has_cache else "  "
            item = QListWidgetItem(f"{icon}{job.job_name}")
            self.list_widget.addItem(item)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _new_job(self) -> None:
        dlg = _NewJobDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.folder_name
        if not name:
            return
        settings = self._main.build_settings()
        folder = settings.applications_root / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "job_description.md").write_text("", encoding="utf-8")
        (folder / "company_research.md").write_text("", encoding="utf-8")
        self.refresh_jobs()
        # Open job description immediately
        _open_in_editor(folder / "job_description.md")

    def _open_folder(self) -> None:
        job = self._selected_job()
        if job:
            _open_in_file_manager(job.folder)

    def _edit_jd(self) -> None:
        job = self._selected_job()
        if job:
            _open_in_editor(job.job_description_file)

    def _edit_research(self) -> None:
        job = self._selected_job()
        if job:
            _open_in_editor(job.company_research_file)

    def _view_cache(self) -> None:
        job = self._selected_job()
        if not job:
            return
        cache = job.folder / "sections.json"
        if not cache.exists():
            QMessageBox.information(self, "No Cache", "No sections.json cache found for this job.\nGenerate the resume first.")
            return
        _open_in_editor(cache)

    def _delete_cache(self) -> None:
        job = self._selected_job()
        if not job:
            return
        cache = job.folder / "sections.json"
        if not cache.exists():
            QMessageBox.information(self, "No Cache", "No sections.json cache found.")
            return
        reply = QMessageBox.question(
            self,
            "Delete Cache",
            f"Delete sections.json for '{job.job_name}'?\nThe next generation run will call Gemini again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cache.unlink()
            self.refresh_jobs()

    def _archive_job(self) -> None:
        job = self._selected_job()
        if not job:
            return
        settings = self._main.build_settings()
        reply = QMessageBox.question(
            self,
            "Archive Application",
            f"Move '{job.job_name}' to applications/ARCHIVE/?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            dest = settings.applications_root / "ARCHIVE" / job.job_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(job.folder), str(dest))
            self.refresh_jobs()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self.refresh_jobs()
