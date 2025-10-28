
# LaTeX Project Setup (VS Code + GitHub)

This repository is configured for writing and compiling LaTeX documents using **Visual Studio Code** with the **LaTeX Workshop** extension.
It also includes a **GitHub Actions workflow** that automatically builds your PDF on each push or pull request.

---

### Install a LaTeX distribution
You only need one of these:
- **macOS (recommended):**
  ```bash
  brew install --cask basictex
  sudo tlmgr update --self
  sudo tlmgr install latexmk xetex amsmath geometry hyperref fancyhdr biblatex fontspec xcolor listings graphics

* **Windows:** [MiKTeX](https://miktex.org/download)
* **Linux:** [TeX Live](https://www.tug.org/texlive/)

---

### Install VS Code & Extension

1. Install **[Visual Studio Code](https://code.visualstudio.com/)**.
2. In VS Code, go to **Extensions** (`Ctrl+Shift+X` / `Cmd+Shift+X`) → search **“LaTeX Workshop”** → install it.

---

### Project structure

```
repo/
├─ report/
│  ├─ main.tex
│  ├─ references.bib
│  └─ out/                # compiled PDFs + aux files (auto-created)
├─ .vscode/
│  └─ settings.json       # VS Code config
└─ .github/workflows/
   └─ latex.yml           # GitHub Actions CI build
```

---

## VS Code Configuration

Create or edit **`.vscode/settings.json`** with:

```json
{
  "latex-workshop.latex.outDir": "%DIR%/out",

  "latex-workshop.latex.tools": [
    {
      "name": "latexmk",
      "command": "latexmk",
      "args": ["-pdf", "-synctex=1", "-interaction=nonstopmode", "-outdir=%OUTDIR%", "%DOC%"]
    },
    {
      "name": "xelatex",
      "command": "xelatex",
      "args": ["-synctex=1", "-interaction=nonstopmode", "-output-directory=%OUTDIR%", "%DOC%"]
    }
  ],

  "latex-workshop.latex.recipes": [
    { "name": "latexmk 🔁", "tools": ["latexmk"] },
    { "name": "xelatex 🔤", "tools": ["xelatex"] }
  ],

  "latex-workshop.latex.autoClean.run": "onBuilt",
  "latex-workshop.latex.clean.fileTypes": [
    "*.aux", "*.bbl", "*.bcf", "*.blg", "*.fdb_latexmk", "*.fls",
    "*.log", "*.out", "*.run.xml", "*.synctex.gz", "*.toc", "*.lot", "*.lof"
  ]
}
```

### Usage

* Open `report/main.tex`
* Build → **Ctrl+Alt+B** (Windows/Linux) or **⌘+Option+B** (macOS)
* PDF output appears in VS Code’s preview tab
* All temporary files go into `report/out/`

---

## GitHub Actions (Automatic PDF Build)

The workflow in `.github/workflows/latex.yml` automatically compiles your document in the cloud and uploads the resulting PDF.

After each push/PR, the workflow run will show a **Download artifact** link for the generated PDF.
