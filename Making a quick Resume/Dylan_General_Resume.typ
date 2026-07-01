// Dylan Bitar — General Resume (pixel-matched to Dylan_General_Resume.html)
// Compile: typst compile Dylan_General_Resume.typ Dylan_General_Resume.pdf --root . --font-path fonts

#let ink         = rgb("#0f1923")
#let ink-mid     = rgb("#3a4a5a")
#let ink-light   = rgb("#6b7f8f")
#let accent      = rgb("#0b6e70")
#let accent-soft = rgb("#e6f4f4")
#let rule-color  = rgb("#c9d6da")
#let sidebar-bg  = rgb("#f4f7f8")

#let lato    = "Lato"
#let garamond = "Cormorant Garamond"
#let mono    = "JetBrains Mono"

#set page(paper: "a4", margin: 0pt)
#set text(font: lato, size: 9.2pt, fill: ink, lang: "en")
#set par(leading: 1.5em, justify: false, spacing: 0pt)

// ── Helpers (CSS-matched) ─────────────────────────────────────────────────────

#let section-label(title) = {
  block(spacing: 7pt, below: 7pt)[
    text(
      font: mono,
      size: 6.8pt,
      weight: "medium",
      fill: accent,
      tracking: 1.8pt,
    )[#upper(title)]
    v(4pt)
    line(length: 100%, stroke: 1pt + accent)
  ]
}

#let section(body) = block(below: 16pt, body)

#let metric-chip(content) = box(
  fill: accent-soft,
  stroke: 0.5pt + rgb("#9ecfd0"),
  radius: 3pt,
  inset: (top: 2pt, bottom: 2pt, left: 6pt, right: 6pt),
)[
  #text(font: mono, size: 7pt, weight: "medium", fill: accent)[#content]
]

#let tag(content, highlight: false) = box(
  fill: if highlight { accent-soft } else { white },
  stroke: 0.5pt + if highlight { rgb("#9ecfd0") } else { rule-color },
  radius: 3pt,
  inset: (top: 2pt, bottom: 2pt, left: 6pt, right: 6pt),
)[
  #text(
    size: 7.5pt,
    weight: if highlight { "bold" } else { "regular" },
    fill: if highlight { accent } else { ink-mid },
  )[#content]
]

#let skill-tags(..items) = box(width: 100%, inset: 0pt)[
  #for (i, item) in items.pos().enumerate() {
    if i > 0 { h(3pt) }
    tag(..item)
  }
]

#let exp-bullet(body) = block(below: 2pt)[
  #grid(
    columns: (10pt, 1fr),
    column-gutter: 0pt,
    align: (left + top, left + top),
    text(fill: accent, weight: "bold")[›],
    text(size: 8.3pt, fill: ink-mid)[#body],
  )
]

#let project-bullet(body) = block(below: 0pt)[
  #grid(
    columns: (10pt, 1fr),
    column-gutter: 0pt,
    align: (left + top, left + top),
    pad(left: 1pt)[text(fill: accent, weight: "bold", size: 11pt)[·]],
    text(size: 8pt, fill: ink-mid)[#body],
  )
]

#let exp-header(title, dates, title-size: 9pt) = {
  grid(
    columns: (1fr, auto),
    column-gutter: 6pt,
    align: (left + horizon, right + horizon),
    text(weight: "bold", size: title-size, fill: ink)[#title],
    text(font: mono, size: 7pt, fill: ink-light)[#dates],
  )
  v(2pt)
}

#let exp-org(content, size: 8pt) = block(below: 4pt)[
  #text(fill: accent, weight: "bold", size: size)[#content]
]

#let project-grade(content) = box(
  fill: accent-soft,
  stroke: 0.5pt + rgb("#9ecfd0"),
  radius: 3pt,
  inset: (top: 1pt, bottom: 1pt, left: 5pt, right: 5pt),
)[
  #text(font: mono, size: 7pt, weight: "medium", fill: accent)[#content]
]

// ── Page grid (matches .page: 210mm, cols 68mm + 1fr, header spans full) ─────

