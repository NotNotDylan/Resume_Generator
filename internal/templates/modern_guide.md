# modern.typ — Template Helper Guide

This file documents every helper function defined in `modern.typ`.
The generation engine injects this guide into the AI prompt so the model knows
which functions are available and how to call them.

---

## Helper Functions

### `#job(title, company, period)[ body ]`

Use for every work experience entry.

```typst
#job(title: "Embedded Systems Engineer", company: "Acme Robotics", period: "Jan 2024 -- Present")[
  - Designed a custom motor controller achieving 0.1° positional accuracy
  - Reduced firmware boot time by 60% through HAL optimisation
]
```

- `title`: Job title string
- `company`: Company name string
- `period`: Date range using `--` for en-dash (e.g. `"Jan 2024 -- Present"`)
- `body`: Bullet list items using `- ` prefix, one per line

---

### `#project(name, tech)[ body ]`

Use for every project entry.

```typst
#project(name: "Autonomous Lawn Mower", tech: "ROS2, Python, RPLiDAR")[
  - Designed and built a fully autonomous outdoor robot using Nav2 stack
  - Integrated RPLiDAR A1 for 360° obstacle detection at < 0.5m resolution
]
```

- `name`: Project name string
- `tech`: Comma-separated technology tags (kept short — max ~40 chars)
- `body`: Bullet list items using `- ` prefix

---

### `#skill-group(label, items)`

Use for a group of related skills. No body block.

```typst
#skill-group(label: "Languages", items: "Python, C++, Rust, TypeScript")
#skill-group(label: "Tools", items: "ROS2, KiCad, Git, Docker")
#skill-group(label: "Platforms", items: "Linux, Raspberry Pi, STM32")
```

- `label`: Category name (kept to 1–2 words; fits in a 3.5cm column)
- `items`: Comma-separated skill list

---

### `#cert(name, year)`

Use for each certification entry. No body block.

```typst
#cert(name: "AWS Cloud Practitioner", year: "2023")
#cert(name: "Google IT Support Professional Certificate", year: "2022")
#cert(name: "PADI Open Water Diver", year: "2019")
```

- `name`: Full certification name
- `year`: Four-digit year string

---

## Placeholder Reference

| Placeholder | Location in template | Content type |
|-------------|---------------------|-------------|
| `FULL_NAME` | Header | Plain text |
| `EMAIL_ADDRESS` | Header | Plain text |
| `LINKEDIN_URL` | Header | Plain text (URL, no https://) |
| `GITHUB_URL` | Header | Plain text (URL, no https://) |
| `LOCATION` | Header | Plain text (City, State) |
| `PROFILE_PHOTO_PATH` | Header | Filename only (e.g. `profile_photo.jpg`) or empty string |
| `PORTFOLIO_NOTE` | Footer | Plain text sentence |
| `TAILORED_PROFILE` | Left column | Plain text, 2–4 sentences, no bullets |
| `TARGETED_COURSEWORK` | Left column | Typst list using `- Subject (Mark)` syntax |
| `TECHNICAL_SKILLS_TAGS` | Left column | One or more `#skill-group(...)` calls |
| `TARGETED_CERTIFICATIONS` | Left column | One or more `#cert(...)` calls |
| `DYNAMIC_EXPERIENCE` | Right column | One or more `#job(...)[ ... ]` blocks |
| `DYNAMIC_PROJECTS` | Right column | One or more `#project(...)[ ... ]` blocks |
| `YOUTUBE_BULLET_1` | Right column | Single sentence string (raw — no helper) |
| `YOUTUBE_BULLET_2` | Right column | Single sentence string (raw — no helper) |
| `YOUTUBE_BULLET_3` | Right column | Single sentence string (raw — no helper) |

---

## Layout Constraints

- **Left column** is narrower — keep `TAILORED_PROFILE` concise.
- **Coursework** must include marks: `- Signal Processing (84)` — not just the subject name.
- **Skills** must use `#skill-group()` — never a plain bullet list.
- **Certifications** must use `#cert()` — never a plain bullet list.
- **YouTube bullets** are plain sentence strings (they are inserted directly into a `#job()` block defined in the template — do not wrap them in `#job()`).
- **Never** produce `#set`, `#show`, `#import`, or `#let` in any content fragment.
- **Never** produce Markdown formatting (`**bold**`, `## heading`) in any content fragment.
- Use `--` for en-dash in date ranges.
- Escape a literal `#` character as `\#` if it appears in text content.
