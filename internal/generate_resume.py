import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, cast

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, create_model

PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
OUTPUT_DIR_PATTERN = re.compile(r"^(?P<batch>\d{2})-(?P<index>\d{2}) (?P<name>.+)$")
ARCHIVE_VERSION_PATTERN = re.compile(r" V(?P<version>\d+)(?=\.[^.]+$)")
IGNORED_APPLICATION_DIRS = {"archive", "unstaged", "template", "company_name - job_name"}
DEFAULT_ARCHIVE_README = "# Application Hold Folder\n\nThis folder is intentionally ignored by the batch resume generator.\nMove application folders here when you do not want them processed in the current run.\nUse it for completed applications, parked applications, or anything you want kept out of the active generation queue.\n"
DEFAULT_JOB_TEMPLATE_README = "# COMPANY_NAME - JOB_NAME\n\nUse this folder as your starter application template.\nKeep the folder name format as COMPANY_NAME - JOB_NAME for clean output naming.\nAdd your role details to job_description.md and company research notes to company_research.md.\n"


@dataclass
class GeneratorSettings:
    applications_root: Path
    outputs_root: Path
    templates_root: Path
    selected_template_name: str
    master_portfolio_file: Path
    api_key_file: Path
    model_name: str = "gemini-2.5-flash"
    research_model_name: str = "gemini-2.5-flash"
    compile_pdf: bool = False
    compiler: str = "xelatex"
    enable_company_research_search: bool = False
    api_call_delay_seconds: float = 4.0
    auto_install_latex_on_windows: bool = True
    resume_title: str = "Dylan's Resume"
    profile_photo_file: Path | None = None
    profile_photo_rotation_degrees: int = 0


@dataclass
class JobSpec:
    job_name: str
    company_name: str
    role_hint: str
    folder: Path
    job_description_file: Path
    company_research_file: Path
    manual_sections_file: Path | None


@dataclass
class OutputFolderRecord:
    logical_name: str
    path: Path
    batch: int
    index: int


class ResumeSections(BaseModel):
    pass


class ApiRateLimiter:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = max(0.0, delay_seconds)
        self._last_call_time = 0.0

    def wait(self) -> None:
        if self.delay_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

    def mark(self) -> None:
        self._last_call_time = time.monotonic()


def extract_retry_delay_seconds(error_message: str, default_seconds: float = 10.0) -> float:
    retry_in_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_message, flags=re.IGNORECASE)
    if retry_in_match:
        return max(1.0, float(retry_in_match.group(1)))
    retry_delay_match = re.search(r"'retryDelay':\s*'([0-9]+(?:\.[0-9]+)?)s'", error_message)
    if retry_delay_match:
        return max(1.0, float(retry_delay_match.group(1)))
    return default_seconds


def format_api_error(model_name: str, exc: Exception) -> RuntimeError:
    status_code = getattr(exc, "status_code", None)
    message = str(exc)
    lowered = message.lower()

    if status_code == 429 or "resource_exhausted" in lowered or "quota" in lowered:
        return RuntimeError(
            "Gemini API quota/rate limit reached for "
            f"'{model_name}'. Wait for the suggested retry window, reduce request volume, "
            "or switch to a model/project with higher quota. "
            "Docs: https://ai.google.dev/gemini-api/docs/rate-limits"
        )

    if status_code in {500, 502, 503, 504} or "unavailable" in lowered:
        return RuntimeError(
            "Gemini API is temporarily unavailable. Please retry shortly. "
            f"Original error: {message}"
        )

    return RuntimeError(f"Gemini API request failed for model '{model_name}': {message}")


