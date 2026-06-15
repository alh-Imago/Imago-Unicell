# Papers

Each subfolder is self-contained — draft, data, and figures together.

```
paper_xxx/
  draft.md          ← working draft (Markdown, converts to LaTeX/PDF)
  notes.md          ← scratch, ideas, reviewer responses, open questions
  data/             ← raw measurements, CSV, JSON results
  figures/          ← generated plots, diagrams, SVG/PNG
  refs.bib          ← BibTeX for this paper
```

Nothing in this folder is picked up by the manual build.
`docs/PAPER_DRAFT.md` is the exception — it lives in docs/ so the manual
§11 panel can render it directly.

See `PAPERS.md` for status, arguments, and dependencies across all papers.
