"""
generate_resume.py — Core generation engine.

No GUI imports. All public functions are synchronous.
The GUI runs run_batch() on a QThread.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, cast

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, create_model

PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
OUTPUT_DIR_PATTERN = re.compile(r"^(?P<batch>\d{2})-(?P<index>\d{2}) (?P<name>.+)$")
ARCHIVE_VERSION_PATTERN = re.compile(r" V(?P<version>\d+)(?=\.[^.]+$)")
IGNORED_APPLICATION_DIRS = {"archive", "unstaged", "template", "company_name - job_name"}

DEFAULT_ARCHIVE_README = (
    "# Application Hold Folder\n\n"
    "This folder is intentionally ignored by the batch resume generator.\n"
    "Move application folders here when you do not want them processed.\n"
)
DEFAULT_JOB_TEMPLATE_README = (
    "# COMPANY_NAME - JOB_NAME\n\n"
    "Use this folder as your starter application template.\n"
    "Paste the job posting into job_description.md.\n"
    "Add company research notes to company_research.md.\n"
)


@dataclass
class GeneratorSettings:
    applications_root: Path
    outputs_root: Path
    templates_root: Path
    selected_template_name: str
    master_portfolio_file: Path
    model_name: str = "gemini-2.5-flash"
    research_model_name: str = "gemini-2.5-flash"
    compile_pdf: bool = False
    typst_binary_path: str = ""
    enable_company_research: bool = False
    api_call_delay_seconds: float = 4.0
    resume_title: str = "Resume"
    profile_photo_file: Optional[Path] = None
    profile_photo_rotation_degrees: int = 0


@dataclass
class JobSpec:
    job_name: str
    company_name: str
    role_hint: str
    folder: Path
    job_description_file: Path
    company_research_file: Path
    manual_sections_file: Optional[Path]


@dataclass
class OutputFolderRecord:
    logical_name: str
    path: Path
    batch: int
    index: int


class _ResumeBase(BaseModel):
    pass


class ApiRateLimiter:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = max(0.0, delay_seconds)
        self._last_call_time: float = 0.0

    def wait(self) -> None:
        if self.delay_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

    def mark(self) -> None:
        self._last_call_time = time.monotonic()


def extract_retry_delay_seconds(error_message: str, default_seconds: float = 10.0) -> float:
    m = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_message, re.IGNORECASE)
    if m:
        return max(1.0, float(m.group(1)))
    m = re.search(r"'retryDelay':\s*'([0-9]+(?:\.[0-9]+)?)s'", error_message)
    if m:
        return max(1.0, float(m.group(1)))
    return default_seconds


def format_api_error(model_name: str, exc: Exception) -> RuntimeError:
    status_code = getattr(exc, "status_code", None)
    message = str(exc)
    lowered = message.lower()
    if status_code == 429 or "resource_exhausted" in lowered or "quota" in lowered:
        return RuntimeError(
            f"Gemini API quota/rate limit reached for '{model_name}'. "
            "Increase the API delay in Settings, wait for the quota window to reset, "
            "or switch to a model with higher quota."
        )
    if status_code in {500, 502, 503, 504} or "unavailable" in lowered:
        return RuntimeError(f"Gemini API temporarily unavailable. Retry shortly. Original: {message}")
    return RuntimeError(f"Gemini API request failed for model '{model_name}': {message}")


def generate_content_with_retry(
    client: genai.Client,
    model_name: str,
    contents: str,
    config: types.GenerateContentConfig,
    rate_limiter: ApiRateLimiter,
    max_attempts: int = 3,
    progress: Optional[Callable[[str, str], None]] = None,
) -> types.GenerateContentResponse:
    _log = progress or (lambda m, l: print(m))
    for attempt in range(1, max_attempts + 1):
        rate_limiter.wait()
        try:
            response = client.models.generate_content(model=model_name, contents=contents, config=config)
            rate_limiter.mark()
            return response
        except genai_errors.APIError as exc:
            rate_limiter.mark()
            status_code = getattr(exc, "status_code", None)
            retryable = status_code in {429, 500, 502, 503, 504}
            if retryable and attempt < max_attempts:
                delay = extract_retry_delay_seconds(str(exc))
                _log(f"Gemini API error (status {status_code}) attempt {attempt}/{max_attempts}. Retrying in {delay:.1f}s…", "warning")
                time.sleep(delay)
                continue
            raise format_api_error(model_name, exc) from exc
    raise RuntimeError(f"Gemini API failed after {max_attempts} attempts for '{model_name}'.")


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


def has_minimum_content(content: str, min_chars: int = 15) -> bool:
    return len(re.findall(r"\S", content)) >= min_chars


def extract_field(master_data: str, label: str) -> str:
    m = re.search(rf"^\s*-?\s*{re.escape(label)}:\s*(.+)$", master_data, re.MULTILINE)
    return m.group(1).strip() if m else ""


def parse_master_bullets(master_data: str, heading: str) -> List[str]:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(master_data)
    if not m:
        return []
    return [item.strip() for item in re.findall(r"^-\s+(.+)$", m.group("body"), re.MULTILINE)]


def safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if c in invalid else c for c in name).strip()
    return cleaned or "Resume"


def resolve_template_file(settings: GeneratorSettings) -> Path:
    requested = settings.selected_template_name.strip()
    if not requested:
        raise RuntimeError("No template selected. Choose one in Settings.")
    candidates = [requested]
    if not requested.lower().endswith(".typ"):
        candidates.append(f"{requested}.typ")
    for candidate in candidates:
        path = settings.templates_root / candidate
        if path.exists():
            return path
    available = sorted(p.name for p in settings.templates_root.glob("*.typ"))
    raise RuntimeError(
        f"Template '{settings.selected_template_name}' not found in {settings.templates_root}. "
        f"Available: {', '.join(available) or 'none'}"
    )


def load_template_guide(template_file: Path) -> str:
    guide_path = template_file.parent / f"{template_file.stem}_guide.md"
    if guide_path.exists():
        return guide_path.read_text(encoding="utf-8")
    return ""


def extract_placeholders(template_text: str) -> List[str]:
    found = sorted(set(PLACEHOLDER_PATTERN.findall(template_text)))
    if not found:
        raise ValueError("No {{PLACEHOLDER}} tokens found in template.")
    return found


def build_schema_model(placeholders: Sequence[str]) -> type[BaseModel]:
    fields = {name: (str, ...) for name in placeholders}
    return cast(type[BaseModel], create_model("ResumeSections", __base__=_ResumeBase, **fields))


def sanitize_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"```[a-z]*\n?", "", cleaned).replace("```", "").strip()
    cleaned = cleaned.replace("\\n", "\n")
    return cleaned


def render_template(template_text: str, values: Dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", sanitize_value(value))
    return rendered


def build_profile_photo_block(settings: GeneratorSettings, output_dir: Path) -> str:
    if settings.profile_photo_file is None or not settings.profile_photo_file.exists():
        return ""
    ext = settings.profile_photo_file.suffix
    target_name = f"profile_photo{ext}"
    shutil.copy2(settings.profile_photo_file, output_dir / target_name)
    return target_name


def build_static_placeholders(settings: GeneratorSettings, master_data: str, output_dir: Path) -> Dict[str, str]:
    return {
        "FULL_NAME": extract_field(master_data, "Name") or extract_field(master_data, "Full Name") or "Your Name",
        "EMAIL_ADDRESS": extract_field(master_data, "Email") or "you@example.com",
        "LINKEDIN_URL": extract_field(master_data, "LinkedIn") or "",
        "GITHUB_URL": extract_field(master_data, "GitHub") or "",
        "LOCATION": extract_field(master_data, "Location") or "",
        "PROFILE_PHOTO_PATH": build_profile_photo_block(settings, output_dir),
        "PORTFOLIO_NOTE": "Full project portfolio and references available upon request.",
    }


def build_resume_prompt(
    placeholders: Sequence[str],
    master_data: str,
    application_text: str,
    company_research: str,
    template_guide: str = "",
) -> str:
    placeholder_block = "\n".join(f"- {name}" for name in placeholders)
    constraints: List[str] = []
    for name in placeholders:
        if name == "TAILORED_PROFILE":
            constraints.append(f"- {name}: 2-4 sentences, no bullet points, first-person, evidence-backed and role-specific.")
        elif "COURSEWORK" in name:
            constraints.append(f"- {name}: 4-5 subjects max. Mark in parentheses after each name. Typst list using `- ` syntax.")
        elif "PROJECTS" in name:
            constraints.append(f"- {name}: 2-4 projects. Use #project() helper for each. Concrete tools and outcomes.")
        elif "EXPERIENCE" in name:
            constraints.append(f"- {name}: Use #job() helper for each entry. Most relevant only. Exclude YouTube role (rendered separately).")
        elif "SKILLS" in name:
            constraints.append(f"- {name}: Use #skill-group() helpers. Role-relevant technical skills only. No soft skills.")
        elif "CERTIFICATIONS" in name:
            constraints.append(f"- {name}: Use #cert() helper. Minimum 3 items when source data supports it.")
        elif "BULLET" in name:
            constraints.append(f"- {name}: Exactly one sentence. Quantified. Plain text — no Typst helper functions.")
        else:
            constraints.append(f"- {name}: Concise Typst content fragment.")
    guide_section = f"\nTemplate helper reference:\n---\n{template_guide}\n---\n" if template_guide else ""
    return f"""You are generating Typst-ready section content for a resume template.
