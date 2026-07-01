"""Job card widget — displays a single job with status icon and checkbox."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


def _job_status(folder: Path) -> tuple[str, str]:
    """Return (icon, colour) for a job folder."""
    jd = folder / "job_description.md"
    if not jd.exists():
        return "⚠", "#f59e0b"
    cache = folder / "sections.json"
    out_cache = None
    # Check outputs/ for a matching sections.json (approximate check on folder name)
    if cache.exists():
        return "✓", "#22c55e"
    return "⚡", "#c4b5fd"


class JobCard(QWidget):
    def __init__(self, job_name: str, company_name: str, role_hint: str, folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.job_name = job_name
        self.folder = folder
        self.setObjectName("job_card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)

        icon_str, colour = _job_status(folder)
        icon_label = QLabel(icon_str)
        icon_label.setStyleSheet(f"color: {colour}; font-size: 14px;")
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        text_widget = QWidget()
        text_layout = QHBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)

        company_label = QLabel(company_name or job_name)
        company_label.setStyleSheet("font-weight: 700; color: #e2e8f0;")
        text_layout.addWidget(company_label)

        if role_hint:
            role_label = QLabel(role_hint)
            role_label.setStyleSheet("color: #64748b; font-size: 11px;")
            text_layout.addWidget(role_label)

        text_layout.addStretch()
        layout.addWidget(text_widget, 1)

        self.setFixedHeight(46)
        self.setStyleSheet(
            "QWidget#job_card { background-color: #2a2a3e; border: 1px solid #2d2d44; border-radius: 8px; margin: 2px 0; }"
            "QWidget#job_card:hover { border-color: #7c3aed; }"
        )

    @property
    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)
