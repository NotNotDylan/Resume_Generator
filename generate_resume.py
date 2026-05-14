import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from google import genai
from google.genai import types
from pydantic import BaseModel, create_model

PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


@dataclass
class RunConfig:
    application_file: Path
    template_file: Path
    master_portfolio_file: Path
    company_research_file: Path | None
    output_root: Path
    run_name: str
    compiler: str
    model_name: str
    no_compile: bool
    api_key_file: Path


class StrictModel(BaseModel):
    pass


def resolve_cli_path(raw_path: str, base_dir: str | None = None) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.resolve()

    direct = candidate.resolve()
    if direct.exists() or base_dir is None:
        return direct

    fallback = (Path(base_dir) / candidate).resolve()
    return fallback


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(
        description="Generate a tailored LaTeX resume using Gemini structured outputs."
    )
    parser.add_argument(
        "application_file",
        help="Path to the target application text file under applications/.",
    )
    parser.add_argument(
        "--template",
        default="templates/template.tex",
        help="Path to a LaTeX template containing {{PLACEHOLDER}} tokens.",
    )
    parser.add_argument(
        "--master-data",
        default="data/master_portfolio.md",
        help="Path to the static portfolio data markdown file.",
    )
    parser.add_argument(
        "--company-research",
        default=None,
        help="Optional path to manual company research notes.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where per-run output folders are created.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Optional run name. If omitted, one is generated from timestamp and application file stem.",
    )
    parser.add_argument(
        "--compiler",
        default="xelatex",
        choices=["xelatex", "pdflatex"],
        help="LaTeX compiler to use for PDF build.",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Google model name to use.",
    )
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Skip LaTeX compilation and only write resume.tex + sections.json.",
    )
    parser.add_argument(
        "--api-key-file",
        default="secrets/gemini_api_key.txt",
        help="Local file containing your Gemini API key on one line (ignored by git by default).",
    )

    args = parser.parse_args()

    application_file = resolve_cli_path(args.application_file, base_dir="applications")
    template_file = resolve_cli_path(args.template)
    master_file = resolve_cli_path(args.master_data)
    company_file = (
        resolve_cli_path(args.company_research, base_dir="applications")
        if args.company_research
        else None
    )
    output_root = resolve_cli_path(args.output_dir)
    api_key_file = resolve_cli_path(args.api_key_file)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_run_name = f"{application_file.stem}_{timestamp}"

    return RunConfig(
        application_file=application_file,
        template_file=template_file,
        master_portfolio_file=master_file,
        company_research_file=company_file,
        output_root=output_root,
        run_name=args.run_name or generated_run_name,
        compiler=args.compiler,
        model_name=args.model,
        no_compile=args.no_compile,
        api_key_file=api_key_file,
    )


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def read_api_key_from_file(path: Path) -> str:
    if not path.exists():
        return ""

    raw = read_text(path)
    for line in raw.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
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


def ensure_applications_path(path: Path) -> None:
    expected_parent = Path("applications").resolve()
    try:
        path.relative_to(expected_parent)
    except ValueError as exc:
        raise ValueError(
            f"application_file must be under {expected_parent}, got: {path}"
        ) from exc


def extract_placeholders(template_text: str) -> List[str]:
    found = PLACEHOLDER_PATTERN.findall(template_text)
    unique_sorted = sorted(set(found))
    if not unique_sorted:
        raise ValueError("No placeholders found. Add tokens like {{TAILORED_PROFILE}}.")
    return unique_sorted


def build_schema_model(placeholders: List[str]) -> type[BaseModel]:
    fields = {name: (str, ...) for name in placeholders}
    return create_model("ResumeSections", __base__=StrictModel, **fields)