Return data ONLY through the structured JSON response schema.
Do not output markdown, code fences, commentary, or any text outside schema values.

Universal rules:
1. Produce exactly one string value for each schema key.
2. Every value must be a valid Typst content fragment for direct insertion.
3. Do not include {{{{PLACEHOLDER}}}} tokens in output values.
4. Do not invent achievements not present in the source data.
5. Escape a literal # as \\# in text content.
6. Use -- for en-dash in date ranges.
7. Do not repeat the same claim across multiple fields unless central to role fit.
8. Coursework must include marks beside subject names.
9. Never produce #set, #show, #import, or #let in any fragment.
10. Never use Markdown formatting in any value.
11. Use only helper functions documented in the template guide.
{guide_section}
Per-placeholder constraints:
{chr(10).join(constraints)}

Placeholders to fill:
{placeholder_block}

Source data (master portfolio):
---
{master_data}
---

Target job description:
---
{application_text}
---

Company research:
---
{company_research or "No company research available."}
---""".strip()


def build_company_research_query(job: JobSpec) -> str:
    role_line = f"Role hint: {job.role_hint}\n" if job.role_hint else ""
    return f"""Research the company {job.company_name}.
{role_line}
Produce a concise markdown brief covering:
1. Company self-description
2. External perspective and candidate context
3. Internship or graduate-role expectations
4. Relevant technical domains, stacks, and tools
5. ATS keywords worth echoing when genuinely evidenced
6. Brand and tone — including one primary accent colour (hex) and one soft tint (hex)

