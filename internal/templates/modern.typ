// ─────────────────────────────────────────────────────────────────────────────
// modern.typ — Primary resume template
// Placeholders: {{DOUBLE_CURLY}} tokens are filled by the generation engine.
// Helper functions below are the ONLY Typst functions the AI may use in content.
// ─────────────────────────────────────────────────────────────────────────────

// ── Colour palette ────────────────────────────────────────────────────────────
#let accent = rgb("#7c3aed")
#let soft   = rgb("#ede9fe")
#let muted  = rgb("#64748b")
#let body-color = rgb("#1e1e2e")

// ── Page setup ────────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (top: 1.6cm, bottom: 1.6cm, left: 1.5cm, right: 1.5cm),
)
#set text(font: "Liberation Sans", size: 9.5pt, fill: body-color)
#set par(leading: 0.55em)

// ── Helper: divider line ──────────────────────────────────────────────────────
#let divider() = {
  v(0.15em)
  line(length: 100%, stroke: 0.5pt + accent.lighten(30%))
  v(0.15em)
}

// ── Helper: section header ────────────────────────────────────────────────────
// Usage: #section("Experience")[ ... content ... ]
#let section(title, body) = {
  text(fill: accent, weight: "bold", size: 10pt)[#upper(title)]
  divider()
  body
  v(0.45em)
}

// ── Helper: job entry ─────────────────────────────────────────────────────────
// Usage: #job(title: "Engineer", company: "Acme", period: "Jan 2024 -- Present")[ - bullet ]
#let job(title: "", company: "", period: "", body) = {
  grid(
    columns: (1fr, auto),
    gutter: 0.3em,
    [*#title* #h(0.2em) #text(fill: muted, style: "italic", size: 8.5pt)[#company]],
    text(fill: muted, size: 8.5pt)[#period],
  )
  v(0.1em)
  body
  v(0.35em)
}

// ── Helper: project entry ─────────────────────────────────────────────────────
// Usage: #project(name: "Robot", tech: "ROS2, Python")[ - bullet ]
#let project(name: "", tech: "", body) = {
  [*#name* #h(0.4em) #text(fill: accent, size: 8pt)[#tech]]
  v(0.1em)
  body
  v(0.35em)
}

// ── Helper: skill group ───────────────────────────────────────────────────────
// Usage: #skill-group(label: "Languages", items: "Python, C++, Rust")
#let skill-group(label: "", items: "") = {
  grid(
    columns: (3.5cm, 1fr),
    gutter: 0.2em,
    text(fill: muted, weight: "bold", size: 8.5pt)[#label],
    text(size: 8.5pt)[#items],
  )
  v(0.1em)
}

// ── Helper: certification item ────────────────────────────────────────────────
// Usage: #cert(name: "AWS Cloud Practitioner", year: "2023")
#let cert(name: "", year: "") = {
  grid(
    columns: (1fr, auto),
    gutter: 0.3em,
    text(size: 8.5pt)[#name],
    text(fill: muted, size: 8.5pt)[#year],
  )
  v(0.08em)
}

// ── Helper: inline contact item ───────────────────────────────────────────────
#let contact-item(icon, value) = {
  text(fill: accent)[#icon] + h(0.2em) + text(size: 8.5pt)[#value]
}

// ─────────────────────────────────────────────────────────────────────────────
// DOCUMENT BODY
// ─────────────────────────────────────────────────────────────────────────────

// ── Header ────────────────────────────────────────────────────────────────────
#grid(
  columns: (1fr, auto),
  gutter: 1em,
  align: horizon,
  [
    #text(size: 22pt, weight: "bold", fill: body-color)[{{FULL_NAME}}]
    #v(0.2em)
    #grid(
      columns: (auto, auto, auto, auto),
      gutter: (1.2em, 0.3em),
      contact-item("✉", "{{EMAIL_ADDRESS}}"),
      contact-item("in", "{{LINKEDIN_URL}}"),
      contact-item("⌂", "{{LOCATION}}"),
      contact-item("⌥", "{{GITHUB_URL}}"),
    )
  ],
  // Profile photo (empty string = no photo)
  if "{{PROFILE_PHOTO_PATH}}" != "" {
    box(
      width: 2.2cm,
      height: 2.2cm,
      clip: true,
      radius: 50%,
      image("{{PROFILE_PHOTO_PATH}}", width: 100%, height: 100%, fit: "cover"),
    )
  },
)

#divider()
#v(0.2em)

// ── Two-column layout ─────────────────────────────────────────────────────────
#columns(2, gutter: 1.2em)[

// ════════════════════════════ LEFT COLUMN ════════════════════════════════════

#section("Profile")[
  #text(size: 9pt)[{{TAILORED_PROFILE}}]
]

#section("Education")[
  #job(title: "B.Eng. (Hons) Mechatronics", company: "UTS", period: "2022 -- 2026")[
    - GPA 6.2 / 7.0 · WAM 79.4
  ]
]

#section("Coursework")[
{{TARGETED_COURSEWORK}}
]

#section("Skills")[
{{TECHNICAL_SKILLS_TAGS}}
]

#section("Certifications")[
{{TARGETED_CERTIFICATIONS}}
]

#colbreak()

// ════════════════════════════ RIGHT COLUMN ═══════════════════════════════════

#section("Experience")[
  {{DYNAMIC_EXPERIENCE}}
  #job(title: "I did a thing", company: "YouTube · Part-time", period: "Feb 2022 -- Present")[
    - {{YOUTUBE_BULLET_1}}
    - {{YOUTUBE_BULLET_2}}
    - {{YOUTUBE_BULLET_3}}
  ]
]

#section("Projects")[
  {{DYNAMIC_PROJECTS}}
]

// Footer note
#v(1fr)
#text(fill: muted, size: 7.5pt)[{{PORTFOLIO_NOTE}}]

] // end columns
