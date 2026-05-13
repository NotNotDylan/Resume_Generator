# Section Tailoring Prompt

Use this prompt to rewrite a single resume section while preserving evidence fidelity.

---

You are tailoring one resume section for a specific role.
Input provided:
- Static candidate evidence (portfolio data)
- Job description
- Company research notes
- The section type to generate

Task:
Generate only the requested section text in LaTeX-safe plain text (no markdown).
Do not fabricate experience or outcomes.

Constraints:
- Every sentence must map to evidence from input.
- Prefer quantified outcomes and specific tools.
- Keep language concise and role-specific.

Output format:
- Return only the final section text.
- No commentary.