Keep the brief under 600 words.""".strip()


def call_structured_model(
    client: genai.Client,
    model_name: str,
    prompt: str,
    schema_model: type[BaseModel],
    rate_limiter: ApiRateLimiter,
    progress: Optional[Callable[[str, str], None]] = None,
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
        progress=progress,
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
    progress: Optional[Callable[[str, str], None]] = None,
) -> str:
    _log = progress or (lambda m, l: print(m))
    if job.company_research_file.exists():
        existing = read_text(job.company_research_file)
        if has_minimum_content(existing):
            return existing.strip()
    if not settings.enable_company_research:
        return ""
    _log(f"  Researching {job.company_name} via Gemini web search…", "info")
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
        progress=progress,
    )
    text = getattr(response, "text", None) or ""
    if text:
        write_text(job.company_research_file, text.strip() + "\n")
    return text.strip()


def normalize_model_sections(model_data: Dict[str, str], master_data: str) -> Dict[str, str]:
    norm = dict(model_data)
    for key in ("YOUTUBE_BULLET_1", "YOUTUBE_BULLET_2", "YOUTUBE_BULLET_3"):
        if key in norm:
            val = norm[key]
            val = re.sub(r"17\s+minimum viable products?\s+for\s+filmed engineering builds?", "10 filmed engineering builds", val, flags=re.IGNORECASE)
            val = re.sub(r"17\s+minimum viable products?", "10 builds", val, flags=re.IGNORECASE)
            norm[key] = val
    if "TARGETED_CERTIFICATIONS" in norm:
        cert_text = norm["TARGETED_CERTIFICATIONS"]
        cert_count = cert_text.count("#cert(")
        if cert_count < 3:
            fallback = parse_master_bullets(master_data, "Section E — Certifications and Licences")
            extra_certs: List[str] = []
            for item in fallback:
                year_m = re.search(r"\((\d{4})\)", item)
                year = year_m.group(1) if year_m else ""
                name_clean = re.sub(r"\s*\(\d{4}\)", "", item).strip()
                entry = f'#cert(name: "{name_clean}", year: "{year}")'
                if entry not in cert_text:
                    extra_certs.append(entry)
            if extra_certs:
                needed = 3 - cert_count
                norm["TARGETED_CERTIFICATIONS"] = cert_text.rstrip() + "\n" + "\n".join(extra_certs[:needed])
    return norm


def filter_model_data(placeholders: Sequence[str], model_data: Dict[str, str]) -> Dict[str, str]:
    expected = set(placeholders)
    return {k: v for k, v in model_data.items() if k in expected}


def validate_key_parity(
    placeholders: Sequence[str],
    model_data: Dict[str, str],
    progress: Optional[Callable[[str, str], None]] = None,
) -> None:
    _log = progress or (lambda m, l: print(m))
    expected = set(placeholders)
    actual = set(model_data.keys())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        _log(f"  Warning: AI did not fill: {', '.join(missing)}", "warning")
    if extra:
        _log(f"  Warning: AI returned unexpected keys: {', '.join(extra)}", "warning")
    for key in missing:
        model_data[key] = ""


def load_manual_sections(path: Path) -> Dict[str, str]:
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        raise ValueError(f"Manual sections file must be a JSON object: {path}")
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError(f"All keys and values must be strings: {path}")
    return dict(data)


def parse_output_folder(folder: Path) -> OutputFolderRecord:
    m = OUTPUT_DIR_PATTERN.match(folder.name)
    if m:
        return OutputFolderRecord(logical_name=m.group("name"), path=folder, batch=int(m.group("batch")), index=int(m.group("index")))
    return OutputFolderRecord(logical_name=folder.name, path=folder, batch=1, index=1)


def collect_output_folders(outputs_root: Path) -> List[OutputFolderRecord]:
    if not outputs_root.exists():
        return []
    records = [parse_output_folder(p) for p in outputs_root.iterdir() if p.is_dir()]
    records.sort(key=lambda r: (r.batch, r.index, r.logical_name.lower()))
    return records


def _rename_paths(rename_map: Dict[Path, Path]) -> None:
    if not rename_map:
        return
    temp_map: Dict[Path, Path] = {}
    for idx, src in enumerate(rename_map):
        tmp = src.with_name(f".__tmp_{idx}__ {src.name}")
        src.rename(tmp)
        temp_map[tmp] = rename_map[src]
    for tmp, dst in temp_map.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp.rename(dst)


def bump_non_current_output_folders(outputs_root: Path, current_job_names: Sequence[str]) -> None:
    current_set = {name.lower() for name in current_job_names}
    rename_map: Dict[Path, Path] = {}
    for record in collect_output_folders(outputs_root):
        if record.logical_name.lower() in current_set:
            continue
        new_batch = min(record.batch + 1, 99)
        new_name = f"{new_batch:02d}-{record.index:02d} {record.logical_name}"
        if record.path.name != new_name:
            rename_map[record.path] = record.path.with_name(new_name)
    _rename_paths(rename_map)


def ensure_current_output_folder(outputs_root: Path, logical_name: str, batch_index: int) -> Path:
    desired_name = f"01-{batch_index:02d} {logical_name}"
    desired_path = outputs_root / desired_name
    existing: Optional[Path] = None
    for record in collect_output_folders(outputs_root):
        if record.logical_name.lower() == logical_name.lower():
            existing = record.path
            break
    if existing is None:
        desired_path.mkdir(parents=True, exist_ok=True)
        return desired_path
    if existing != desired_path:
        _rename_paths({existing: desired_path})
    desired_path.mkdir(parents=True, exist_ok=True)
    return desired_path


def next_archive_version(archive_dir: Path) -> int:
    highest = 0
    if archive_dir.exists():
        for p in archive_dir.iterdir():
            if p.is_file():
                m = ARCHIVE_VERSION_PATTERN.search(p.name)
                if m:
                    highest = max(highest, int(m.group("version")))
    return highest + 1


def archive_existing_artifacts(job_output_dir: Path, resume_title: str) -> None:
    safe_title = safe_filename(resume_title)
    candidates = [job_output_dir / f"{safe_title}.typ", job_output_dir / f"{safe_title}.pdf", job_output_dir / "sections.json"]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return
    archive_dir = job_output_dir / "ARCHIVE"
    archive_dir.mkdir(parents=True, exist_ok=True)
    version = next_archive_version(archive_dir)
    for p in existing:
        shutil.move(str(p), str(archive_dir / f"{p.stem} V{version}{p.suffix}"))


def enforce_clean_output_contents(job_output_dir: Path, resume_title: str) -> None:
    safe_title = safe_filename(resume_title)
    allowed_files = {f"{safe_title}.typ", f"{safe_title}.pdf", "sections.json"}
    allowed_dirs = {"ARCHIVE"}
    photo_exts = {".jpg", ".jpeg", ".png", ".webp"}
    for p in job_output_dir.iterdir():
        if p.is_file():
            if p.name in allowed_files or p.suffix.lower() in photo_exts:
                continue
            p.unlink(missing_ok=True)
        elif p.is_dir() and p.name not in allowed_dirs:
            shutil.rmtree(p, ignore_errors=True)


def resolve_typst_binary(typst_binary_path: str) -> str:
    if typst_binary_path:
        p = Path(typst_binary_path)
        if p.exists():
            return str(p)
        raise RuntimeError(f"Typst binary not found at configured path: {typst_binary_path}\nUpdate the Typst Binary Path in Settings.")
    found = shutil.which("typst")
    if found:
        return found
    raise RuntimeError(
        "Typst binary not found on PATH and no custom path is configured.\n"
        "Download from https://github.com/typst/typst/releases and place on PATH,\n"
        "or set the Typst Binary Path in the Settings tab."
    )


def run_typst_compile(typst_bin: str, typ_file: Path, pdf_file: Path, output_dir: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        [typst_bin, "compile", str(typ_file), str(pdf_file), "--root", str(output_dir)],
        cwd=output_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def parse_job_name(folder_name: str) -> tuple[str, str]:
    parts = [p.strip() for p in folder_name.split(" - ", 1)]
    return (parts[0], parts[1]) if len(parts) == 2 else (folder_name.strip(), "")


def discover_jobs(applications_root: Path) -> List[JobSpec]:
    jobs: List[JobSpec] = []
    for current_root, dirs, _ in os.walk(applications_root, topdown=True):
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_APPLICATION_DIRS]
        current_dir = Path(current_root)
        if current_dir == applications_root:
            continue
        jd_file = current_dir / "job_description.md"
        if not jd_file.exists():
            continue
        company_name, role_hint = parse_job_name(current_dir.name)
        manual: Optional[Path] = None
        for candidate in (current_dir / "sections_override.json", current_dir / "sections.json"):
            if candidate.exists():
                manual = candidate
                break
        jobs.append(JobSpec(
            job_name=current_dir.name,
            company_name=company_name,
            role_hint=role_hint,
            folder=current_dir,
            job_description_file=jd_file,
            company_research_file=current_dir / "company_research.md",
            manual_sections_file=manual,
        ))
    jobs.sort(key=lambda j: j.job_name.lower())
    return jobs


def ensure_supporting_structure(settings: GeneratorSettings) -> None:
    template_dir = settings.applications_root / "COMPANY_NAME - JOB_NAME"
    write_text(template_dir / "README.md", DEFAULT_JOB_TEMPLATE_README)
    for fname in ("job_description.md", "company_research.md"):
        p = template_dir / fname
        if not p.exists():
            write_text(p, "")
    write_text(settings.applications_root / "ARCHIVE" / "README.md", DEFAULT_ARCHIVE_README)
    write_text(settings.applications_root / "UNSTAGED" / "README.md", DEFAULT_ARCHIVE_README)
    if settings.profile_photo_file is not None:
        gitkeep = settings.profile_photo_file.parent / ".gitkeep"
        if not gitkeep.exists():
            write_text(gitkeep, "")


def process_job(
    client: genai.Client,
    settings: GeneratorSettings,
    master_data: str,
    template_text: str,
    template_guide: str,
    job: JobSpec,
    output_dir: Path,
    rate_limiter: ApiRateLimiter,
    force_regenerate: bool = False,
    progress: Optional[Callable[[str, str], None]] = None,
) -> None:
    _log = progress or (lambda m, l: print(m))
    archive_existing_artifacts(output_dir, settings.resume_title)
    static_values = build_static_placeholders(settings, master_data, output_dir)
    static_template = render_template(template_text, static_values)
    placeholders = extract_placeholders(static_template)

    override_path = job.folder / "sections_override.json"
    cache_path = output_dir / "sections.json"

    if override_path.exists():
        _log("  Using manual sections_override.json — skipping AI.", "info")
        model_data = load_manual_sections(override_path)
    elif cache_path.exists() and not force_regenerate:
        _log("  Using cached sections.json — skipping AI.", "info")
        model_data = load_manual_sections(cache_path)
    else:
        application_text = read_text(job.job_description_file)
        company_research = maybe_generate_company_research(client, settings, job, rate_limiter, progress)
        _log("  Calling Gemini for resume generation…", "info")
        prompt = build_resume_prompt(placeholders, master_data, application_text, company_research, template_guide)
        schema_model = build_schema_model(placeholders)
        model_data = call_structured_model(client, settings.model_name, prompt, schema_model, rate_limiter, progress)

    model_data = filter_model_data(placeholders, model_data)
    model_data = normalize_model_sections(model_data, master_data)
    validate_key_parity(placeholders, model_data, progress)
    write_json(cache_path, model_data)

    safe_title = safe_filename(settings.resume_title)
    typ_path = output_dir / f"{safe_title}.typ"
    pdf_path = output_dir / f"{safe_title}.pdf"
    rendered = render_template(static_template, model_data)
    write_text(typ_path, rendered)

    if not settings.compile_pdf:
        enforce_clean_output_contents(output_dir, settings.resume_title)
        return

    typst_bin = resolve_typst_binary(settings.typst_binary_path)
    _log("  Compiling PDF with Typst…", "info")
    code, stdout, stderr = run_typst_compile(typst_bin, typ_path, pdf_path, output_dir)
    if code != 0:
        stdout_lines = [l for l in stdout.splitlines() if l.strip()]
        stderr_lines = [l for l in stderr.splitlines() if l.strip()]
        enforce_clean_output_contents(output_dir, settings.resume_title)
        raise RuntimeError(
            f"Typst compilation failed for {job.job_name}.\n"
            f"stdout:\n{chr(10).join(stdout_lines[-40:]) or '(none)'}\n\n"
            f"stderr:\n{chr(10).join(stderr_lines[-25:]) or '(none)'}"
        )
    if not pdf_path.exists():
        enforce_clean_output_contents(output_dir, settings.resume_title)
        raise RuntimeError(f"Compilation succeeded but PDF not produced for {job.job_name}.")
    enforce_clean_output_contents(output_dir, settings.resume_title)


def run_batch(
    settings: GeneratorSettings,
    api_key: str,
    job_names: Optional[List[str]] = None,
    force_regenerate: bool = False,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    cancel_flag: Optional[list] = None,
) -> None:
    """
    Run the resume generation batch.

    Args:
        settings:          All persisted configuration (does NOT contain api_key).
        api_key:           Gemini API key — passed directly, never written to disk.
        job_names:         If provided, only process these job folder names.
        force_regenerate:  Ignore existing sections.json cache.
        progress_callback: Optional (message, level) -> None for GUI progress.
        cancel_flag:       Mutable list; set cancel_flag[0] = True to stop after current job.
    """
    _log = progress_callback or (lambda m, l: print(m))
    ensure_supporting_structure(settings)
    settings.outputs_root.mkdir(parents=True, exist_ok=True)

    all_jobs = discover_jobs(settings.applications_root)
    if not all_jobs:
        raise RuntimeError(
            f"No job_description.md files found under {settings.applications_root}. "
            "Create an application folder: applications/COMPANY_NAME - ROLE/"
        )

    if job_names is not None:
        job_name_set = {n.lower() for n in job_names}
        jobs = [j for j in all_jobs if j.job_name.lower() in job_name_set]
    else:
        jobs = all_jobs

    if not jobs:
        raise RuntimeError("No matching jobs found for the selected names.")

    bump_non_current_output_folders(settings.outputs_root, [j.job_name for j in jobs])

    if not api_key or not api_key.strip():
        raise RuntimeError("No API key provided. Enter your Gemini API key in the Generate tab.")

    client = genai.Client(api_key=api_key.strip())
    rate_limiter = ApiRateLimiter(settings.api_call_delay_seconds)
    master_data = read_text(settings.master_portfolio_file)
    template_file = resolve_template_file(settings)
    template_text = template_file.read_text(encoding="utf-8")
    template_guide = load_template_guide(template_file)

    _log(f"Starting batch: {len(jobs)} job(s) to process.", "info")
    for index, job in enumerate(jobs, start=1):
        if cancel_flag and cancel_flag[0]:
            _log("Batch cancelled by user.", "warning")
            break
        _log(f"[{index}/{len(jobs)}] {job.job_name}", "info")
        try:
            output_dir = ensure_current_output_folder(settings.outputs_root, job.job_name, index)
            process_job(
                client=client,
                settings=settings,
                master_data=master_data,
                template_text=template_text,
                template_guide=template_guide,
                job=job,
                output_dir=output_dir,
                rate_limiter=rate_limiter,
                force_regenerate=force_regenerate,
                progress=_log,
            )
            _log(f"  Done \u2713 \u2192 {output_dir.name}", "success")
        except Exception as exc:
            _log(f"  Error processing {job.job_name}: {exc}", "error")

    _log("Batch complete.", "success")
