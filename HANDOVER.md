# Resume Generator — Complete Rebuild Handover

> This document is the single source of truth for recreating this system from scratch.
> No other documentation, source code, or prior context is required.
> Read every section before writing a single line of code.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Core Design Ethos](#2-core-design-ethos)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [The Master Portfolio](#5-the-master-portfolio)
6. [Applications Folder Convention](#6-applications-folder-convention)
7. [The Typst Template System](#7-the-typst-template-system)
8. [The AI Pipeline](#8-the-ai-pipeline)
9. [The GUI Application](#9-the-gui-application)
10. [The Generation Engine](#10-the-generation-engine)
11. [Output Management](#11-output-management)
12. [Settings Reference](#12-settings-reference)
13. [Dependency and Environment Setup](#13-dependency-and-environment-setup)
14. [Prompt Engineering Reference](#14-prompt-engineering-reference)
15. [Error Handling Philosophy](#15-error-handling-philosophy)
16. [Security Considerations](#16-security-considerations)

---

## 1. What This System Does

This is an **AI-powered, batch resume generator** with a polished graphical interface. Its purpose is to produce a unique, highly tailored resume PDF for every job application — automatically — without the candidate having to manually rewrite anything between applications.

The user maintains a single "master portfolio" document that is the authoritative record of everything they have ever done. When they want to apply for a job, they create a folder, paste in the job description, optionally add company research, and press a button. The system uses a large language model (Google Gemini) to read the portfolio and the job description together and write custom resume content for that specific role. That content is injected into a Typst template and compiled into a print-ready PDF.

The whole process — from a blank job folder to a finished PDF — takes under two minutes per application.

**Key outcomes the system must deliver:**

- One master portfolio, unlimited tailored resumes
- Every resume is factually grounded — no hallucinated achievements
- Output PDFs are visually polished and consistent across applications
- Zero terminal usage — everything happens inside the GUI
- The API key is never written to disk; it lives only in memory for the duration of the session

---

## 2. Core Design Ethos

These principles govern every architectural decision. When in doubt, return to them.

### 2.1 Single Source of Truth

The `master_portfolio.md` file is the only place personal information lives. The AI reads it; the GUI reads it; the templates read it. Nothing about the user's history, skills, or identity is stored anywhere else in an editable form. If the user updates their portfolio, every future resume benefits automatically.

### 2.2 Folders Are the Interface (for data entry)

Each job application is a folder inside `applications/`. The folder name encodes the company and role. Two files inside — `job_description.md` and `company_research.md` — are all the AI needs. This is intentional: it is simple, version-controllable, and durable. The GUI provides a way to create and populate these files without touching a file manager, but the underlying storage is always plain files.

### 2.3 The AI Is a Writer, Not a Decision-Maker

Gemini's job is to write Typst-formatted content fragments — not to choose what goes into the resume structurally. The template defines the structure. The master portfolio defines the facts. Gemini's only job is to select, emphasise, and phrase the facts in the most relevant way for the target role.

### 2.4 Templates Are Documents, Not Code

Typst templates use `{{PLACEHOLDER_NAME}}` tokens — double curly braces, uppercase, underscores. These tokens are found by regex, given to the AI as the exact set of fields to fill, and replaced by the AI's output. The template author never writes Python. The Python author never hand-codes template logic.

### 2.5 Reproducibility Through Cached AI Output

After the AI runs for a job, its output is saved to `sections.json` in the output folder. On subsequent runs, if that file exists and the user has not requested a fresh generation, the system skips the API call and re-renders from the cache. This means a re-run to fix a template typo costs zero API calls.

### 2.6 Batch Versioning Is Automatic

The output folder naming system ensures that the newest batch of resumes is always `01-XX`, and older batches are automatically bumped to higher numbers. This keeps the output folder clean and makes it immediately obvious which resumes are newest.

### 2.7 The GUI Owns the Session

The graphical interface is the primary entry point and the only way an end user should interact with this system. There is no separate CLI to maintain. All settings, all triggers, all feedback live in the GUI. The backend engine is a pure Python library; it has no awareness of the GUI and can be called programmatically if needed, but the GUI is the intended interface.

---

## 3. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| GUI | PyQt6 | Mature, cross-platform, native look, rich widget library |
| AI | Google Gemini API (via `google-genai` SDK) | Structured JSON output, web search tool, large context window |
| Typesetting | Typst | Fast, self-contained binary, readable syntax, no dependency hell |
| Template tokens | `{{UPPERCASE_SNAKE}}` regex | Simple, unambiguous, no extra library needed |
| Data schema | Pydantic v2 | Runtime schema construction, validated structured AI output |
| Settings persistence | JSON file (`settings.json`) | Human-readable, easy to hand-edit if needed |
| Python version | 3.11+ | Match-case, tomllib, better type hints |

### Why Typst

Typst is a modern typesetting system built as a purpose-designed alternative to older, heavier document systems. It compiles in milliseconds, produces PDF output directly, has a clean scripting syntax that reads like code, and ships as a single self-contained binary with zero package manager required. Templates written in Typst are easy to read and modify — a template author who knows basic Typst can create or modify a resume template in under an hour.

For this project, Typst is the only typesetter. All templates are `.typ` files. The compilation step calls the `typst compile` binary. There are no class files, no document class inheritance chains, no obscure macro packages. Templates ship as a single `.typ` file with helper functions at the top.

**Typst installation:** download the single binary release from `https://github.com/typst/typst/releases`. No additional packages, fonts, or installers are needed beyond what the template imports at its top level.

**Compilation call:**
```
typst compile "Resume.typ" "Resume.pdf" --root .
```

The `--root .` flag sets the Typst project root to the output folder, allowing the template to reference the profile photo by relative path.

---

## 4. Repository Structure

```
Resume_Generator/
│
├── main.py                         # GUI entry point — run this to launch
├── HANDOVER.md                     # This document
├── README.md                       # Brief user-facing readme
├── settings.json                   # Persisted settings (auto-created, never commit)
│
├── internal/
│   ├── __init__.py
│   ├── generate_resume.py          # Core generation engine (no GUI imports)
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── app.py                  # MainWindow — tabs, toolbar, status bar
│   │   ├── panels/
│   │   │   ├── __init__.py
│   │   │   ├── generate_panel.py   # Generate tab: job list, key, log
│   │   │   ├── jobs_panel.py       # Jobs tab: browse and edit applications
│   │   │   ├── portfolio_panel.py  # Portfolio tab: edit master_portfolio.md
│   │   │   └── settings_panel.py   # Settings tab: all configuration options
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── job_card.py         # Single job row widget with status icon
│   │   │   └── log_view.py         # Colour-coded scrollable log display
│   │   └── styles/
│   │       └── theme.qss           # Qt stylesheet (dark violet theme)
│   ├── data/
│   │   └── master_portfolio.md     # SOURCE OF TRUTH — never auto-generated
│   ├── prompts/
│   │   ├── company_research_prompt.md
│   │   └── section_tailoring_prompt.md
│   ├── profile_photo/
│   │   └── .gitkeep
│   ├── templates/
│   │   ├── modern.typ              # Primary Typst resume template
│   │   └── minimal.typ             # Minimal single-column variant
│   └── requirements.txt
│
├── applications/
│   ├── ARCHIVE/                    # Completed/rejected apps (ignored by engine)
│   │   └── README.md
│   ├── UNSTAGED/                   # In-progress research (ignored by engine)
│   │   └── README.md
│   ├── COMPANY_NAME - JOB_NAME/    # Template folder (ignored by engine)
│   │   ├── README.md
│   │   ├── job_description.md
│   │   └── company_research.md
│   └── Example Corp - Software Engineer/
│       ├── job_description.md      # REQUIRED
│       ├── company_research.md     # Created by AI or written manually
│       └── sections.json           # OPTIONAL — cached AI output or manual override
│
└── outputs/
    └── 01-01 Example Corp - Software Engineer/
        ├── Resume.typ              # Rendered Typst source
        ├── Resume.pdf              # Compiled output
        ├── sections.json           # AI output cache
        ├── profile_photo.jpg       # Copied from internal/profile_photo/
        └── ARCHIVE/
            ├── Resume V1.typ
            └── Resume V1.pdf
```

---

## 5. The Master Portfolio

`internal/data/master_portfolio.md` is the single most important file in the system. It is a structured Markdown document containing the user's complete professional history, skills, education, and projects. The AI reads the entire file for every resume generation. It must be kept comprehensive, accurate, and up to date.

### 5.1 Structure

The document uses a specific heading hierarchy. The engine uses regex to extract individual fields from it.

```markdown
# [Name]'s Resume Master Portfolio

## Section A — Personal Information
- Name: Dylan Smith
- Pronouns: he/him
- Location: Sydney, NSW, Australia
- Email: dylan@example.com
- LinkedIn: linkedin.com/in/dylansmith
- GitHub: github.com/dylansmith
- University: University of Technology Sydney
- Degree: Bachelor of Engineering (Honours)
- Major: Mechatronics
- Expected Graduation: November 2026

### Personal Profile
Two to four sentences that form the base of the tailored profile. The AI will
rephrase and extend this for each specific role, but this is the foundation.

## Section B — Education and Transcript
- Program: Bachelor of Engineering (Honours) — Mechatronics Engineering
- Status: Currently enrolled, Year 3 of 4
- GPA: 6.2 / 7.0
- WAM: 79.4

**Completed Subjects:**
- Introduction to Programming (95)
- Engineering Mechanics (88)
- Embedded Systems (91)
- Signal Processing (84)
- Control Systems (79)

## Section C — Personal Experience Catalogue

### YouTube / Product Development
**I did a thing · YouTube · Part-time**
- Timeline: February 2022 – Present
- Built 17 engineering projects for a YouTube channel with 25,000 subscribers
- Designed and 3D-printed custom enclosures for electronics projects
- Wrote and published detailed technical build logs and tutorials

### Casual Academic
**Casual Academic Tutor · University of Technology Sydney · Casual**
- Timeline: July 2024 – Present
- Supported 120 students across two programming subjects
- Delivered weekly tutorial sessions and provided one-on-one debugging assistance

## Section D — Project Portfolio

# Dylan's Engineering Project Portfolio

## Professional Projects: YouTube Channel
**Overview:** 17 Total | 14 Completed | 10 Published

1. **Autonomous Lawn Mower**
   * **Context:** Personal YouTube project
   * **Description:** Designed and built an autonomous lawn mower using ROS2 and RPLiDAR.
   * **Technical Details:** ROS2 Humble, RPLiDAR A1, Raspberry Pi 4B, Python, Nav2

2. **Custom PCB Motor Driver**
   * **Context:** Personal YouTube project
   * **Description:** Designed a four-channel brushless motor driver from scratch.
   * **Technical Details:** KiCad 7, STM32F4, CAN bus, DRV8313

## Academic Projects: Mechatronics Engineering
### Mechatronics Studio 3
**Robotic Arm Pick-and-Place**
* **Project:** Designed and programmed a 6-DOF robotic arm to sort objects by colour.
* **Context:** Final-year capstone unit, team of 4.
* **Technical Details:** OpenCV, ROS2, Python, custom inverse kinematics solver

## Section E — Certifications and Licences
- PADI Open Water Diver (2019)
- AWS Cloud Practitioner (2023)
- Google IT Support Professional Certificate (2022)

## Section F — Awards
- Dean's List for Academic Excellence, Semester 2 2023
- First Place, UTS Robotics Competition 2024
```

### 5.2 Field Extraction

The engine extracts specific fields from Section A using this regex pattern:
```python
re.search(rf"^\s*-?\s*{re.escape(field_name)}:\s*(.+)$", master_data, re.MULTILINE)
```

Fields extracted automatically (label must match exactly):

| Label in portfolio | Becomes placeholder |
|-------------------|-------------------|
| `Name` | `{{FULL_NAME}}` |
| `Email` | `{{EMAIL_ADDRESS}}` |
| `LinkedIn` | `{{LINKEDIN_URL}}` |
| `GitHub` | `{{GITHUB_URL}}` |
| `Location` | `{{LOCATION}}` |

Section E is extracted by finding the heading and collecting all bullet items beneath it; these form the fallback pool for certifications when the AI's output is sparse.

The full document text is passed verbatim to Gemini for all other content.

---

## 6. Applications Folder Convention

Each job application lives in its own folder inside `applications/`. The folder name is the only metadata — there is no database or index file.

### 6.1 Naming Convention

```
COMPANY_NAME - ROLE_HINT
```

The engine splits on the **first occurrence** of ` - ` (space-hyphen-space). Everything before it is the company name; everything after is the role hint. Both are used in AI prompts and output folder naming.

Valid examples:
```
Google - Software Engineering Intern
Boston Dynamics - Robotics Research Scientist
UTS Human Technology Futures - UX Research Assistant
```

### 6.2 Contents

| File | Required | Purpose |
|------|----------|---------|
| `job_description.md` | **Yes** | The raw job posting, pasted as-is |
| `company_research.md` | No | AI-generated or manually written company brief |
| `sections.json` | No | Cached AI output; if present, skips API call |
| `sections_override.json` | No | Takes precedence over `sections.json`; never overwritten by engine |

If `sections_override.json` exists, the engine uses it unconditionally — it never calls Gemini for that job, and it never overwrites the file. This allows manual tweaking of a specific section without disabling caching for future runs.

### 6.3 Ignored Folders

The engine ignores any folder whose name (case-insensitive) is in this set:
- `archive`
- `unstaged`
- `template`
- `company_name - job_name`

### 6.4 Discovery Order

Jobs are discovered by walking `applications/` one level deep. They are sorted **alphabetically by folder name** before processing. The GUI displays them in this order and allows the user to select a subset for the current run.

---

## 7. The Typst Template System

### 7.1 What a Template Is

A template is a `.typ` file that describes the full visual layout of the resume. It contains all styling, layout logic, helper function definitions, and placeholder tokens where dynamic content is injected.

Placeholder tokens follow this exact convention:
```
{{PLACEHOLDER_NAME}}
```
- Double curly braces on each side
- All uppercase letters and digits
- Words separated by underscores
- No spaces inside braces

The engine locates all placeholders with:
```python
re.findall(r'\{\{([A-Z0-9_]+)\}\}', template_text)
```

### 7.2 Static vs Dynamic Placeholders

**Static placeholders** are filled before the AI is called. Their values come directly from the master portfolio or settings:

| Placeholder | Source |
|-------------|--------|
| `{{FULL_NAME}}` | Section A → Name |
| `{{EMAIL_ADDRESS}}` | Section A → Email |
| `{{LINKEDIN_URL}}` | Section A → LinkedIn |
| `{{GITHUB_URL}}` | Section A → GitHub |
| `{{LOCATION}}` | Section A → Location |
| `{{PROFILE_PHOTO_PATH}}` | Profile photo filename (copied to output dir) |
| `{{PORTFOLIO_NOTE}}` | Static footer string |

**Dynamic placeholders** are everything else still remaining in the template after static substitution. The engine discovers them by scanning the partially-rendered template, then sends that list to Gemini as the exact schema to fill.

### 7.3 Typst Helper Functions

Every template defines helper functions at the top that AI-generated content fragments call. These functions handle spacing, typography, and visual formatting consistently. The AI must only produce calls to these pre-defined functions and plain text content — it must never produce `#set`, `#show`, or any document-level Typst declarations.

Example template helpers:

```typst
// Job entry helper
#let job(title: "", company: "", period: "", body) = [
  #grid(
    columns: (1fr, auto),
    [*#title* \ #text(style: "italic")[#company]],
    [#text(fill: gray)[#period]]
  )
  #body
  #v(0.4em)
]

// Project entry helper
#let project(name: "", tech: "", body) = [
  *#name* #h(0.3em) #text(fill: accent, size: 0.85em)[#tech]
  #body
  #v(0.3em)
]

// Section header helper
#let section(title, body) = [
  #text(fill: accent, weight: "bold", size: 1.05em)[#upper(title)]
  #line(length: 100%, stroke: 0.5pt + accent)
  #v(0.2em)
  #body
  #v(0.5em)
]
```

The AI prompt includes a copy of all helper signatures so it knows exactly which functions are available and what parameters they take.

### 7.4 Typst Injection

Each dynamic placeholder receives a self-contained Typst content fragment. The template defines the visual container; the AI fills in the content.

Example showing the relationship:

```typst
// Template excerpt:
#section("Experience")[
  {{DYNAMIC_EXPERIENCE}}
]

// After AI generation and injection, the placeholder is replaced with:
#section("Experience")[
  #job(title: "Embedded Systems Engineer", company: "Acme Robotics", period: "Jan 2024 – Present")[
    - Designed a custom motor controller achieving 0.1° positional accuracy
    - Reduced firmware boot time by 60% through HAL optimisation
  ]
  #job(title: "Casual Academic", company: "University of Technology Sydney", period: "Jul 2024 – Present")[
    - Supported 120 students across two programming subjects
  ]
]
```

### 7.5 Content Fragment Rules (enforced via prompt)

The AI must follow these rules when generating content fragments for Typst templates:

1. **Never wrap output in triple backticks or any code fence**
2. **Never use Markdown formatting** (no `**bold**`, no `## headings`)
3. **Produce fragments only** — no `#set`, `#show`, `#import`, or document-level declarations
4. **Use only the helper functions defined in the template** — no inventing new Typst functions
5. **Escape `#` if it appears as a literal character** (use `\#`)
6. **Use `--` for en-dash in date ranges** (Typst convention)

### 7.6 Compilation

After all placeholders are injected, the engine saves `Resume.typ` in the output folder and calls:

```
typst compile "Resume.typ" "Resume.pdf" --root .
```

The working directory is the output folder. The `--root .` flag ensures Typst resolves relative paths (like the profile photo) correctly.

If the `typst` binary is not found on PATH, the engine:
1. Checks the user-configured custom binary path from settings
2. Raises a clear error with instructions to download from `https://github.com/typst/typst/releases`

There is no fallback typesetter and no alternative compilation path. Typst is the sole compilation tool.

### 7.7 Template Guide Files

Every template ships with a companion `[name]_guide.md` file that documents:
- Every helper function and its parameters with a usage example
- Which placeholders are expected
- Layout constraints specific to this template (e.g., "skills must be comma-separated, not a list")
- Colour variables available for use in content (`accent`, `soft`, `text`)

---

## 8. The AI Pipeline

### 8.1 Overview

The AI pipeline runs once per job per batch, unless a cached `sections.json` exists. It consists of two stages — company research (optional) and resume generation — both using the Google Gemini API.

### 8.2 Company Research Stage

**Trigger:** Runs if `enable_company_research` is `True` AND (`company_research.md` does not exist OR its content contains fewer than 15 non-whitespace characters).

**Model:** Configurable, default `gemini-2.5-flash`  
**Tools:** `[google_search]` enabled  
**Temperature:** 0.2  
**Output:** Plain Markdown text (not JSON)

**Prompt structure:**
```
Research the company {COMPANY_NAME}.
Role hint: {ROLE_HINT}

Produce a concise markdown brief covering:
1. Company self-description (what they say about themselves)
2. External perspective (what candidates and employees say)
3. Internship or graduate-role expectations
4. Relevant technical domains, stacks, and tools
5. ATS keywords and trigger phrases worth echoing when genuinely evidenced
6. Brand and tone — including one primary accent colour (hex) and one soft tint (hex)

Keep the brief under 600 words. Cite sources where possible.
```

**Result:** Written to `applications/[JOB_FOLDER]/company_research.md`. Future runs load from this file — the API is never called again for the same job's research unless the file is deleted or emptied.

### 8.3 Resume Generation Stage

**Trigger:** Runs if no `sections.json` or `sections_override.json` exists in the output folder for this job.

**Model:** Configurable, default `gemini-2.5-flash`  
**Tools:** None (pure generation)  
**Temperature:** 0.2  
**Output:** Structured JSON matching the dynamic schema

#### Schema Construction

At runtime, the engine builds a Pydantic model dynamically from the discovered placeholder names:

```python
fields = {key: (str, ...) for key in dynamic_placeholders}
DynamicResumeModel = create_model("ResumeModel", **fields)
```

This model is passed to Gemini as `response_schema`. Gemini is constrained to return exactly the keys in the schema.

#### Prompt Construction

The prompt is assembled in four parts:

**Part 1 — System Role and Hard Rules**
```
You are generating Typst-ready section content for a resume template.
Return data only through the structured response schema.
Do not output markdown, code fences, commentary, or any text outside schema values.

Universal rules:
1. Produce exactly one string value for each key in the schema.
2. Every value must be a valid Typst content fragment for direct insertion into the template.
3. Do not include placeholder brace tokens ({{ }}) in your output values.
4. Do not invent achievements, claims, or figures not supported by the source data.
5. Escape the # character if it appears as a literal value (write \# instead).
6. Use -- for en-dash in date ranges.
7. Do not repeat the same claim across multiple fields unless it is central to role fit.
8. Relevant coursework must always include the grade or mark beside the subject name.
9. Use only the helper functions defined in the template guide — never invent new Typst functions.
10. Do not produce #set, #show, #import, or any document-level Typst declarations.
```

**Part 2 — Template Helper Function Reference**

This block is inserted from the active template's guide file. It tells the AI exactly which functions exist and how to call them. Example:

```
Available Typst helper functions for this template:

#job(title: str, company: str, period: str)[body content]
  - Use for each work experience entry
  - body content: bullet list items using - prefix
  - period: use -- for en-dash, e.g. "Jan 2024 -- Present"

#project(name: str, tech: str)[body content]
  - Use for each project entry
  - tech: comma-separated technology tags

#skill-group(label: str, items: str)
  - Use for a group of related skills
  - items: comma-separated list

#cert(name: str, year: str)
  - Use for each certification
  - year: four-digit year string
```

**Part 3 — Per-Placeholder Constraints**

Each dynamic placeholder gets an explicit constraint paragraph in the prompt:

```
Per-placeholder constraints:

TAILORED_PROFILE:
  2 to 4 sentences. No bullet points. Write in first person. Ground every claim in
  the source data. Make it specific to this role and company — generic profiles
  are worse than no profile at all.

DYNAMIC_EXPERIENCE:
  Use the #job() helper for each entry. Select only the most relevant experience.
  Exclude the YouTube/personal project role — it is rendered separately via the
  YOUTUBE_* placeholders. Keep each entry clearly separated.

DYNAMIC_PROJECTS:
  2 to 4 projects. Use the #project() helper for each entry. Emphasise concrete
  tools and technical outcomes.

TARGETED_COURSEWORK:
  4 to 5 subjects maximum. Include the mark in parentheses after each name.
  Prioritise the strongest marks in the most relevant subjects.
  Format as a Typst list using - bullet syntax.

TECHNICAL_SKILLS_TAGS:
  Role-relevant technical skills only. Use #skill-group() helpers. Group into short
  categories (e.g., "Languages", "Tools", "Platforms"). Do not list soft skills.

TARGETED_CERTIFICATIONS:
  Role-relevant certifications. Minimum 3 items when source data supports it.
  Use #cert() helper for each item.

YOUTUBE_BULLET_1, YOUTUBE_BULLET_2, YOUTUBE_BULLET_3:
  One sentence each. Quantified or specific. These are bullet points in the
  YouTube/personal-development experience block. Do not use the #job() helper here —
  these are raw bullet strings only.
```

**Part 4 — Source Data and Placeholder List**

```
Placeholders to fill:
- TAILORED_PROFILE
- DYNAMIC_EXPERIENCE
- [... all dynamic placeholders in sorted order ...]

Source data (master portfolio):
---
[FULL CONTENT OF master_portfolio.md]
---

Target job description:
---
[FULL CONTENT OF job_description.md]
---

Company research:
---
[FULL CONTENT OF company_research.md, or "No company research available."]
---
```

### 8.4 Rate Limiting

The engine maintains an `ApiRateLimiter` that enforces a configurable delay between API calls (default 4 seconds). This prevents 429 errors on the free tier. The delay is configurable in the GUI settings panel.

### 8.5 Retry Logic

```
For attempt in 1..3:
  1. rate_limiter.wait()               # enforce minimum delay
  2. call client.models.generate_content(...)
  3. rate_limiter.mark()               # record timestamp
  4. On APIError:
     - Parse error message for "retry in Xs" pattern
     - If 429 or 5xx AND attempt < 3:
         sleep(parsed_delay_or_10s)
         retry
     - Otherwise:
         raise RuntimeError with formatted message
```

### 8.6 Output Normalisation

After the AI responds, the engine normalises each section before injecting it into the template. This fixes common AI output quirks:

**Experience (`DYNAMIC_EXPERIENCE`):** Parse individual `#job()` calls, filter out any entries mentioning YouTube or "I did a thing" (handled by `YOUTUBE_*` placeholders), rebuild with consistent spacing.

**Projects (`DYNAMIC_PROJECTS`):** Parse individual `#project()` calls, deduplicate, rebuild.

**Coursework (`TARGETED_COURSEWORK`):** Extract items, limit to 5, ensure marks are present, remove duplicates.

**Certifications (`TARGETED_CERTIFICATIONS`):** Extract items from AI output, merge with the fallback pool from Section E of the master portfolio, deduplicate (preserve first occurrence), enforce minimum 3 items.

**YouTube Bullets:** Strip any introductory phrasing. Enforce single-sentence constraint. Normalise any inflated project counts to match the master portfolio's stated total.

---

## 9. The GUI Application

### 9.1 Architecture

The GUI is a PyQt6 application. `main.py` is the only entry point — it instantiates `QApplication` and `MainWindow`, applies the stylesheet, and calls `app.exec()`.

The GUI and the engine are strictly decoupled:
- `internal/generate_resume.py` contains zero GUI imports
- The GUI runs the engine on a `QThread` subclass to keep the interface responsive
- All engine progress is communicated to the GUI via Qt signals
- All engine errors are caught on the worker thread and forwarded to the GUI via signals

### 9.2 Session Settings vs Persisted Settings

There are two settings objects:

**`PersistedSettings`** — read from and written to `settings.json`. Contains all non-secret configuration. Changes are written after a 500ms debounce to avoid hammering the disk on every keystroke.

**`SessionSettings`** — lives only in memory for the duration of the window being open. Contains the API key. Never serialised. Cleared automatically when the window is destroyed.

### 9.3 Main Window Layout

The main window has a **tab bar** across the top with four tabs:

| Tab | Purpose |
|-----|---------|
| **Generate** | Primary workflow: select jobs, configure session, run, watch logs |
| **Jobs** | Browse, create, and edit job application folders |
| **Portfolio** | Edit `master_portfolio.md` in a rich text editor |
| **Settings** | All persisted configuration options |

The window title shows the application name and the current output folder path.

A **status bar** at the bottom shows: idle / running (X of Y jobs complete) / last completed time.

### 9.4 Generate Tab

This is the first tab the user sees and the one they use on every generation run.

**Left panel — Job List (60% of width):**
- Scrollable list of all discovered jobs. Auto-refreshes when the tab gains focus.
- Each job is rendered as a `JobCard` widget showing:
  - Company name (bold)
  - Role hint (muted)
  - Status icon: ✓ green (has `sections.json` cache), ⚡ violet (needs AI generation), ⚠ amber (missing `job_description.md`)
- Checkbox on each card for include/exclude from current run
- "Select All" and "Deselect All" buttons at the top
- "Refresh" button to re-scan the applications folder

**Right panel — Controls and Log (40% of width):**

- **API Key field:** Password-masked `QLineEdit`. Label reads "Gemini API Key (session only — never saved)". If `GEMINI_API_KEY` is set in the environment when the app launches, this field pre-populates from it. There is no "save" button — the value is held only in `SessionSettings._api_key`.

- **Model selector:** Compact dropdown showing available models, with a "custom" option that reveals a text field.

- **Force Regenerate checkbox:** When checked, ignores existing `sections.json` and calls Gemini for every selected job.

- **Generate button:** Large, full-width, violet background. Disabled when API key is empty or no jobs are checked. Label changes to "Running..." during a run.

- **Cancel button:** Appears only during a run, replacing the Generate button. Sets a cancellation flag; the current job finishes, then the batch stops.

- **Log view:** Read-only `QPlainTextEdit` with monospaced font. Receives real-time progress messages. Auto-scrolls to bottom. Lines are colour-coded:
  - White: informational
  - Yellow: warnings
  - Red: errors
  - Green: completion/success

- **Clear Log button:** Clears the log view.

### 9.5 Jobs Tab

Allows the user to manage application folders without leaving the GUI.

**Components:**
- Scrollable list of all job folders with company name, role, and status
- **New Job button:** Opens a two-field dialog (company name, role). Creates the folder and empty `job_description.md` and `company_research.md` files.
- **Open in File Manager button:** Opens the selected job's folder in the system file manager (`xdg-open` on Linux, `explorer` on Windows, `open` on macOS)
- **Edit Job Description button:** Opens `job_description.md` in the default text editor
- **Edit Company Research button:** Opens `company_research.md` in the default text editor
- **View AI Cache button:** Opens `sections.json` in the default application (JSON viewer or text editor)
- **Archive Job button:** Moves the job folder to `applications/ARCHIVE/` with a confirmation dialog
- **Delete AI Cache button:** Deletes `sections.json` for the selected job (forces AI regeneration on next run), with a confirmation dialog

### 9.6 Portfolio Tab

A split panel:

- **Left (60%):** Monospaced `QPlainTextEdit` showing the raw Markdown content of `master_portfolio.md`. Line numbers enabled.
- **Right (40%):** Read-only `QTextBrowser` showing a basic HTML preview (Markdown headings, bold, and bullet lists rendered visually).
- **Save button:** Writes changes back to `master_portfolio.md`. Shows an unsaved-changes indicator (`*`) in the tab title when edits are pending.
- **Reload button:** Discards unsaved changes and reloads from disk. Asks for confirmation if there are unsaved edits.

The Portfolio tab does not auto-save. Changes are only written on explicit save.

### 9.7 Settings Tab

All settings are organised into labelled `QGroupBox` sections. Changes persist via debounced write to `settings.json`.

**API Settings:**
- Model Name: `QComboBox` with common models + custom text entry (default: `gemini-2.5-flash`)
- Research Model Name: Same widget (default: `gemini-2.5-flash`)
- API Call Delay (seconds): `QDoubleSpinBox` (default: 4.0, range: 0.5–60.0)
- Enable Company Research: `QCheckBox` toggle

**Generation Settings:**
- Template: `QComboBox` listing all `.typ` files found in `internal/templates/`
- Resume Title: `QLineEdit` (used as the output filename stem)
- Force Regenerate by Default: `QCheckBox`

**Output Settings:**
- Output Folder: `QLineEdit` + "Browse" `QPushButton` (opens `QFileDialog.getExistingDirectory`). The selected path is stored in `settings.json` as an absolute path.
- Compile to PDF: `QCheckBox`
- Typst Binary Path: `QLineEdit` + "Browse" `QPushButton`. Leave blank to use system PATH.

**Profile Photo Settings:**
- Profile Photo: `QLineEdit` + "Browse" `QPushButton` (file picker accepting `.jpg`, `.jpeg`, `.png`)
- Photo Rotation (degrees): `QComboBox` with options 0, 90, 180, 270

### 9.8 API Key Security Model

The API key follows this exact lifecycle:

1. **Entry:** User types or pastes the key into the Generate tab field
2. **Storage:** Value is held in `SessionSettings._api_key: str` (private attribute)
3. **Scope:** `SessionSettings` is instantiated once when the window opens; it goes out of scope and is garbage collected when the window closes
4. **Transmission:** The key is passed to `genai.Client(api_key=...)` as a direct constructor argument on the generation thread. It is never assigned to an environment variable by the application.
5. **Display:** The GUI field is always a password-masked `QLineEdit` — the value is never shown in plaintext
6. **Persistence:** There is no "Save Key" button. The key does not appear in `settings.json`, log files, or any other persisted store.
7. **Pre-population:** If `GEMINI_API_KEY` is set in the environment before launching, the GUI reads it once at startup using `os.getenv("GEMINI_API_KEY", "")` and writes it into the session field. The environment variable is not re-read during the session.

### 9.9 Worker Thread Pattern

The generation engine runs on a `QThread` subclass:

```python
class GeneratorWorker(QThread):
    progress = pyqtSignal(str, str)   # message, level ("info"|"warning"|"error"|"success")
    finished = pyqtSignal(bool)       # success: bool

    def __init__(self, settings, session, job_names, force_regenerate):
        ...

    def run(self):
        try:
            run_batch(
                settings=self.settings,
                api_key=self.session.api_key,
                job_names=self.job_names,
                force_regenerate=self.force_regenerate,
                progress_callback=self._emit_progress,
            )
            self.finished.emit(True)
        except Exception as exc:
            self.progress.emit(str(exc), "error")
            self.finished.emit(False)

    def _emit_progress(self, message: str, level: str = "info") -> None:
        self.progress.emit(message, level)
```

The main window connects `worker.progress` to the log view's append method and `worker.finished` to the post-run UI reset.

### 9.10 Qt Stylesheet (theme.qss)

The application uses a dark violet theme. Key visual decisions:

| Element | Value |
|---------|-------|
| Window background | `#1e1e2e` (deep navy-black) |
| Panel / card background | `#2a2a3e` (slightly lighter) |
| Accent colour | `#7c3aed` (violet) |
| Success colour | `#22c55e` (green) |
| Warning colour | `#f59e0b` (amber) |
| Error colour | `#ef4444` (red) |
| Text primary | `#e2e8f0` (near white) |
| Text muted | `#64748b` (slate grey) |
| Border radius | 6px on all cards, inputs, buttons |
| Font | System default sans-serif for UI; monospace for editor and log |

The Generate button uses the accent colour with a darker hover state and a slight scale transform.

---

## 10. The Generation Engine

`internal/generate_resume.py` is a pure Python module. It imports nothing from the GUI. All functions are synchronous. The GUI runs it on a `QThread`.

### 10.1 Entry Point

```python
def run_batch(
    settings: GeneratorSettings,
    api_key: str,
    job_names: list[str] | None = None,
    force_regenerate: bool = False,
    progress_callback: Callable[[str, str], None] | None = None,
) -> None:
```

- `settings` — all persisted configuration (see Section 12)
- `api_key` — Gemini API key, passed directly (never read from disk inside the engine)
- `job_names` — if provided, only process jobs whose folder names are in this list; if `None`, process all discovered jobs
- `force_regenerate` — if `True`, skip cache check and always call Gemini
- `progress_callback` — optional `(message: str, level: str) -> None` function; defaults to `print` if `None`

### 10.2 Per-Job Processing Sequence

For each discovered job in sorted order (filtered by `job_names` if provided):

1. **Prepare output folder** — create or validate `outputs/XX-YY Job Name/`, archive any existing artifacts inside it
2. **Extract static placeholders** — read master portfolio, extract personal fields, copy profile photo, build `PORTFOLIO_NOTE`
3. **Render static pass** — replace all static `{{PLACEHOLDER}}` tokens in the template text
4. **Discover dynamic placeholders** — scan the partially-rendered template for remaining `{{PLACEHOLDER}}` tokens
5. **Check for manual override** — if `sections_override.json` exists in the application folder, load it and skip to step 8
6. **Check for cache** — if `sections.json` exists in the output folder AND `force_regenerate=False`, load it and skip to step 8
7. **Run AI pipeline** — company research (if needed), then resume generation
8. **Normalise output** — clean and validate all section values
9. **Save cache** — write `sections.json` to the output folder
10. **Render final pass** — replace all dynamic `{{PLACEHOLDER}}` tokens
11. **Write `.typ` file** — save the fully-rendered Typst source to the output folder
12. **Compile** — call `typst compile` to produce the PDF (if `compile_pdf=True`)
13. **Cleanup** — remove any files not in the allowed set (`.typ`, `.pdf`, `sections.json`, profile photo, `ARCHIVE/`)

### 10.3 GeneratorSettings Fields

```python
@dataclass
class GeneratorSettings:
    applications_root: Path           # e.g. Path("applications")
    outputs_root: Path                # e.g. Path("outputs")
    templates_root: Path              # e.g. Path("internal/templates")
    selected_template_name: str       # e.g. "modern.typ"
    master_portfolio_file: Path       # e.g. Path("internal/data/master_portfolio.md")
    model_name: str                   # e.g. "gemini-2.5-flash"
    research_model_name: str          # e.g. "gemini-2.5-flash"
    compile_pdf: bool                 # True = call typst compile after rendering
    typst_binary_path: str            # "" = use PATH; else absolute path to binary
    enable_company_research: bool     # True = call Gemini with google_search for research
    api_call_delay_seconds: float     # Minimum seconds between API calls
    resume_title: str                 # Used as output filename stem
    profile_photo_file: Path | None   # None = no photo
    profile_photo_rotation_degrees: int  # 0, 90, 180, or 270
```

Note: `api_key` is NOT a field on `GeneratorSettings`. It is passed directly to `run_batch()` as a separate argument so settings can be serialised to JSON without risk of including the key.

---

## 11. Output Management

### 11.1 Output Folder Naming

```
XX-YY Job Name
```

- `XX` = batch number (two digits, zero-padded). `01` is always the most recent batch.
- `YY` = job index (two digits, zero-padded). Assigned once; stable across re-runs for the same job.
- `Job Name` = the verbatim folder name from `applications/` (includes the ` - ` separator).

### 11.2 Batch Versioning Algorithm

Before processing any jobs in a run:

1. Read all existing folders in `outputs/` matching `(\d{2})-(\d{2}) (.+)`.
2. Identify which logical names are in the **current batch** (the jobs about to be processed).
3. For all folders whose logical name is **not** in the current batch: increment their batch number by 1 (capped at 99). This bumps old batches out of the `01` slot.
4. Assign batch `01` and sequential indices (`01`, `02`, `03`, ...) to folders in the current batch, creating new folders if they don't exist.

The index assigned to each job is determined by its alphabetical position in the discovery order. If the same job was processed in a previous run, it retains its previous index.

### 11.3 Archival

When an output folder already contains a `Resume.typ` and/or `Resume.pdf`:

1. Create an `ARCHIVE/` subdirectory if it does not exist.
2. Find the highest existing version number (`V1`, `V2`, ...) in `ARCHIVE/` for this resume title.
3. Move old files to `ARCHIVE/Resume V{N+1}.typ`, `ARCHIVE/Resume V{N+1}.pdf`, `ARCHIVE/sections.json V{N+1}`.

The `ARCHIVE/` folder is never cleaned up automatically.

### 11.4 Allowed Output Folder Contents

After each run, the cleanup step deletes any file not in this allowlist:
- `{resume_title}.typ`
- `{resume_title}.pdf` (only if `compile_pdf=True`)
- `sections.json`
- `profile_photo.{ext}` (any image extension)
- `ARCHIVE/` (subdirectory — preserved entirely)

This removes Typst auxiliary files and any stale artefacts.

---

## 12. Settings Reference

All persisted settings live in `settings.json` at the repository root. The GUI reads and writes this file. Do not hand-edit it while the GUI is running.

```json
{
  "applications_root": "applications",
  "outputs_root": "outputs",
  "templates_root": "internal/templates",
  "selected_template_name": "modern.typ",
  "master_portfolio_file": "internal/data/master_portfolio.md",
  "model_name": "gemini-2.5-flash",
  "research_model_name": "gemini-2.5-flash",
  "compile_pdf": true,
  "typst_binary_path": "",
  "enable_company_research": true,
  "api_call_delay_seconds": 4.0,
  "resume_title": "Dylan's Resume",
  "profile_photo_file": "internal/profile_photo/Me.jpg",
  "profile_photo_rotation_degrees": 90,
  "force_regenerate": false
}
```

Path values may be relative (resolved from the repository root at runtime) or absolute.

`typst_binary_path`: If empty string, `typst` is resolved via `shutil.which`. If set, used directly as the executable path.

**The `api_key` field never appears in `settings.json`.**

---

## 13. Dependency and Environment Setup

### 13.1 Python Dependencies

`internal/requirements.txt`:
```
google-genai>=1.0.0
pydantic>=2.0.0
PyQt6>=6.7.0
```

Install:
```
pip install -r internal/requirements.txt
```

Python 3.11 or later is required.

### 13.2 Typst Binary

Download the latest release from `https://github.com/typst/typst/releases`.

- **Linux/macOS:** Place on PATH (e.g., `/usr/local/bin/typst`) or set `typst_binary_path` in settings.
- **Windows:** Place `typst.exe` on PATH or set `typst_binary_path` in settings.

Typst is a single self-contained binary. No package manager, font packages, or runtime dependencies are needed.

### 13.3 API Key

The Gemini API key is entered in the Generate tab of the GUI each session. For development convenience, set `GEMINI_API_KEY` in the environment before launching — the GUI pre-populates the field from it.

Obtain a key at: `https://aistudio.google.com/app/apikey`

### 13.4 Git Ignores

These paths belong in `.gitignore`:
```
internal/profile_photo/*.jpg
internal/profile_photo/*.jpeg
internal/profile_photo/*.png
outputs/
settings.json
*.pdf
__pycache__/
*.pyc
```

Do **not** ignore `sections.json` files inside `applications/` subdirectories — these are AI output caches and should be committed so collaborators don't waste API quota re-generating them.

---

## 14. Prompt Engineering Reference

### 14.1 Core Principles

**Constraint over instruction.** Tell the model what it may not do, not just what it should do. "Never produce Typst document-level declarations" is more effective than "produce only content fragments."

**Explicit per-field rules.** Each placeholder gets its own constraint paragraph. Universal rules come first; per-field overrides follow.

**Grounded generation.** The prompt explicitly forbids inventing facts not present in the source data. This is the most critical safety property — without it, the model will fabricate plausible-sounding but false achievements.

**Low temperature.** Use 0.2 for all generation tasks. Resume content is not creative writing; it should be precise, consistent, and close to deterministic.

**Structured output.** Always use `response_mime_type: "application/json"` with a schema. Never rely on parsing freeform text from the model.

### 14.2 Adding a New Placeholder

1. Add `{{NEW_PLACEHOLDER}}` to the template `.typ` file where the content should appear.
2. Add a constraint paragraph to the prompt builder for this placeholder — describe the expected format, length, and helper function to use.
3. Add a normalisation step in `normalize_model_sections()` if the AI output for this field requires post-processing.
4. Document the placeholder in the template's guide file.
5. Test by deleting `sections.json` for a job and re-running generation.

### 14.3 Adding a New Template

1. Create `internal/templates/your_template.typ`.
2. Define all `{{PLACEHOLDER}}` tokens in the template.
3. Define helper functions at the top of the `.typ` file for the AI to use in content fragments.
4. Create `internal/templates/your_template_guide.md` documenting all helper functions and placeholder constraints.
5. Update the prompt builder to include the helper reference block from the guide file when this template is active.
6. The GUI's template selector reads the `internal/templates/` folder automatically — no code change needed for the dropdown.

### 14.4 Modifying the Company Research Prompt

The company research prompt is built inline in `build_company_research_query()` in `generate_resume.py`. Edit that function to change what information is collected. The function receives the `JobSpec` object, so it has access to `job.company_name` and `job.role_hint`.

---

## 15. Error Handling Philosophy

### 15.1 Fail Loudly, Fail Specifically

When the engine encounters an unrecoverable error, it raises a `RuntimeError` with a message that:
- States exactly what went wrong
- Identifies which job was being processed
- Includes relevant excerpts from any subprocess output (e.g., last 40 lines of Typst stdout)
- Suggests a concrete next step

The GUI catches all exceptions from the worker thread and displays them in the log view in red. A failed job does not stop the batch — the engine moves to the next job.

### 15.2 Recoverable vs Fatal Errors

**Recoverable** (log warning, continue to next job):
- API error for a single job
- Typst compilation failure for a single job
- Missing company research (skip that stage, continue with generation)

**Fatal** (stop the entire batch immediately):
- Invalid or missing API key (would fail for every job)
- `master_portfolio.md` not found
- Template `.typ` file not found
- Typst binary not found and compile is requested

### 15.3 API Error Classification

| Condition | User Message | Action |
|-----------|-------------|--------|
| HTTP 429 / `quota_exceeded` | "Rate limited — check delay setting or wait" | Sleep extracted delay, retry up to 3× |
| HTTP 500/502/503/504 | "Gemini server error — retrying" | Retry with backoff |
| Invalid key / auth error | "Invalid API key — check the Generate tab field" | Raise fatal error |
| Schema mismatch in response | "AI returned unexpected fields" | Log warning, use available fields |

### 15.4 Key Parity Validation

After AI generation and normalisation, the engine validates:
- Every dynamic placeholder has a value in the model output
- No unexpected keys are present

If either check fails: log a warning, pad missing keys with empty strings, discard extra keys. Do not abort the job.

### 15.5 Typst Compilation Error Reporting

If `typst compile` exits with a non-zero code, the engine:
1. Reads stdout and stderr from the subprocess
2. Extracts the last 40 lines of stdout and last 25 lines of stderr
3. Raises `RuntimeError` with both excerpts and the job name
4. Preserves the `.typ` file in the output folder so the user can inspect it manually

---

## 16. Security Considerations

### 16.1 API Key Handling

- Never written to disk by the application
- Stored only as a private `_api_key: str` attribute on `SessionSettings`
- Object goes out of scope when the window closes
- Never logged
- Always displayed as a masked password field in the GUI
- No "remember key" feature
- Passed to `genai.Client(api_key=...)` as a direct argument — not assigned to environment variables by the application

### 16.2 File Operations

- All paths use `pathlib.Path` — no string concatenation for path building
- Output paths are validated to be inside the configured output folder before writes
- The cleanup allowlist (delete only non-listed files) is safer than a denylist approach
- `subprocess` is always called with a list of arguments (`[binary, "compile", ...]`), never with `shell=True`
- The Typst compile call is constructed as: `[typst_path, "compile", str(typ_file), str(pdf_file), "--root", str(output_dir)]`

### 16.3 AI Output Handling

- AI output is treated as untrusted user content
- It is normalised and sanitised before insertion into templates
- It is never executed — only inserted as text into a `.typ` source file
- Typst enforces that content fragments cannot execute arbitrary system operations; they are document content, not scripts

### 16.4 No Unsolicited Network Traffic

- The GUI makes no network requests itself
- All Gemini API calls are made on the background `QThread`, explicitly triggered by the user pressing Generate
- There is no telemetry, analytics, update checking, or any other background network activity

---

*End of handover document. This fully describes the system. When in doubt, return to Section 2.*
