# Resume Generator (Gemini + LaTeX)

A reusable Python pipeline that turns your portfolio data plus a target application into a tailored LaTeX resume and compiled PDF.

## What this repo gives you
- Structured resume generation with `google-genai` using `gemini-2.5-flash`.
- Strict JSON output via Pydantic schema keys that match your template placeholders.
- Generic template support: bring any `.tex` template that uses `{{PLACEHOLDER}}` tokens.
- Automatic output of both `.tex` and `.pdf` in a dedicated run folder.
- Prompt pack to help users gather company research and normalize project portfolios.

## Repository layout
- `generate_resume.py`: CLI pipeline.
- `requirements.txt`: Python dependencies.
- `data/master_portfolio.md`: static profile, metrics, experience, and projects source.
- `templates/template.tex`: AltaCV starter template with required placeholders.
- `applications/`: target job descriptions and optional company-research notes.
- `outputs/`: generated run artifacts.
- `prompts/`: reusable prompt-engineering assets.

## Quickstart

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Set your API key (easy local-file option)
The script supports two ways to provide your key.

Recommended beginner option (local file):
1. Copy `secrets/gemini_api_key.template.txt` to `secrets/gemini_api_key.txt`
2. Paste your raw key on one line in `secrets/gemini_api_key.txt`
3. Run the script normally

Security notes:
- `secrets/gemini_api_key.txt` is ignored by git in `.gitignore`.
- Never paste your real key into tracked files like `README.md` or source code.
- If a key is exposed, revoke and regenerate it in Google AI Studio.

Alternative option (environment variable):
The script first checks `GEMINI_API_KEY` in your environment.

Where to get a free key:
1. Go to https://aistudio.google.com
2. Sign in.
3. Open API key management.
4. Create key.
5. Export it locally.

PowerShell example:
```powershell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
```

Persistent PowerShell option (survives new terminals):
```powershell
setx GEMINI_API_KEY "YOUR_KEY_HERE"
```

After `setx`, open a new terminal before running the script.

### 3) Add your inputs
- Edit `data/master_portfolio.md` with your profile and projects.
- Put the target application text in `applications/`.
- Optionally add manual company research notes in `applications/`.

### 4) Run generation
```bash
python generate_resume.py applications/example_job_description.txt
```

Optional arguments:
- `--template templates/template.tex`
- `--master-data data/master_portfolio.md`
- `--company-research applications/example_company_research.md`
- `--compiler xelatex` (or `pdflatex`)
- `--run-name company_role`
- `--no-compile` (generate `.tex` + `sections.json` only)
- `--api-key-file secrets/gemini_api_key.txt`

Example with research file and compile skipped:
```bash
python generate_resume.py applications/example_job_description.txt --company-research applications/example_company_research.md --run-name example_robotics --no-compile
```

## Output behavior
Each run creates `outputs/<run_name>/` containing:
- `resume.tex`
- `resume.pdf`
- `sections.json` (model output)
- `compile.stdout.log`
- `compile.stderr.log`

If `--no-compile` is used, only `resume.tex` and `sections.json` are created.

## Template modularity
This pipeline is template-agnostic.

Rules for any custom template:
1. Use double-curly placeholders like `{{TAILORED_PROFILE}}`.
2. Keep placeholders as content slots, not style commands.
3. Ensure all placeholders can be represented as string fields in JSON.

The script automatically:
- scans placeholders,
- builds a strict Pydantic schema,
- enforces key parity,
- injects returned values into the LaTeX template.

## Prompt pack
- `prompts/company_research_prompt.md`
- `prompts/template_conversion_prompt.md`
- `prompts/section_tailoring_prompt.md`
- `prompts/project_portfolio_normalizer_prompt.md`

The portfolio normalizer prompt lets users paste rough project notes and outputs a consistent project catalog markdown format for reliable resume generation.

## Notes and limitations
- Free Gemini API workflows may not include web browsing. Use manual research and paste notes into a file.
- You need a local LaTeX distribution (TeX Live or MiKTeX) with the selected compiler available on PATH.
- If compilation fails, inspect the compile logs in the run folder.

## Publish-ready usage flow for friends and classmates
1. Clone repo.
2. Set API key.
3. Fill `data/master_portfolio.md`.
4. Drop job description into `applications/`.
5. Run one command.
6. Collect `.tex` and `.pdf` from `outputs/<run>/`.
