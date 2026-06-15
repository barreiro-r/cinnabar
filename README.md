# cinnabar

A specialized Python tool for rendering academic and scientific articles from Markdown (specifically optimized for Obsidian workflows) into beautiful, self-contained, and interactive HTML documents.

## 🚀 Features

- **Self-Contained HTML:** Embeds all images as base64 strings, allowing you to share a single HTML file without worrying about external asset paths.
- **Scientific Figures:** Supports a custom Obsidian-style figure syntax for automatic numbering, titling, and descriptions.
- **Cross-Referencing:**
    - **Figures:** Link to figures using `\ref{fig:1.1}`.
    - **Equations:** Link to equations using `\eqref{1.1.1}` or `\ref{eq:1.1.1}`.
- **KaTeX Integration:** Native support for LaTeX math blocks (`$$...$$`) and inline math (`$...$`) with high-quality rendering.
- **Interactive Side-Navigation:**
    - Automatically generates a table of contents from headers.
    - Features a sticky sidebar with **active scroll tracking** (highlights the current section).
- **Automated Bibliography:**
    - Detects DOI links in the text.
    - **Crossref API Integration:** Optionally fetches full citation metadata (authors, title, journal, year) automatically.
- **Advanced Highlights:** Supports Obsidian-style `==highlight==` syntax with support for nested markdown (italics/bold) inside highlights.
- **Academic Design Palette:** Features a sophisticated "Cinnabar & Teal" color scheme designed for readability and professional presentation.

## 🛠️ Requirements

- Python 3.12+
- Dependencies: `requests`, `click`, `rich`, `markdown-it-py`, `jinja2`.

## 📦 Installation

1. Clone the repository to your local machine.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required packages:
   ```bash
   pip install requests click rich markdown-it-py jinja2
   ```

## 📖 Usage

Run the renderer by pointing it to your source Markdown file:

```bash
python cinnabar.py --input-file="path/to/your/article.md"
```

### Options:
- `--input-file`, `-i`: (Required) Path to the input markdown file.
- `--output-path`, `-o`: Directory to save the rendered `render.html` (defaults to current directory).
- `--fetch-citations`: Enable this flag to fetch full metadata from Crossref for DOIs found in the text.
- `--verbose`, `-v`: Enable detailed debug logging.

### Example:
```bash
python cinnabar.py --input-file="DNALM-313/PROJECT DNA-LM & PRS.md" --fetch-citations --verbose
```

## 🎨 Design Palette

The rendered output follows a specific scientific design guide:

| Element | Color | Use Case |
| :--- | :--- | :--- |
| **Cinnabar** | `#E34234` | Header numbers, Figure labels, Active Nav |
| **Vibrant Teal** | `#008080` | Links, Citations, References |
| **Deep Brick** | `#A6261B` | Highlighted text color |
| **Blush Tint** | `#FCEBE9` | Highlighted background |
| **Text Charcoal**| `#1A1C1C` | Primary body text |
| **Background** | `#FFFFFF` | Page background |

## 📝 Markdown Syntax Notes

### Figures
```markdown
![[image.png|fig:1.1|title:My Title|desc:Detailed description.]]
```

### Equation Tags
```latex
$$E = mc^2 \tag{1.1.1}$$
```

### Cross-References
- Check out the results in `\ref{fig:1.1}`.
- Derived from equation `\eqref{1.1.1}`.

---
*Created by Gemini CLI for scientific publishing workflows.*
