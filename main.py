import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from internal.gui.app import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Resume Generator")

    qss_path = Path(__file__).parent / "internal" / "gui" / "styles" / "theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

settings = GeneratorSettings(
    applications_root=APPLICATIONS_ROOT,
    outputs_root=OUTPUTS_ROOT,
    templates_root=TEMPLATES_ROOT,
    selected_template_name=SELECTED_TEMPLATE_NAME,
    master_portfolio_file=MASTER_PORTFOLIO_FILE,
    api_key_file=API_KEY_FILE,
    model_name=MODEL_NAME,
    research_model_name=RESEARCH_MODEL_NAME,
    compile_pdf=COMPILE_PDF,
    compiler=COMPILER,
    enable_company_research_search=ENABLE_COMPANY_RESEARCH_SEARCH,
    api_call_delay_seconds=API_CALL_DELAY_SECONDS,
    auto_install_latex_on_windows=AUTO_INSTALL_LATEX_ON_WINDOWS,
    resume_title=RESUME_TITLE,
    profile_photo_file=PROFILE_PHOTO_FILE,
    profile_photo_rotation_degrees=PROFILE_PHOTO_ROTATION_DEGREES,
)

if __name__ == "__main__":
    try:
        run_batch(settings)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