#box(width: 210mm)[
  #grid(
    columns: (68mm, 1fr),
    column-gutter: 0pt,
    row-gutter: 0pt,

    // ── HEADER (grid-column: 1 / -1) ─────────────────────────────────────────
    grid.cell(colspan: 2)[
      #block(
        width: 100%,
        fill: ink,
        inset: (top: 22pt, right: 26pt, bottom: 18pt, left: 26pt),
        stroke: (bottom: 3pt + accent),
      )[
        #grid(
          columns: (68mm, 1fr),
          column-gutter: 0pt,
          align: (left + top, left + bottom),
          pad(right: 16pt)[
            #text(
              font: garamond,
              size: 28pt,
              weight: "semibold",
              fill: white,
              tracking: -0.5pt,
            )[Dylan Bitar]
            #v(3pt)
            #text(
              font: mono,
              size: 7pt,
              fill: rgb("#ffffff73"),
              tracking: 0.5pt,
            )[HE / HIM]
          ],
          pad(bottom: 6pt)[
            #text(
              font: mono,
              size: 8.5pt,
              weight: "medium",
              fill: rgb("#a8c8ca"),
              tracking: 0.3pt,
            )[Mechatronics Engineering (Hons) · UTS  |  Sensing & Embedded Systems]
            #v(8pt)
            #box(inset: 0pt)[
              #for (i, item) in (
                "possibly.a.dylan\@gmail.com",
                "linkedin.com/in/dylan-bitar",
                "Student No. 25308685",
              ).enumerate() {
                if i > 0 { h(18pt) }
                text(size: 7.8pt, fill: rgb("#ffffffa6"))[
                  #text(fill: accent, weight: "bold")[▪]#h(4pt)#item
                ]
              }
            ]
          ],
        )
      ]
    ],

    // ── SIDEBAR (aside) ──────────────────────────────────────────────────────
    block(
      width: 100%,
      fill: sidebar-bg,
      stroke: (right: 0.5pt + rule-color),
      inset: (top: 20pt, right: 18pt, bottom: 24pt, left: 18pt),
    )[
      #section[
        #section-label("Education")
        #block(below: 10pt)[
          #text(weight: "bold", size: 8.5pt)[University of Technology Sydney]
          #block(spacing: 0pt)[
            #set par(leading: 1.4em, spacing: 0pt)
            #text(size: 8pt, fill: ink-mid)[
            B.Eng (Hons) / Dip. Professional Engineering Practice \
            Major: Mechatronic Engineering
            ]
          ]
          #v(1pt)
          #text(font: mono, size: 7pt, fill: ink-light)[Jan 2024 – Nov 2029 (expected)]
          #v(4pt)
          #box(inset: 0pt)[
            #metric-chip[WAM 81.12]
            #h(8pt)
            #metric-chip[GPA 5.92]
          ]
        ]
        #block(below: 0pt)[
          #text(weight: "bold", size: 8.5pt)[St Mary's Cathedral College]
          #block(spacing: 0pt)[
            #set par(leading: 1.4em, spacing: 0pt)
            #text(size: 8pt, fill: ink-mid)[
              High School Diploma \
              1st — Engineering Studies, Sydney Catholic Schools
            ]
          ]
          #v(1pt)
          #text(font: mono, size: 7pt, fill: ink-light)[ATAR 88.9 | 2022–2023]
        ]
      ]

      #section[
        #section-label("Relevant Coursework")
        #for (name, grade) in (
          ("Sensors & Control for Mechatronic Systems", "D · 82"),
          ("Embedded Mechatronics Systems", "HD"),
          ("Programming 1 (Python & fundamentals)", "HD · 92"),
          ("Industrial Robotics (6-DOF simulation & control)", "D"),
          ("Intro to Mechatronics Engineering", "HD"),
          ("Engineering Project Appraisal", "D · 76"),
        ) {
          block(below: 4pt)[
            grid(
              columns: (1fr, auto),
              column-gutter: 4pt,
              align: (left + horizon, right + horizon),
              text(size: 7.8pt, fill: ink-mid)[#name],
              text(font: mono, size: 6.8pt, weight: "medium", fill: accent)[#grade],
            )
          ]
        }
      ]

      #section[
        #section-label("Technical Skills")
        #for (group, items, highlights) in (
          (
            "Sensing & Signal Processing",
            ("Sensor Integration", "Time-of-Flight", "Analogue Filtering", "Heart Rate Sensing", "Control Systems", "PID"),
            (0, 1, 2, 3),
          ),
          (
            "Programming",
            ("Python", "C / Embedded C", "STM32CubeIDE", "MATLAB"),
            (0, 1),
          ),
          (
            "Hardware & Embedded",
            ("STM32 Microcontrollers", "Altium PCB Design", "SMD Soldering (0402)", "Fusion 360", "SolidWorks"),
            (0, 1),
          ),
          (
            "Tools & Platforms",
            ("Rapid Prototyping", "Microsoft Azure AI", "Git", "MS Office"),
            (),
          ),
        ) {
          block(below: 9pt)[
            text(weight: "bold", size: 7.5pt, fill: ink-mid, tracking: 0.5pt)[#upper(group)]
            v(4pt)
            skill-tags(..items.enumerate().map(((i, item)) => (item, i in highlights)))
          ]
        }
      ]

      #section[
        #section-label("Certifications")
        #for (name, issuer) in (
          ("Microsoft Azure AI Fundamentals", "Microsoft · Jul 2024 · ID C10243EC6D0E908E"),
          ("C Programming for Embedded Applications", "LinkedIn Learning · Jul 2024"),
          ("First Aid & CPR / BLS", "Current certification"),
          ("General Construction Induction (White Card)", "SafeWork NSW"),
        ) {
          block(below: 6pt)[
            text(weight: "bold", size: 8pt, fill: ink)[#name]
            text(size: 7.5pt, fill: ink-light)[#issuer]
          ]
        }
      ]

      #section[
        #section-label("Awards")
        #for (name, issuer) in (
          ("UTS Dean's List", "University of Technology Sydney · 2024"),
          ("Rookie of the Year", "UTS Motorsports Autonomous · 2024"),
          ("1st Place — Engineering Studies", "Sydney Catholic Schools · 2023"),
        ) {
          block(below: 6pt)[
            text(weight: "bold", size: 8pt, fill: ink)[#name]
            text(size: 7.5pt, fill: ink-light)[#issuer]
          ]
        }
      ]
    ],

    // ── MAIN (main) ─────────────────────────────────────────────────────────
    block(
      width: 100%,
      inset: (top: 20pt, right: 22pt, bottom: 24pt, left: 20pt),
    )[
      #section[
        #section-label("Profile")
        #block(
          stroke: (left: 2pt + accent),
          inset: (left: 10pt),
        )[
          #block(spacing: 0pt)[
            #set par(leading: 1.6em, spacing: 0pt)
            #text(size: 8.8pt, fill: ink-mid)[
              Penultimate-year Mechatronics Engineering student with hands-on experience in embedded sensing systems, analogue signal processing, and rapid hardware prototyping. Passionate about applying sensor fusion and AI to solve real-world infrastructure challenges. Proven ability to design, build, and iterate on multi-sensor hardware from PCB layout through to software integration — independently and as part of high-performing research teams.
            ]
          ]
        ]
      ]

      #section[
        #section-label("Relevant Experience")

        #block(below: 13pt)[
          #box(
            width: 100%,
            fill: accent-soft,
            stroke: 1pt + rgb("#9ecfd0"),
            radius: 4pt,
            inset: (top: 9pt, right: 11pt, bottom: 9pt, left: 11pt),
          )[
            #exp-header("Product Development Engineer", "May 2025 – Present", title-size: 9.5pt)
            #text(fill: accent, weight: "bold", size: 8.5pt)[
              "I did a thing" · YouTube
              #h(0.35em)
              #box(
                fill: accent,
                radius: 3pt,
                inset: (top: 1pt, bottom: 1pt, left: 6pt, right: 6pt),
              )[
                #text(
                  font: mono,
                  size: 6.8pt,
                  weight: "medium",
                  fill: white,
                  tracking: 0.5pt,
                )[5.6M+ SUBSCRIBERS]
              ]
            ]
            #v(5pt)
            #exp-bullet[Sole engineer delivering 10+ functional prototypes for one of YouTube's largest engineering channels — averaging just 30 working hours per complete project cycle (ideation → sourcing → fabrication → iteration).]
            #exp-bullet[Designed and built a wearable flotation device with integrated sail mechanism; produced an autonomous CO₂-actuated projectile system — both requiring rigorous sensor and actuator integration.]
            #exp-bullet[Full engineering autonomy across every stage; all prototypes built to withstand hours of repeated takes during professional filming.]
          ]
        ]

        #for (title, org, dates, bullets, org-size) in (
          (
            "Embedded Systems Engineer",
            "UTS Motorsports Autonomous",
            "Apr 2024 – Aug 2025",
            (
              "Developed real-time embedded firmware in C for STM32 microcontrollers on an autonomous Formula SAE vehicle, including sensor data acquisition and actuation control.",
              "Contributed to steer-by-wire system development; showcased technology at SXSW Sydney 2024 to industry professionals, receiving recognition as Rookie of the Year.",
              "Collaborated within a multidisciplinary team of 30+ across mechanical, electrical, and software subsystems — analogous to the UTS TRU / nbn multi-stakeholder structure.",
            ),
            8pt,
          ),
          (
            "Casual Academic — Mechatronics Engineering",
            "University of Technology Sydney",
            "Feb 2025 – Present",
            (
              "Tutored undergraduate cohorts in 41099 Introduction to Mechatronics Engineering, reinforcing concepts in sensor systems, embedded programming, and control theory.",
            ),
            8pt,
          ),
          (
            "Avionics Trainee",
            "UTS Rocketry Team",
            "Apr 2024 – Jan 2025",
            (
              "Prototyped avionics data loggers to capture and record in-flight sensor data (accelerometers, altimeters); attended workshops on flight data processing and analysis.",
            ),
            8pt,
          ),
        ) {
          block(below: 11pt)[
            exp-header(title, dates)
            exp-org(org, size: org-size)
            for bullet in bullets {
              exp-bullet(bullet)
            }
          ]
        }
      ]

      #section[
        #section-label("Key Technical Projects")
        #for (name, grade, bullets) in (
          (
            "Multi-Sensor PCB — Step Tracker & Sensing Platform",
            "HD — Embedded Mechatronics Studio 2025",
            (
              "Designed a compact multi-sensor PCB in Altium Designer integrating: heart rate monitor, Time-of-Flight distance sensor (secondary daughter-board soldered perpendicularly), OLED display, STM32 microcontroller, USB-C power & communication, and battery charging.",
              "Implemented a 4th-order Butterworth low-pass filter using only C0G/NP0 components for clean analogue accelerometer signal conditioning — directly applicable to non-invasive sensing pipelines.",
              "Designed for miniaturisation: 0402 SMD components, stencil-applied solder paste, hand-soldered; replaced recommended Arduino shield with integrated STM32 for enhanced performance.",
            ),
          ),
          (
            "6-DOF Robotic Arm Simulation & Control Software",
            "Distinction — Industrial Robotics 2025",
            (
              "Developed Python software to simulate and control three 6-DOF robotic arms, implementing forward/inverse kinematics and trajectory planning algorithms relevant to automated inspection pipelines.",
            ),
          ),
          (
            "Cart-Pendulum Balancing — Embedded Control System",
            "HD — Intro to Mechatronics 2024",
            (
              "Implemented a PID control loop on a physical double-pendulum-on-cart system using stepper motors and sensor feedback; designed system CAD in Fusion 360 with a custom GUI for real-time parameter tuning.",
            ),
          ),
        ) {
          block(below: 9pt)[
            box(
              width: 100%,
              fill: sidebar-bg,
              stroke: (left: 2.5pt + accent),
              radius: (top-right: 3pt, bottom-right: 3pt),
              inset: (top: 8pt, right: 10pt, bottom: 8pt, left: 10pt),
            )[
              grid(
                columns: (1fr, auto),
                column-gutter: 6pt,
                align: (left + horizon, right + horizon),
                text(weight: "bold", size: 8.8pt, fill: ink)[#name],
                project-grade(grade),
              )
              v(3pt)
              for bullet in bullets {
                project-bullet(bullet)
              }
            ]
          ]
        }
      ]

      #section[
        #section-label("Leadership & Outreach")
        #block(below: 5pt)[
          exp-header("Vice President", "Jun 2024 – Nov 2025")
          exp-org("UTS Aerial Society")
          exp-bullet[Co-founded and governed a new UTS society, managing operations, membership, and event logistics alongside academic commitments.]
        ]
        #block(below: 0pt)[
          exp-header("General Committee — STEM Outreach", "Mar – Oct 2024")
          exp-org("Engineers Without Borders, UTS Chapter")
          exp-bullet[Organised and delivered hands-on engineering workshops to 400+ students across regional NSW (Wagga Wagga) and metropolitan schools; led outreach to Colyton High School independently.]
        ]
      ]
    ],
  )
]
