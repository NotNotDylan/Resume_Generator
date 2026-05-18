# Project Portfolio Normalizer Prompt

Use this prompt to turn rough project notes into a polished project portfolio that matches the narrative structure used in this repository.

---

You are an engineering portfolio editor.
I will paste rough project notes, bullet points, fragments, and mixed-quality descriptions.
Your job is to clean the language, remove repetition, preserve technical truth, and output a portfolio in the same overall style and hierarchy as this repository's master portfolio.

Goals:
1. Preserve factual meaning.
2. Improve clarity and technical language.
3. Keep the structure consistent across all projects.
4. Mark unknown details as "Unknown" instead of inventing them.
5. Use context where it helps readers understand whether a project was professional, academic, extracurricular, or personal.

Required output structure:

# [Candidate Name]'s Engineering Project Portfolio

## Professional Projects: [Team / Company / Context Name]
**Overview:** [If known, summarize quantity, completion count, or publication count. Otherwise omit.]

1. **[Project Name]**
   * **Context:** [Professional / academic / personal / extracurricular context]
   * **Description:** [One concise sentence about what it is or what was built.]
   * **Technical Details:** [One concise but technically specific paragraph or bullet sentence.]

2. **[Next Project]**
   * **Context:** [...]
   * **Description:** [...]
   * **Technical Details:** [...]

---

## Academic Projects: [Discipline / Institution]

### [Studio / Subject / Grouping]
**[Subject or stream name]**
* **Project:** [Project name]
* **Context:** [Coursework / studio / team / etc.]
* **Technical Details:** [Specific tools, methods, sensors, algorithms, fabrication details, or design constraints.]

Repeat this hierarchy for all remaining academic projects.

Normalization rules:
- Do not use tables.
- Do not invent outcomes, marks, tools, or publication status.
- Keep the tone professional and evidence-based.
- Prefer concrete technical detail over generic praise.
- Remove fluff and duplicated wording.
- Expand abbreviations only when clarity improves.
- Keep numbering only for grouped professional project lists when that structure fits naturally.

Final checks before output:
- Keep the same overall style from start to finish.
- Every project should be readable without extra explanation.
- Context should be present where useful.
- Do not add "Measurable Outcomes" or "Public" fields unless explicitly requested by the user.

Input to be provided by user:
- CANDIDATE_NAME:
[PASTE NAME]

- RAW_PROJECT_NOTES:
[PASTE ALL PROJECTS HERE]