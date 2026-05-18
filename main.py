from pathlib import Path
from internal.generate_resume import GeneratorSettings, run_batch

# User configuration
APPLICATIONS_ROOT = Path("applications")
OUTPUTS_ROOT = Path("outputs")
INTERNAL_ROOT = Path("internal")
TEMPLATES_ROOT = INTERNAL_ROOT / "templates"
SELECTED_TEMPLATE_NAME = "template.tex"
MASTER_PORTFOLIO_FILE = INTERNAL_ROOT / "data/master_portfolio.md"
API_KEY_FILE = INTERNAL_ROOT / "secrets/gemini_api_key.txt"
MODEL_NAME = "gemini-2.5-flash"
RESEARCH_MODEL_NAME = "gemini-2.5-flash"
COMPILE_PDF = True
COMPILER = "xelatex"
ENABLE_COMPANY_RESEARCH_SEARCH = False
API_CALL_DELAY_SECONDS = 4.0
AUTO_INSTALL_LATEX_ON_WINDOWS = True
RESUME_TITLE = "Dylan's Resume"
PROFILE_PHOTO_FILE = INTERNAL_ROOT / "profile_photo/Me.jpg"
PROFILE_PHOTO_ROTATION_DEGREES = 90

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
