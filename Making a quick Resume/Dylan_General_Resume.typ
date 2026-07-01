// Dylan Bitar — General Resume (pixel-matched to Dylan_General_Resume.html)
// Compile: typst compile Dylan_General_Resume.typ Dylan_General_Resume.pdf --root . --font-path fonts

#let ink         = rgb("#0f1923")
#let ink-mid     = rgb("#3a4a5a")
#let ink-light   = rgb("#6b7f8f")
#let accent      = rgb("#0b6e70")
#let accent-soft = rgb("#e6f4f4")
#let rule-color  = rgb("#c9d6da")
#let sidebar-bg  = rgb("#f4f7f8")

#let lato     = "Lato"
#let garamond = "Cormorant Garamond"
#let mono     = "JetBrains Mono"

#set page(paper: "a4", margin: 0pt)
#set text(font: lato, size: 9.2pt, fill: ink, lang: "en")
#set par(leading: 1.5em, justify: false, spacing: 0pt)

// CSS px → print pt (96dpi CSS px × 0.75 = 72dpi pt)
#let px(n) = n * 0.75pt

// ── Helpers (CSS-matched) ─────────────────────────────────────────────────────

#let section-label(title) = {
  block(below: px(7))[
    #text(
      font: mono,
      size: 6.8pt,
      weight: "medium",
      fill: accent,
      tracking: px(1.8),
    )[#upper(title)]
    #v(px(4))
    #line(length: 100%, stroke: 0.75pt + accent)
  ]
}

#let section(body) = {
  block(below: px(16))[
    #body
  ]
}

#let metric-chip(content) = box(
  fill: accent-soft,
  stroke: 0.5pt + rgb("#9ecfd0"),
  radius: px(3),
  inset: (top: px(2), bottom: px(2), left: px(6), right: px(6)),
)[
  #text(font: mono, size: 7pt, weight: "medium", fill: accent)[#content]
]

#let tag(content, highlight: false) = box(
  fill: if highlight { accent-soft } else { white },
  stroke: 0.5pt + if highlight { rgb("#9ecfd0") } else { rule-color },
  radius: px(3),
  inset: (top: px(2), bottom: px(2), left: px(6), right: px(6)),
)[
  #text(
    size: 7.5pt,
    weight: if highlight { "bold" } else { "regular" },
    fill: if highlight { accent } else { ink-mid },
  )[#content]
]

#let skill-tags(items, highlights) = [
  #set par(spacing: px(3), leading: 0.7em)
  #for (i, item) in items.enumerate() {
    box(outset: (right: px(3), bottom: px(3)))[
      #tag(item, highlight: i in highlights)
    ]
  }
]

#let exp-bullet(body) = block(below: px(2))[
  #grid(
    columns: (px(10), 1fr),
    column-gutter: 0pt,
    align: (left + top, left + top),
    [#text(fill: accent, weight: "bold")[›]],
    [#text(size: 8.3pt, fill: ink-mid)[#body]],
  )
]

#let project-bullet(body) = block(below: 0pt)[
  #grid(
    columns: (px(10), 1fr),
    column-gutter: 0pt,
    align: (left + top, left + top),
    pad(left: px(1))[#text(fill: accent, weight: "bold", size: 11pt)[·]],
    [#text(size: 8pt, fill: ink-mid)[#body]],
  )
]

#let exp-header(title, dates, title-size: 9pt) = [
  #grid(
    columns: (1fr, auto),
    column-gutter: px(6),
    align: (left + horizon, right + horizon),
    [#text(weight: "bold", size: title-size, fill: ink)[#title]],
    [#text(font: mono, size: 7pt, fill: ink-light)[#dates]],
  )
  #v(px(2))
]

#let exp-org(content, size: 8pt) = block(below: px(4))[
  #text(fill: accent, weight: "bold", size: size)[#content]
]