def generate_content_with_retry(
    client: genai.Client,
    model_name: str,
    contents: str,
    config: types.GenerateContentConfig,
    rate_limiter: ApiRateLimiter,
    max_attempts: int = 3,
) -> types.GenerateContentResponse:
    for attempt in range(1, max_attempts + 1):
        rate_limiter.wait()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            rate_limiter.mark()
            return response
        except genai_errors.APIError as exc:
            rate_limiter.mark()
            status_code = getattr(exc, "status_code", None)
            retryable = status_code in {429, 500, 502, 503, 504}
            if retryable and attempt < max_attempts:
                delay = extract_retry_delay_seconds(str(exc))
                print(
                    f"Warning: Gemini API error (status {status_code}) on attempt {attempt}/{max_attempts}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue
            raise format_api_error(model_name, exc) from exc

    raise RuntimeError(f"Gemini API request failed after {max_attempts} attempts for model '{model_name}'.")


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def has_minimum_research_content(content: str, min_chars: int = 15) -> bool:
    non_whitespace_count = len(re.findall(r"\S", content))
    return non_whitespace_count >= min_chars


def read_api_key_from_file(path: Path) -> str:
    if not path.exists():
        return ""
    for line in read_text(path).splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("#"):
            return candidate
    return ""


def resolve_api_key(api_key_file: Path) -> str:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    file_key = read_api_key_from_file(api_key_file)
    if file_key and "PASTE" not in file_key:
        print(f"GEMINI_API_KEY loaded from local file: {api_key_file}")
        return file_key
    raise RuntimeError(
        "No Gemini API key found. Set GEMINI_API_KEY in your terminal or create "
        f"{api_key_file} with your raw API key on one line."
    )


def ensure_supporting_structure(settings: GeneratorSettings) -> None:
    template_job_dir = settings.applications_root / "COMPANY_NAME - JOB_NAME"
    write_text(template_job_dir / "README.md", DEFAULT_JOB_TEMPLATE_README)
    write_text(template_job_dir / "job_description.md", "")
    write_text(template_job_dir / "company_research.md", "")
    write_text(settings.applications_root / "ARCHIVE" / "README.md", DEFAULT_ARCHIVE_README)
    write_text(settings.applications_root / "UNSTAGED" / "README.md", DEFAULT_ARCHIVE_README)
    if settings.profile_photo_file is not None:
        write_text(settings.profile_photo_file.parent / ".gitkeep", "")


def parse_job_name(folder_name: str) -> tuple[str, str]:
    parts = [part.strip() for part in folder_name.split(" - ", 1)]
    if len(parts) == 2:
        return parts[0], parts[1]
    return folder_name.strip(), ""


def discover_jobs(applications_root: Path) -> List[JobSpec]:
    jobs: List[JobSpec] = []
    for current_root, dirs, _ in os.walk(applications_root, topdown=True):
        dirs[:] = [directory for directory in dirs if directory.lower() not in IGNORED_APPLICATION_DIRS]
        current_dir = Path(current_root)
        if current_dir == applications_root:
            continue

        job_description_file = current_dir / "job_description.md"
        if not job_description_file.exists():
            continue

        company_name, role_hint = parse_job_name(current_dir.name)
        manual_override = None
        for candidate in (current_dir / "sections_override.json", current_dir / "sections.json"):
            if candidate.exists():
                manual_override = candidate
                break

        jobs.append(
            JobSpec(
                job_name=current_dir.name,
                company_name=company_name,
                role_hint=role_hint,
                folder=current_dir,
                job_description_file=job_description_file,
                company_research_file=current_dir / "company_research.md",
                manual_sections_file=manual_override,
            )
        )
    jobs.sort(key=lambda item: item.job_name.lower())
    return jobs


def extract_placeholders(template_text: str) -> List[str]:
    placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(template_text)))
    if not placeholders:
        raise ValueError("No placeholders found. Add tokens like {{TAILORED_PROFILE}}.")
    return placeholders


def build_schema_model(placeholders: Sequence[str]) -> type[BaseModel]:
    fields = {name: (str, ...) for name in placeholders}
    return cast(type[BaseModel], create_model("ResumeSections", __base__=ResumeSections, **fields))