def build_prompt(
    placeholders: List[str],
    master_data: str,
    application_text: str,
    company_research: str | None,
) -> str:
    placeholder_block = "\n".join(f"- {name}" for name in placeholders)
    research_block = company_research.strip() if company_research else "No research file provided."

    keyed_constraints: List[str] = []
    for name in placeholders:
        if "PROFILE" in name:
            keyed_constraints.append(f"- {name}: 2-4 sentences, no bullet list.")
        elif "EXPERIENCE" in name:
            keyed_constraints.append(
                f"- {name}: LaTeX list/event fragments only, 3-7 bullets total, each bullet one concise sentence."
            )
        elif "PROJECT" in name:
            keyed_constraints.append(
                f"- {name}: 2-4 project entries maximum, each with concrete tools and one measurable outcome."
            )
        elif "COURSEWORK" in name:
            keyed_constraints.append(f"- {name}: 6-8 relevant items, strongest relevance first.")
        elif "CERTIFICATION" in name:
            keyed_constraints.append(f"- {name}: 3-6 role-relevant certifications, concise formatting.")
        elif "SKILL" in name:
            keyed_constraints.append(f"- {name}: role-focused tags only, omit unrelated skills.")
        elif "BULLET" in name:
            keyed_constraints.append(f"- {name}: exactly one bullet sentence with quantified or specific detail.")
        else:
            keyed_constraints.append(f"- {name}: concise LaTeX-safe content fragment.")

    keyed_constraints_block = "\n".join(keyed_constraints)

    return f"""
You are generating LaTeX-ready section content for a resume template.
Return data ONLY through the structured response schema. Do not output markdown.

Rules:
1) Produce exactly one string value for each placeholder key.
2) Each value must be valid LaTeX fragment content for insertion.
3) Do not include surrounding placeholder braces in values.
4) Do not invent achievements not supported by source data.
5) Keep output concise and role-focused.
6) Escape LaTeX-sensitive characters when needed: %, &, _, #.
7) Never include code fences, YAML, XML, or commentary.
8) Do not repeat the same claim across multiple fields unless context requires it.

Per-placeholder constraints:
{keyed_constraints_block}

Placeholders to fill:
{placeholder_block}

Static profile data source:
---
{master_data}
---

Target application text:
---
{application_text}
---

Manual company research notes:
---
{research_block}
---
""".strip()


def call_model(
    client: genai.Client,
    model_name: str,
    prompt: str,
    schema_model: type[BaseModel],
) -> Dict[str, str]:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=schema_model,
        ),
    )

    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        if isinstance(parsed, BaseModel):
            return parsed.model_dump()
        if isinstance(parsed, dict):
            return parsed

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Model returned no parsable content.")

    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("Structured output was not a JSON object.")
    return data


def sanitize_model_output(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.replace("```latex", "").replace("```", "").strip()
    return cleaned


def validate_key_parity(placeholders: List[str], model_data: Dict[str, str]) -> None:
    expected = set(placeholders)
    actual = set(model_data.keys())

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing or extra:
        lines = ["Placeholder/schema mismatch detected."]
        if missing:
            lines.append(f"Missing keys: {', '.join(missing)}")
        if extra:
            lines.append(f"Unexpected keys: {', '.join(extra)}")
        raise ValueError("\n".join(lines))


def render_template(template_text: str, model_data: Dict[str, str]) -> str:
    rendered = template_text
    for key, value in model_data.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", sanitize_model_output(value))
    return rendered


def run_compile(compiler: str, tex_file: Path, working_dir: Path) -> Tuple[int, str, str]:
    if shutil.which(compiler) is None:
        raise RuntimeError(
            f"Compiler '{compiler}' not found on PATH. Install TeX Live or MiKTeX and retry."
        )

    cmd = [
        compiler,
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_file.name,
    ]

    completed = subprocess.run(
        cmd,
        cwd=working_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    return completed.returncode, completed.stdout, completed.stderr


def write_json(path: Path, data: Dict[str, str]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    config = parse_args()

    ensure_applications_path(config.application_file)

    template_text = read_text(config.template_file)
    master_data = read_text(config.master_portfolio_file)
    application_text = read_text(config.application_file)
    company_research = (
        read_text(config.company_research_file) if config.company_research_file else None
    )

    placeholders = extract_placeholders(template_text)
    schema_model = build_schema_model(placeholders)
    prompt = build_prompt(placeholders, master_data, application_text, company_research)

    api_key = resolve_api_key(config.api_key_file)
    client = genai.Client(api_key=api_key)
    model_data = call_model(client, config.model_name, prompt, schema_model)
    validate_key_parity(placeholders, model_data)

    output_dir = config.output_root / config.run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    write_json(output_dir / "sections.json", model_data)

    rendered_tex = render_template(template_text, model_data)
    rendered_tex_path = output_dir / "resume.tex"
    rendered_tex_path.write_text(rendered_tex, encoding="utf-8")

    print("Resume generation complete.")
    print(f"Run directory: {output_dir}")
    print(f"LaTeX file: {rendered_tex_path}")

    if config.no_compile:
        print("PDF compilation skipped (--no-compile set).")
        return

    code, stdout, stderr = run_compile(config.compiler, rendered_tex_path, output_dir)
    (output_dir / "compile.stdout.log").write_text(stdout, encoding="utf-8")
    (output_dir / "compile.stderr.log").write_text(stderr, encoding="utf-8")

    if code != 0:
        raise RuntimeError(
            "LaTeX compilation failed. Inspect compile.stdout.log and compile.stderr.log in "
            f"{output_dir}"
        )

    generated_pdf = output_dir / "resume.pdf"
    if not generated_pdf.exists():
        raise RuntimeError("Compilation finished but resume.pdf was not created.")

    print(f"PDF file: {generated_pdf}")


if __name__ == "__main__":
    main()