#let project-grade(content) = box(
  fill: accent-soft,
  stroke: 0.5pt + rgb("#9ecfd0"),
  radius: px(3),
  inset: (top: px(1), bottom: px(1), left: px(5), right: px(5)),
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
        inset: (top: px(22), right: px(26), bottom: px(18), left: px(26)),
        stroke: (bottom: px(3) + accent),
      )[
        #grid(
          columns: (68mm, 1fr),
          column-gutter: 0pt,
          align: (left + top, left + bottom),
          pad(right: px(16))[
            #text(
              font: garamond,
              size: 28pt,
              weight: "semibold",
              fill: white,
              tracking: px(-0.5),
            )[Dylan Bitar]
            #v(px(3))
            #text(
              font: mono,
              size: 7pt,
              fill: rgb("#ffffff73"),
              tracking: px(0.5),
            )[HE / HIM]
          ],
          pad(bottom: px(6))[
            #text(
              font: mono,
              size: 8.5pt,
              weight: "medium",
              fill: rgb("#a8c8ca"),
              tracking: px(0.3),
            )[Mechatronics Engineering (Hons) · UTS | Sensing & Embedded Systems]
            #v(px(8))
            #box(inset: 0pt)[
              #for (i, item) in (
                "possibly.a.dylan@gmail.com",
                "linkedin.com/in/dylan-bitar",
                "Student No. 25308685",
              ).enumerate() {
                if i > 0 { h(px(18)) }
                text(size: 7.8pt, fill: rgb("#ffffffa6"))[
                  #text(fill: accent, weight: "bold")[▪]#h(px(4))#item
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
      inset: (top: px(20), right: px(18), bottom: px(24), left: px(18)),
    )[
      #section[
        #section-label("Education")
        #block(below: px(10))[
          #text(weight: "bold", size: 8.5pt)[University of Technology Sydney]
          #v(px(1))
          #block(spacing: 0pt)[
            #set par(leading: 1.4em, spacing: 0pt)
            #text(size: 8pt, fill: ink-mid)[
              B.Eng (Hons) / Dip. Professional Engineering Practice \
              Major: Mechatronic Engineering
            ]
          ]
          #v(px(2))
          #text(font: mono, size: 7pt, fill: ink-light)[Jan 2024 – Nov 2029 (expected)]
          #v(px(4))
          #box(inset: 0pt)[
            #metric-chip[WAM 81.12]
            #h(px(8))
            #metric-chip[GPA 5.92]
          ]
        ]
        #block(below: 0pt)[
          #text(weight: "bold", size: 8.5pt)[St Mary's Cathedral College]
          #v(px(1))
          #block(spacing: 0pt)[
            #set par(leading: 1.4em, spacing: 0pt)
            #text(size: 8pt, fill: ink-mid)[
              High School Diploma \
              1st — Engineering Studies, Sydney Catholic Schools
            ]
          ]
          #v(px(2))
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
          block(below: px(4))[
            #grid(
              columns: (1fr, auto),
              column-gutter: px(4),
              align: (left + horizon, right + horizon),
              [#text(size: 7.8pt, fill: ink-mid)[#name]],
              [#text(font: mono, size: 6.8pt, weight: "medium", fill: accent)[#grade]],
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
          block(below: px(9))[
            #text(weight: "bold", size: 7.5pt, fill: ink-mid, tracking: px(0.5))[#upper(group)]
            #v(px(4))
            #skill-tags(items, highlights)
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
          block(below: px(6))[
            #text(weight: "bold", size: 8pt, fill: ink)[#name]
            #block(spacing: 0pt)[
              #text(size: 7.5pt, fill: ink-light)[#issuer]
            ]
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
          block(below: px(6))[
            #text(weight: "bold", size: 8pt, fill: ink)[#name]
            #block(spacing: 0pt)[
              #text(size: 7.5pt, fill: ink-light)[#issuer]
            ]
          ]
        }
      ]
    ],

    // ── MAIN (main) ─────────────────────────────────────────────────────────
    block(
      width: 100%,
      inset: (top: px(20), right: px(22), bottom: px(24), left: px(20)),
    )[
      #section[
        #section-label("Profile")
        #block(
          stroke: (left: px(2) + accent),
          inset: (left: px(10)),
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

        #block(below: px(13))[
          #box(
            width: 100%,
            fill: accent-soft,
            stroke: 1pt + rgb("#9ecfd0"),
            radius: px(4),
            inset: (top: px(9), right: px(11), bottom: px(9), left: px(11)),
          )[
            #exp-header("Product Development Engineer", "May 2025 – Present", title-size: 9.5pt)
            #text(fill: accent, weight: "bold", size: 8.5pt)[
              "I did a thing" · YouTube
              #h(0.35em)
              #box(
                fill: accent,
                radius: px(3),
                inset: (top: px(1), bottom: px(1), left: px(6), right: px(6)),
              )[
                #text(
                  font: mono,
                  size: 6.8pt,
                  weight: "medium",
                  fill: white,
                  tracking: px(0.5),
                )[5.6M+ SUBSCRIBERS]
              ]
            ]
            #v(px(5))
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
          block(below: px(11))[
            #exp-header(title, dates)
            #exp-org(org, size: org-size)
            #for bullet in bullets [
              #exp-bullet(bullet)
            ]
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
          block(below: px(9))[
            #box(
              width: 100%,
              fill: sidebar-bg,
              stroke: (left: px(2.5) + accent),
              radius: (top-right: px(3), bottom-right: px(3)),
              inset: (top: px(8), right: px(10), bottom: px(8), left: px(10)),
            )[
              #grid(
                columns: (1fr, auto),
                column-gutter: px(6),
                align: (left + horizon, right + horizon),
                [#text(weight: "bold", size: 8.8pt, fill: ink)[#name]],
                [#project-grade(grade)],
              )
              #v(px(3))
              #for bullet in bullets [
                #project-bullet(bullet)
              ]
            ]
          ]
        }
      ]

      #section[
        #section-label("Leadership & Outreach")
        #block(below: px(5))[
          #exp-header("Vice President", "Jun 2024 – Nov 2025")
          #exp-org("UTS Aerial Society")
          #exp-bullet[Co-founded and governed a new UTS society, managing operations, membership, and event logistics alongside academic commitments.]
        ]
        #block(below: 0pt)[
          #exp-header("General Committee — STEM Outreach", "Mar – Oct 2024")
          #exp-org("Engineers Without Borders, UTS Chapter")
          #exp-bullet[Organised and delivered hands-on engineering workshops to 400+ students across regional NSW (Wagga Wagga) and metropolitan schools; led outreach to Colyton High School independently.]
        ]
      ]
    ],
  )
]