def sanitize_model_output(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.replace("```latex", "").replace("```", "").strip()
    cleaned = cleaned.replace("\\n", "\n")
    return cleaned


def extract_latex_items(fragment: str) -> List[str]:
    return [
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(r"\\item\s+(.*?)(?=(?:\\item|\\end\{itemize\}))", fragment, flags=re.DOTALL)
    ]


def build_latex_itemize(items: Sequence[str]) -> str:
    unique_items = list(dict.fromkeys(item.strip() for item in items if item.strip()))
    if not unique_items:
        return ""
    body = "\n".join(f"\\item {item}" for item in unique_items)
    return (
        "\\begin{itemize}[label=\\textbullet, nosep, leftmargin=*, topsep=0.25em, partopsep=0pt, parsep=0pt, itemsep=0.2em]\n"
        f"{body}\n"
        "\\end{itemize}"
    )


def parse_master_bullets(master_data: str, heading: str) -> List[str]:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(master_data)
    if not match:
        return []
    return [item.strip() for item in re.findall(r"^-\s+(.+)$", match.group("body"), flags=re.MULTILINE)]


def build_resume_entry(title: str, subtitle: str, date_text: str, items_block: str) -> str:
    entry_parts = [f"\\cvevent{{{title}}}{{{subtitle}}}{{{date_text}}}{{}}"]
    if items_block:
        entry_parts.append("\\vspace{-0.9em}")
        entry_parts.append(items_block)
    entry_parts.append("\\medskip")
    return "\n".join(entry_parts)


def normalize_experience_fragment(fragment: str) -> str:
    entry_pattern = re.compile(
        r"\\textbf\{(?P<title>.+?)\}\s*\\hfill\s*(?P<date>.*?)\s*\\textit\{(?P<subtitle>.+?)\}\s*(?P<items>\\begin\{itemize\}.*?\\end\{itemize\})",
        flags=re.DOTALL,
    )
    entries: List[str] = []
    for match in entry_pattern.finditer(fragment):
        title = re.sub(r"\s+", " ", match.group("title")).strip()
        subtitle = re.sub(r"\s+", " ", match.group("subtitle")).strip()
        date_text = re.sub(r"\s+", " ", match.group("date")).strip()
        if "youtube" in subtitle.lower() or "i did a thing" in subtitle.lower():
            continue
        items_block = build_latex_itemize(extract_latex_items(match.group("items")))
        entries.append(build_resume_entry(title, subtitle, date_text, items_block))
    return "\n\n".join(entries).strip() or sanitize_model_output(fragment)


def normalize_projects_fragment(fragment: str) -> str:
    entry_pattern = re.compile(
        r"\\textbf\{(?P<title>.+?)\}\s*\\hfill\s*\\textit\{(?P<subtitle>.+?)\}\s*(?P<items>\\begin\{itemize\}.*?\\end\{itemize\})",
        flags=re.DOTALL,
    )
    entries: List[str] = []
    for match in entry_pattern.finditer(fragment):
        title = re.sub(r"\s+", " ", match.group("title")).strip()
        subtitle = re.sub(r"\s+", " ", match.group("subtitle")).strip()
        items_block = build_latex_itemize(extract_latex_items(match.group("items")))
        entries.append(build_resume_entry(title, subtitle, "", items_block))
    return "\n\n".join(entries).strip() or sanitize_model_output(fragment)


def normalize_coursework_fragment(fragment: str, maximum_items: int = 5) -> str:
    items = extract_latex_items(fragment)
    if not items:
        return sanitize_model_output(fragment)
    return build_latex_itemize(items[:maximum_items])


def normalize_certifications_fragment(fragment: str, master_data: str, minimum_items: int = 3) -> str:
    items = extract_latex_items(fragment)
    fallback_items = parse_master_bullets(master_data, "Section E — Certifications and Licences")
    merged_items = list(dict.fromkeys(items + fallback_items))
    return build_latex_itemize(merged_items[: max(minimum_items, len(items))] or fallback_items[:minimum_items])


def normalize_youtube_bullets(model_data: Dict[str, str]) -> None:
    bullet = model_data.get("YOUTUBE_BULLET_1", "")
    if not bullet:
        return
    bullet = re.sub(
        r"Rapidly developed\s+17\s+minimum viable products\s+for filmed engineering builds",
        "Rapidly developed 10 filmed engineering builds",
        bullet,
        flags=re.IGNORECASE,
    )
    bullet = re.sub(
        r"Rapidly developed\s+17\s+minimum viable products",
        "Rapidly developed 10 builds",
        bullet,
        flags=re.IGNORECASE,
    )
    model_data["YOUTUBE_BULLET_1"] = bullet


def normalize_model_sections(model_data: Dict[str, str], master_data: str) -> Dict[str, str]:
    normalized = dict(model_data)
    normalize_youtube_bullets(normalized)
    if "DYNAMIC_EXPERIENCE" in normalized:
        normalized["DYNAMIC_EXPERIENCE"] = normalize_experience_fragment(normalized["DYNAMIC_EXPERIENCE"])
    if "DYNAMIC_PROJECTS" in normalized:
        normalized["DYNAMIC_PROJECTS"] = normalize_projects_fragment(normalized["DYNAMIC_PROJECTS"])
    if "TARGETED_COURSEWORK" in normalized:
        normalized["TARGETED_COURSEWORK"] = normalize_coursework_fragment(normalized["TARGETED_COURSEWORK"], maximum_items=5)
    if "TARGETED_CERTIFICATIONS" in normalized:
        normalized["TARGETED_CERTIFICATIONS"] = normalize_certifications_fragment(
            normalized["TARGETED_CERTIFICATIONS"],
            master_data,
            minimum_items=3,
        )
    return normalized


def render_template(template_text: str, values: Dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", sanitize_model_output(value))
    return rendered


def validate_key_parity(placeholders: Sequence[str], model_data: Dict[str, str]) -> None:
    expected = set(placeholders)
    actual = set(model_data.keys())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        message = ["Placeholder/schema mismatch detected."]
        if missing:
            message.append(f"Missing keys: {', '.join(missing)}")
        if extra:
            message.append(f"Unexpected keys: {', '.join(extra)}")
        raise ValueError("\n".join(message))


def filter_model_data(placeholders: Sequence[str], model_data: Dict[str, str]) -> Dict[str, str]:
    expected = set(placeholders)
    return {key: value for key, value in model_data.items() if key in expected}


def load_manual_sections(path: Path) -> Dict[str, str]:
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        raise ValueError(f"Manual sections file must contain a JSON object: {path}")
    normalized: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"Manual sections file must contain string keys and string values: {path}")
        normalized[key] = value
    return normalized


def run_compile(compiler: str, tex_file: Path, working_dir: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        [compiler, "-interaction=nonstopmode", "-halt-on-error", tex_file.name],
        cwd=working_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _candidate_compiler_paths() -> List[Path]:
    candidates: List[Path] = []
    if os.name != "nt":
        return candidates

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "")

    roots = [
        Path(local_app_data) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
        Path(local_app_data) / "Programs" / "MiKTeX" / "miktex" / "bin",
        Path(program_files) / "MiKTeX" / "miktex" / "bin" / "x64",
        Path(program_files) / "MiKTeX" / "miktex" / "bin",
        Path(program_files_x86) / "MiKTeX" / "miktex" / "bin",
    ]

    for root in roots:
        if root and root.exists():
            candidates.append(root / "xelatex.exe")
            candidates.append(root / "pdflatex.exe")

    return candidates


def resolve_available_compiler(preferred: str) -> str | None:
    candidates = [preferred]
    for fallback in ("xelatex", "pdflatex"):
        if fallback not in candidates:
            candidates.append(fallback)

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved

    for candidate_path in _candidate_compiler_paths():
        if candidate_path.exists():
            return str(candidate_path)

    return None


def try_install_latex_windows() -> bool:
    if os.name != "nt":
        return False
    if shutil.which("winget") is None:
        return False

    command = [
        "winget",
        "install",
        "--id",
        "MiKTeX.MiKTeX",
        "-e",
        "--source",
        "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return False

    success_codes = {0}
    return completed.returncode in success_codes


def extract_field(master_data: str, label: str) -> str:
    pattern = re.compile(rf"^\s*-?\s*{re.escape(label)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(master_data)
    return match.group(1).strip() if match else ""


def safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = ''.join('_' if char in invalid else char for char in name).strip()
    return cleaned or "Resume"


def resolve_template_file(settings: GeneratorSettings) -> Path:
    requested = settings.selected_template_name.strip()
    if not requested:
        raise RuntimeError("No template selected. Set SELECTED_TEMPLATE_NAME in main.py.")

    candidates = [requested]
    if not requested.lower().endswith(".tex"):
        candidates.append(f"{requested}.tex")

    for candidate in candidates:
        template_file = settings.templates_root / candidate
        if template_file.exists():
            return template_file

    available_templates = sorted(path.name for path in settings.templates_root.glob("*.tex"))
    available_text = ", ".join(available_templates) if available_templates else "no .tex templates found"
    raise RuntimeError(
        f"Template '{settings.selected_template_name}' was not found in {settings.templates_root}. "
        f"Available templates: {available_text}."
    )


def build_profile_photo_block(settings: GeneratorSettings, output_dir: Path) -> str:
    if settings.profile_photo_file is None or not settings.profile_photo_file.exists():
        return ""
    target_name = f"profile_photo{settings.profile_photo_file.suffix}"
    target_path = output_dir / target_name
    shutil.copy2(settings.profile_photo_file, target_path)
    return f"\\ResumeProfilePhoto{{{target_name}}}{{{settings.profile_photo_rotation_degrees}}}"


def build_static_placeholders(
    settings: GeneratorSettings,
    master_data: str,
    output_dir: Path,
) -> Dict[str, str]:
    linkedin_url = extract_field(master_data, "LinkedIn") or "https://linkedin.com/in/your-profile"
    github_url = extract_field(master_data, "GitHub") or "https://github.com/your-profile"
    email_address = extract_field(master_data, "Email") or "you@example.com"
    location = extract_field(master_data, "Location") or "Your Location"
    full_name = extract_field(master_data, "Name") or extract_field(master_data, "Full Name") or "Your Name"
    return {
        "FULL_NAME": full_name,
        "EMAIL_ADDRESS": email_address,
        "LINKEDIN_URL": linkedin_url,
        "GITHUB_URL": github_url,
        "LOCATION": location,
        "PROFILE_PHOTO_BLOCK": build_profile_photo_block(settings, output_dir),
        "PORTFOLIO_NOTE": "\\cvsection{Additional Information}\nFull Project Portfolio \\& References\\nAvailable upon request.",
    }


def build_resume_prompt(
    placeholders: Sequence[str],
    master_data: str,
    application_text: str,
    company_research: str,
) -> str:
    placeholder_block = "\n".join(f"- {name}" for name in placeholders)
    constraints: List[str] = []
    for name in placeholders:
        if name == "TAILORED_PROFILE":
            constraints.append(f"- {name}: 2-4 sentences, no bullet list, evidence-backed and role-specific.")
        elif "COURSEWORK" in name:
            constraints.append(
                f"- {name}: 4-5 subjects maximum, show marks beside each chosen subject, prioritize strongest relevant marks first."
            )
        elif "PROJECTS" in name:
            constraints.append(
                f"- {name}: 2-4 projects maximum, concrete tools and technical details, and format each project as a separate entry with clear spacing."
            )
        elif "EXPERIENCE" in name:
            constraints.append(
                f"- {name}: concise LaTeX event/list fragments only, select only the most relevant experience entries, exclude the YouTube product-development role because the template renders it separately, and keep each entry clearly separated."
            )
        elif "SKILLS" in name:
            constraints.append(f"- {name}: role-relevant technical skill groups or tags only.")
        elif "CERTIFICATIONS" in name:
            constraints.append(f"- {name}: role-relevant certifications only, concise formatting, and include at least 3 certifications when the source data supports it.")
        elif "BULLET" in name:
            constraints.append(f"- {name}: exactly one sentence, quantified or specific if possible.")
        else:
            constraints.append(f"- {name}: concise LaTeX-safe content fragment.")

    return f"""
You are generating LaTeX-ready section content for a resume template.
Return data only through the structured response schema.
Do not output markdown, commentary, code fences, XML, or YAML.

Rules:
1) Produce exactly one string value for each placeholder key.
2) Every value must be valid LaTeX fragment content for direct insertion.
3) Do not include surrounding placeholder braces in the returned values.
4) Do not invent achievements not supported by the source data.
5) Escape LaTeX-sensitive characters when needed, including %, &, _, and #.
6) Avoid repeating the same claim across multiple fields unless it is central to the role fit.
7) Relevant coursework must show grades/marks beside the selected subject names.

Per-placeholder constraints:
{chr(10).join(constraints)}

Placeholders to fill:
{placeholder_block}

Static source data:
---
{master_data}
---

Target application:
---
{application_text}
---

Company research:
---
{company_research or 'No company research provided.'}
---
""".strip()


def build_company_research_query(job: JobSpec) -> str:
    role_hint_text = f"Role hint: {job.role_hint}\n" if job.role_hint else ""
    return f"""
Research the company {job.company_name}.
{role_hint_text}
Produce a concise markdown brief with these sections:
1. Company self-description
2. External perspective and useful candidate context
3. Internship or graduate-role expectations
4. Relevant technical stacks, domains, and strengths to emphasize
5. ATS, recruiter, and trigger keywords likely worth echoing when truly evidenced
6. Brand and visual direction with one primary accent HEX and one soft tint HEX

Use the role hint for extra specificity when available.
Keep claims source-aware and concise.
""".strip()


def call_structured_model(
    client: genai.Client,
    model_name: str,
    prompt: str,
    schema_model: type[BaseModel],
    rate_limiter: ApiRateLimiter,
) -> Dict[str, str]:
    response = generate_content_with_retry(
        client=client,
        model_name=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=schema_model,
        ),
        rate_limiter=rate_limiter,
        max_attempts=3,
    )

    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        if isinstance(parsed, BaseModel):
            return cast(Dict[str, str], parsed.model_dump())
        if isinstance(parsed, dict):
            return cast(Dict[str, str], parsed)

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Model returned no parsable content.")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("Structured output was not a JSON object.")
    return cast(Dict[str, str], data)


def maybe_generate_company_research(
    client: genai.Client,
    settings: GeneratorSettings,
    job: JobSpec,
    rate_limiter: ApiRateLimiter,
) -> str:
    if job.company_research_file.exists():
        existing = read_text(job.company_research_file)
        if has_minimum_research_content(existing, min_chars=15):
            return existing.strip()
    if not settings.enable_company_research_search:
        return ""

    response = generate_content_with_retry(
        client=client,
        model_name=settings.research_model_name,
        contents=build_company_research_query(job),
        config=types.GenerateContentConfig(
            temperature=0.2,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
        rate_limiter=rate_limiter,
        max_attempts=2,
    )

    research_text = getattr(response, "text", None)
    if not research_text:
        return ""

    # Cache research in the application folder so subsequent runs do not re-query.
    write_text(job.company_research_file, research_text.strip() + "\n")
    return research_text.strip()


def parse_output_folder(folder: Path) -> OutputFolderRecord:
    match = OUTPUT_DIR_PATTERN.match(folder.name)
    if match:
        return OutputFolderRecord(
            logical_name=match.group("name"),
            path=folder,
            batch=int(match.group("batch")),
            index=int(match.group("index")),
        )
    return OutputFolderRecord(logical_name=folder.name, path=folder, batch=1, index=1)


def collect_output_folders(outputs_root: Path) -> List[OutputFolderRecord]:
    if not outputs_root.exists():
        return []
    records = [parse_output_folder(path) for path in outputs_root.iterdir() if path.is_dir()]
    records.sort(key=lambda item: (item.batch, item.index, item.logical_name.lower()))
    return records


def rename_paths(rename_map: Dict[Path, Path]) -> None:
    if not rename_map:
        return
    temp_paths: Dict[Path, Path] = {}
    for index, source in enumerate(rename_map):
        temp_path = source.with_name(f".__tmp_rename_{index}__ {source.name}")
        source.rename(temp_path)
        temp_paths[temp_path] = rename_map[source]
    for temp_path, target in temp_paths.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path.rename(target)


def bump_non_current_output_folders(outputs_root: Path, current_job_names: Sequence[str]) -> None:
    current_set = {name.lower() for name in current_job_names}
    rename_map: Dict[Path, Path] = {}
    for record in collect_output_folders(outputs_root):
        if record.logical_name.lower() in current_set:
            continue
        new_name = f"{min(record.batch + 1, 99):02d}-{record.index:02d} {record.logical_name}"
        if record.path.name != new_name:
            rename_map[record.path] = record.path.with_name(new_name)
    rename_paths(rename_map)


def ensure_current_output_folder(outputs_root: Path, logical_name: str, batch_index: int) -> Path:
    desired_name = f"01-{batch_index:02d} {logical_name}"
    desired_path = outputs_root / desired_name
    existing = None
    for record in collect_output_folders(outputs_root):
        if record.logical_name.lower() == logical_name.lower():
            existing = record.path
            break
    if existing is None:
        desired_path.mkdir(parents=True, exist_ok=True)
        return desired_path
    if existing != desired_path:
        rename_paths({existing: desired_path})
    desired_path.mkdir(parents=True, exist_ok=True)
    return desired_path


def next_archive_version(archive_dir: Path) -> int:
    highest = 0
    if archive_dir.exists():
        for path in archive_dir.iterdir():
            if not path.is_file():
                continue
            match = ARCHIVE_VERSION_PATTERN.search(path.name)
            if match:
                highest = max(highest, int(match.group("version")))
    return highest + 1


def archive_existing_artifacts(job_output_dir: Path, resume_title: str) -> None:
    safe_title = safe_filename(resume_title)
    current_artifacts = [
        job_output_dir / f"{safe_title}.tex",
        job_output_dir / f"{safe_title}.pdf",
        job_output_dir / "sections.json",
    ]
    existing = [path for path in current_artifacts if path.exists()]
    if not existing:
        return
    archive_dir = job_output_dir / "ARCHIVE"
    archive_dir.mkdir(parents=True, exist_ok=True)
    version = next_archive_version(archive_dir)
    for path in existing:
        archived_name = f"{path.stem} V{version}{path.suffix}"
        shutil.move(str(path), str(archive_dir / archived_name))


def build_job_artifact_paths(job_output_dir: Path, resume_title: str) -> Dict[str, Path]:
    safe_title = safe_filename(resume_title)
    return {
        "tex": job_output_dir / f"{safe_title}.tex",
        "pdf": job_output_dir / f"{safe_title}.pdf",
        "json": job_output_dir / "sections.json",
    }


def enforce_clean_output_contents(job_output_dir: Path, resume_title: str) -> None:
    safe_title = safe_filename(resume_title)
    allowed_files = {f"{safe_title}.tex", f"{safe_title}.pdf", "sections.json"}
    allowed_dirs = {"ARCHIVE"}

    for path in job_output_dir.iterdir():
        if path.is_file() and path.name not in allowed_files:
            path.unlink()
        elif path.is_dir() and path.name not in allowed_dirs:
            shutil.rmtree(path)


def load_template_text(settings: GeneratorSettings) -> str:
    template_file = resolve_template_file(settings)
    return read_text(template_file)


def copy_template_support_files(settings: GeneratorSettings, output_dir: Path) -> None:
    # Copy class/style files so custom LaTeX templates (e.g., AltaCV) compile in output folders.
    for extension in ("*.cls", "*.sty", "*.bst", "*.bbx", "*.cbx"):
        for support_file in settings.templates_root.glob(extension):
            if support_file.is_file():
                shutil.copy2(support_file, output_dir / support_file.name)


def process_job(
    client: genai.Client,
    settings: GeneratorSettings,
    master_data: str,
    template_text: str,
    job: JobSpec,
    output_dir: Path,
    rate_limiter: ApiRateLimiter,
) -> None:
    archive_existing_artifacts(output_dir, settings.resume_title)
    static_template = render_template(template_text, build_static_placeholders(settings, master_data, output_dir))
    placeholders = extract_placeholders(static_template)

    if job.manual_sections_file is not None:
        model_data = load_manual_sections(job.manual_sections_file)
    else:
        application_text = read_text(job.job_description_file)
        company_research = maybe_generate_company_research(client, settings, job, rate_limiter)
        if not company_research and job.company_research_file.exists():
            company_research = read_text(job.company_research_file)
        prompt = build_resume_prompt(placeholders, master_data, application_text, company_research)
        schema_model = build_schema_model(placeholders)
        model_data = call_structured_model(client, settings.model_name, prompt, schema_model, rate_limiter)

    model_data = filter_model_data(placeholders, model_data)
    model_data = normalize_model_sections(model_data, master_data)
    validate_key_parity(placeholders, model_data)
    artifact_paths = build_job_artifact_paths(output_dir, settings.resume_title)
    write_json(artifact_paths["json"], model_data)

    rendered_tex = render_template(static_template, model_data)
    write_text(artifact_paths["tex"], rendered_tex)

    if not settings.compile_pdf:
        enforce_clean_output_contents(output_dir, settings.resume_title)
        return

    copy_template_support_files(settings, output_dir)

    compiler = resolve_available_compiler(settings.compiler)
    if compiler is None and settings.auto_install_latex_on_windows and os.name == "nt":
        print("LaTeX compiler not found. Attempting automatic MiKTeX install via winget...")
        if try_install_latex_windows():
            compiler = resolve_available_compiler(settings.compiler)

    if compiler is None:
        warning = (
            "PDF compilation skipped because no LaTeX compiler was found. "
            "Run internal/install_latex.ps1 (Windows) or install TeX Live/MiKTeX manually, then re-run main.py."
        )
        print(f"Warning: {warning}")
        enforce_clean_output_contents(output_dir, settings.resume_title)
        return
    preferred_path = shutil.which(settings.compiler)
    if preferred_path is None or Path(preferred_path).resolve() != Path(compiler).resolve():
        print(
            f"Warning: preferred compiler '{settings.compiler}' not found. "
            f"Using '{compiler}' instead."
        )

    compilers_to_try = [compiler]
    primary_name = Path(compiler).name.lower()
    fallback_name = "pdflatex" if "xelatex" in primary_name else "xelatex"
    fallback_compiler = resolve_available_compiler(fallback_name)
    if fallback_compiler is not None and fallback_compiler not in compilers_to_try:
        compilers_to_try.append(fallback_compiler)

    final_code = 1
    last_stdout = ""
    last_stderr = ""

    for compiler_to_try in compilers_to_try:
        code, stdout, stderr = run_compile(compiler_to_try, artifact_paths["tex"], output_dir)
        final_code = code
        last_stdout = stdout
        last_stderr = stderr

        if code == 0:
            break

    if final_code != 0:
        enforce_clean_output_contents(output_dir, settings.resume_title)
        stdout_lines = [line for line in last_stdout.splitlines() if line.strip()]
        stderr_lines = [line for line in last_stderr.splitlines() if line.strip()]
        stdout_excerpt = "\n".join(stdout_lines[-40:]) if stdout_lines else "(no stdout output)"
        stderr_excerpt = "\n".join(stderr_lines[-25:]) if stderr_lines else "(no stderr output)"
        raise RuntimeError(
            f"LaTeX compilation failed for {job.job_name}.\n"
            f"Last compiler stdout lines:\n{stdout_excerpt}\n\n"
            f"Last compiler stderr lines:\n{stderr_excerpt}"
        )
    produced_pdf = artifact_paths["tex"].with_suffix(".pdf")
    if produced_pdf.exists() and produced_pdf != artifact_paths["pdf"]:
        shutil.move(str(produced_pdf), str(artifact_paths["pdf"]))
    if not artifact_paths["pdf"].exists():
        enforce_clean_output_contents(output_dir, settings.resume_title)
        raise RuntimeError(f"Compilation completed but PDF was not produced for {job.job_name}.")

    enforce_clean_output_contents(output_dir, settings.resume_title)


def run_batch(settings: GeneratorSettings) -> None:
    ensure_supporting_structure(settings)
    settings.outputs_root.mkdir(parents=True, exist_ok=True)

    jobs = discover_jobs(settings.applications_root)
    if not jobs:
        raise RuntimeError(
            f"No job_description.md files were found under {settings.applications_root}. "
            "Create an application folder using applications/COMPANY_NAME - JOB_NAME/."
        )

    bump_non_current_output_folders(settings.outputs_root, [job.job_name for job in jobs])

    api_key = resolve_api_key(settings.api_key_file)
    client = genai.Client(api_key=api_key)
    rate_limiter = ApiRateLimiter(settings.api_call_delay_seconds)
    master_data = read_text(settings.master_portfolio_file)
    template_text = load_template_text(settings)

    print(f"Found {len(jobs)} job(s) to process.")
    for index, job in enumerate(jobs, start=1):
        output_dir = ensure_current_output_folder(settings.outputs_root, job.job_name, index)
        process_job(client, settings, master_data, template_text, job, output_dir, rate_limiter)
        print(f"Completed: {job.job_name} -> {output_dir}")