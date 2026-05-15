# Resume Generator (Gemini + LaTeX)

This repo generates tailored LaTeX resumes in batch from job folders under applications.
The workflow is driven by main.py rather than command-line flags.

## Core workflow
1. Put your API key in secrets/gemini_api_key.txt.
2. Configure settings at the top of main.py.
3. Fill data/master_portfolio.md with your personal master data.
4. Create one folder per job under applications.
5. Run python main.py.

## Easiest PDF setup (Windows)
If you want automatic PDF output from LaTeX, run this once:
```powershell
./install_latex.ps1
```
Then close and reopen PowerShell and run:
```powershell
python main.py
```

What this does:
- Installs MiKTeX using winget.
- Lets the generator use xelatex/pdflatex for PDF creation.

If you skip this install:
- The generator still creates .tex and sections.json.
- PDF output is skipped until a LaTeX engine is available.

## Key links
- Free Google API key quickstart: https://ai.google.dev/gemini-api/docs/api-key
- Gemini API docs and capabilities: https://ai.google.dev/gemini-api/docs

## Local API key file
Recommended local-only setup:
1. Copy secrets/gemini_api_key.template.txt to secrets/gemini_api_key.txt
2. Paste your raw API key on one line
3. Keep that file local only

The repo ignores secrets/gemini_api_key.txt in git.

One-time terminal alternative:
```powershell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
```

Persistent Windows user environment alternative:
```powershell
setx GEMINI_API_KEY "YOUR_KEY_HERE"
```

Open a new terminal after setx.

## main.py configuration
Use main.py to change:
- selected template name
- model name
- research model name
- whether PDF compilation runs
- compiler choice
- whether web-backed company research generation is enabled
- API throttling delay
- resume title
- profile photo file path

## Applications folder structure
The generator recursively scans applications for job folders.
It ignores folders named ARCHIVE, UNSTAGED, and COMPANY_NAME - JOB_NAME.

Canonical job folder shape:
```text
applications/
  Company Name - Role Title/
    job_description.md
    company_research.md
    sections.json              optional manual override
    sections_override.json     optional manual override
```

The included starter folder is created automatically at:
```text
applications/
  COMPANY_NAME - JOB_NAME/
    README.md
    job_description.md
    company_research.md
```

Folder naming note:
- The generator reads the company name from the folder title by splitting on the first " - ".
- Any text after that is treated as a role hint for more specific research and output naming.

## Manual JSON override
If you paste the AI-generated sections JSON into a job folder as sections.json or sections_override.json, the program skips AI generation for that job and renders the template directly from that JSON.
This is the fastest way to make manual revisions while keeping the rest of the pipeline intact.

## Optional web-backed company research
If enable_company_research_search is true in main.py and company_research.md is missing or empty, the generator can request company research automatically using a Google search-enabled model call.
This is intended for users willing to use a model configuration that supports that workflow.

The company research prompt emphasizes:
- company context
- role-specific expectations
- visual colour theme suggestions
- ATS/recruiter trigger words and keyword cues

## Output behavior
The outputs folder contains one folder per logical job, prefixed as:
```text
XX-YY Job Name
```

Meaning:
- XX = batch age, with the newest generation batch always using 01
- YY = the job index within the newest batch

If an existing job is regenerated:
- its existing output folder is reused and renamed to the newest 01-YY position
- active resume artifacts are archived inside that job output folder under ARCHIVE
- archived files receive a suffix like V1, V2, and so on

New active files do not get V numbers.

## Output files
Each active job output folder contains:
- [resume title].tex
- [resume title].pdf if compile_pdf is enabled and compilation succeeds
- sections.json
- compile.stdout.log when PDF compilation runs
- compile.stderr.log when PDF compilation runs

## Template switching
Put templates in templates and change SELECTED_TEMPLATE_NAME in main.py.
The generator scans placeholders from the chosen template automatically.

## Profile photo
Put a profile photo in assets/profile_photo and point PROFILE_PHOTO_FILE in main.py to it.
The default template places it in the top-right header area.

## Notes
- Relevant coursework selection is expected to show marks beside the chosen subjects.
- The default template includes full LinkedIn and GitHub URLs rather than short handles.
- The default template also includes a note that the full project portfolio and references are available upon request.
- There is no reliable dependency-free way to render a LaTeX template to PDF without a LaTeX engine. If you want PDF output from this template, install MiKTeX or TeX Live.