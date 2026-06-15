import os
import re
import base64
import time
from datetime import datetime
import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from markdown_it import MarkdownIt
from jinja2 import Template

# Initialize Rich Console
console = Console()

def fetch_crossref_citation(doi_url, debug=False):
    """Fetches citation metadata from Crossref API."""
    doi = doi_url.replace("https://doi.org/", "").strip()
    api_url = f"https://api.crossref.org/works/{doi}"
    
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()['message']
            
            title_list = data.get('title', [])
            title = title_list[0] if title_list else "Unknown Title"
            
            # Authors
            authors_data = data.get('author', [])
            authors = []
            for author in authors_data:
                family = author.get('family', '')
                given = author.get('given', '')
                if family and given:
                    authors.append(f"{family}, {given[0]}.")
                elif family:
                    authors.append(family)
            
            author_str = ", ".join(authors)
            if not author_str:
                author_str = "Unknown Author"
                
            # Year
            issued_parts = data.get('issued', {}).get('date-parts', [])
            issued_year = issued_parts[0][0] if issued_parts and issued_parts[0] else None
            year_str = f"({issued_year})" if issued_year else ""
            
            # Container (Journal)
            container_list = data.get('container-title', [])
            container_title = container_list[0] if container_list else ""
            container_str = f"<i>{container_title}</i>." if container_title else ""
            
            citation = f"{author_str} {year_str}. {title}. {container_str} <a href='{doi_url}'>{doi_url}</a>"
            log_debug(f"Fetched citation for {doi}", debug=debug)
            return citation
        else:
            log_debug(f"Crossref API returned {response.status_code} for {doi}", debug=debug)
    except Exception as e:
        log_debug(f"Error fetching citation for {doi}: {e}", debug=debug)
        
    return f"<a href='{doi_url}'>{doi_url}</a>"

def log_debug(message: str, data: any = None, debug: bool = False):
    """Logs a debug message if debug mode is enabled."""
    if debug:
        console.print(f"[gray]\\[DEBUG][/gray] {message}")
        if data:
            console.print(data)

def print_header():
    """Prints a styled header to the console."""
    header_text = Text("CINNABAR", style="bold #E34234", justify="center")
    console.print(Panel(header_text, border_style="#E34234", expand=False))
    console.print()

def print_panel_end_message(success: bool, duration: float):
    """Prints a summary of execution details inside a Panel."""
    completion_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if success:
        status_message = "[green]Script Finished Successfully[/green]"
    else:
        status_message = "[red]Script Failed[/red]"

    summary_message = (
        f"[bold]{status_message}[/bold]\n"
        f"Completion Time : {completion_timestamp}\n"
        f"Total Duration  : [cyan]{duration:.2f} seconds[/cyan]"
    )

    console.print(
        Panel.fit(
            summary_message,
            title="[blue]Execution Summary[/blue]",
            border_style="blue",
            padding=(1, 2)
        )
    )

def get_image_base64(figures_dir: str, filename: str, debug: bool):
    """Encodes an image to a base64 string."""
    path = os.path.join(figures_dir, filename.strip())
    if not os.path.exists(path):
        console.print(f"[yellow]\\[WARN][/yellow] Figure not found: {path}")
        return ""
    
    ext = os.path.splitext(filename)[1].lower().strip('.')
    mime_type = f"image/{ext}"
    if ext == "jpg": mime_type = "image/jpeg"
    
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    
    log_debug(f"Embedded image: {filename}", debug=debug)
    return f"data:{mime_type};base64,{data}"

@click.command()
@click.option('--input-file', '-i', required=True, type=click.Path(exists=True), help="Path to the input markdown file.")
@click.option('--output-path', '-o', type=click.Path(), help="Directory to save the rendered HTML.")
@click.option('--verbose', '-v', is_flag=True, help="Show verbose debugging output.")
@click.option('--fetch-citations', is_flag=True, help="Fetch citation metadata from Crossref API instead of just showing DOI links.")
def main(input_file, output_path, verbose, fetch_citations):
    """Renders a Markdown article with figures, math, and bibliography into a self-contained HTML file."""
    start_time = time.time()
    print_header()
    console.print(f"[cyan]\\[INFO][/cyan] Starting render of {input_file}")

    success = False
    try:
        # 1. Setup paths
        input_abs = os.path.abspath(input_file)
        input_dir = os.path.dirname(input_abs)
        input_basename = os.path.splitext(os.path.basename(input_file))[0]
        figures_dir = os.path.join(input_dir, "figures")
        
        output_dir = os.path.abspath(output_path) if output_path else os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        final_output_path = os.path.join(output_dir, "render.html")

        log_debug(f"Resolved input: {input_abs}", debug=verbose)
        log_debug(f"Output path: {final_output_path}", debug=verbose)

        # 2. Read content
        with open(input_abs, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # --- Remove Obsidian Comments ---
            progress.add_task(description="Removing comments...", total=None)
            content = re.sub(r'%%.*?%%', '', content, flags=re.DOTALL)
            
            # --- Figures ---
            progress.add_task(description="Processing figures...", total=None)
            FIG_PATTERN = r'!?\[\[(.*?)\]\]'
            
            def format_fig_num(num_str):
                num_str = num_str.strip()
                if '.' in num_str:
                    parts = num_str.split('.')
                    return f"{int(parts[0]):02d}.{parts[1]}"
                else:
                    return f"{int(num_str):02d}"

            def replace_fig(match):
                inner_text = match.group(1)
                
                # If it doesn't look like our figure format with pipes, skip it
                if '|' not in inner_text:
                    return match.group(0)
                    
                parts = inner_text.split('|')
                filename = parts[0].strip()
                
                # Parse attributes into a dict
                attrs = {'fig': '', 'title': '', 'desc': ''}
                for part in parts[1:]:
                    if ':' in part:
                        key, val = part.split(':', 1)
                        attrs[key.strip().lower()] = val.strip()
                    else:
                        # Some markdown editors append sizes like '|500' at the end, just ignore them
                        pass
                
                # Must have at least a fig number to be processed as our figures
                if not attrs['fig']:
                    return match.group(0)
                
                img_data = get_image_base64(figures_dir, filename, verbose)
                
                display_num = format_fig_num(attrs['fig'])
                fig_label = f"Figure {display_num}"
                
                title_text = f" {attrs['title']}" if attrs['title'] else ""
                desc_text = f". {attrs['desc']}" if attrs['desc'] else ""
                
                return f"""
<figure class="figure-container" id="fig-{display_num}">
    <img src="{img_data}" alt="{attrs['title']}">
    <figcaption>
        <span class="fig-label">{fig_label}</span>{title_text}{desc_text}
    </figcaption>
</figure>
"""
            content = re.sub(FIG_PATTERN, replace_fig, content)

            # --- Figure References (\ref{fig:...}) ---
            progress.add_task(description="Processing figure references...", total=None)
            def replace_fig_ref(match):
                fig_num = match.group(1)
                display_num = format_fig_num(fig_num)
                return f'<a href="#fig-{display_num}" class="fig-ref">Figure {display_num}</a>'
            
            # Handle potential $...$ wrapping and standard \ref
            content = re.sub(r'\$?\\ref\{fig:(.*?)\}\$?', replace_fig_ref, content)

            # --- Equation References ---
            def replace_eq_ref(match):
                eq_tag = match.group(1)
                eq_id = f"eq-{re.sub(r'[^a-z0-9]+', '-', eq_tag.lower()).strip('-')}"
                return f'<a href="#{eq_id}" class="eq-ref">(Equation {eq_tag})</a>'
            
            # Support \eqref{1.1.1} and \ref{eq:1.1.1}, handling optional $ wrapping
            content = re.sub(r'\$?\\eqref\{(.*?)\}\$?', replace_eq_ref, content)
            content = re.sub(r'\$?\\ref\{eq:(.*?)\}\$?', replace_eq_ref, content)

            # --- Comments / Highlights ---
            progress.add_task(description="Processing comments...", total=None)
            def replace_highlight(match):
                inner_content = match.group(1)
                # Leniently handle italics and bold inside highlights
                inner_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', inner_content)
                inner_content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', inner_content)
                inner_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', inner_content)
                inner_content = re.sub(r'_(.*?)_', r'<em>\1</em>', inner_content)
                return f'<mark>{inner_content}</mark>'
            
            # Use <mark> for inline highlights (==...==)
            # We only match if there are no newlines between == to keep it inline
            COMMENT_PATTERN = r'==([^=\n]+)==(?!=)'
            content = re.sub(COMMENT_PATTERN, replace_highlight, content)

            # --- Bibliography ---
            progress.add_task(description="Building bibliography...", total=None)
            DOI_REGEX = re.compile(r'https://doi\.org/10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
            
            found_dois = []
            for match in DOI_REGEX.finditer(content):
                doi = match.group(0).rstrip(').,')
                if doi not in found_dois:
                    found_dois.append(doi)
            
            log_debug(f"Found {len(found_dois)} unique DOIs", debug=verbose)
            
            bibliography = []
            placeholder_map = {}
            for i, doi in enumerate(found_dois, 1):
                token = f"__DOI_TOKEN_{i}__"
                placeholder_map[token] = f'<a href="{doi}" class="citation">[{i}]</a>'
                
                if fetch_citations:
                    progress.update(progress.task_ids[-1], description=f"Fetching citation {i}/{len(found_dois)}...")
                    citation_text = fetch_crossref_citation(doi, verbose)
                else:
                    citation_text = f'<a href="{doi}">{doi}</a>'
                    
                bibliography.append(f'<li id="ref-{i}">{citation_text}</li>')
                
                # Surgical replacement:
                # 1. Replace (DOI) with token
                content = content.replace(f"({doi})", token)
                # 2. Replace standalone DOI
                content = content.replace(doi, token)

            # Finalize DOI tags
            for token, html in placeholder_map.items():
                content = content.replace(token, html)

            # Post-process multiple citations ([1], [2])
            content = re.sub(r'\((<a href=".*?" class="citation">\[\d+\]</a>(?:,\s*<a href=".*?" class="citation">\[\d+\]</a>)*)\)', r'\1', content)

            # --- Math Protection ---
            progress.add_task(description="Protecting math blocks...", total=None)
            math_blocks = []
            eq_map = {}
            def replace_math_block(m):
                content_math = m.group(0)
                # Check for tag
                tag_match = re.search(r'\\tag\{(.*?)\}', content_math)
                if tag_match:
                    tag_val = tag_match.group(1)
                    eq_id = f"eq-{re.sub(r'[^a-z0-9]+', '-', tag_val.lower()).strip('-')}"
                    eq_map[tag_val] = eq_id
                    math_blocks.append(f'<div id="{eq_id}" class="equation-wrapper">{content_math}</div>')
                else:
                    math_blocks.append(content_math)
                return f"@@MATH_BLOCK_{len(math_blocks)-1}@@"
            
            content = re.sub(r'\$\$.*?\$\$', replace_math_block, content, flags=re.DOTALL)
            
            math_inline = []
            def replace_math_inline(m):
                math_inline.append(m.group(0))
                return f"@@MATH_INLINE_{len(math_inline)-1}@@"
            
            content = re.sub(r'\$.*?\$', replace_math_inline, content)

            # --- Render Markdown ---
            progress.add_task(description="Rendering HTML...", total=None)
            md = MarkdownIt("js-default", {"html": True})
            html_body = md.render(content)

            # --- Extract Nav and Add IDs ---
            nav_items = []
            def add_header_ids(match):
                tag = match.group(1)
                inner = match.group(2)
                # Clean text for ID and Nav
                text_only = re.sub(r'<[^>]*>', '', inner).strip()
                header_id = re.sub(r'[^a-z0-9]+', '-', text_only.lower()).strip('-')
                
                # Ensure unique ID
                base_id = header_id
                counter = 1
                while any(item['id'] == header_id for item in nav_items):
                    header_id = f"{base_id}-{counter}"
                    counter += 1
                
                nav_items.append({'tag': tag, 'text': text_only, 'id': header_id})
                return f'<{tag} id="{header_id}">{inner}</{tag}>'

            html_body = re.sub(r'<(h[1-3])>(.*?)</\1>', add_header_ids, html_body)

            # Add References to nav if exists
            if bibliography:
                nav_items.append({'tag': 'h2', 'text': 'References', 'id': 'references-section'})

            # --- Style Heading Numbers ---
            # Wrap numbers at the start of headers (e.g., "1. ", "1.1 ") in a span
            html_body = re.sub(r'(<(h[1-6])[^>]*>)((\d+\.?)+)', r'\1<span class="header-num">\3</span>', html_body)

            # --- Restore Math ---
            for i, math in enumerate(math_blocks):
                html_body = html_body.replace(f"@@MATH_BLOCK_{i}@@", math)
            for i, math in enumerate(math_inline):
                html_body = html_body.replace(f"@@MATH_INLINE_{i}@@", math)

        # 4. HTML Template
        template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    
    <!-- KaTeX CSS and JS for auto-rendering math -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ],
            macros: { '\\\\RR': '\\\\mathbb{R}' }
        });"></script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Sorts+Mill+Goudy:ital@0;1&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Sorts Mill Goudy', serif; line-height: 1.6; color: #1A1C1C; margin: 0; padding: 0; background-color: #FFFFFF; }
        .layout-wrapper { display: flex; max-width: 1200px; margin: 0 auto; padding: 60px 20px; position: relative; }
        
        /* Navigation Sidebar */
        .side-nav { width: 200px; position: sticky; top: 40px; height: calc(100vh - 80px); overflow-y: auto; padding-right: 15px; border-right: 1px solid #D1D5D5; font-family: 'Montserrat', sans-serif; }
        .nav-title { font-family: 'Sorts Mill Goudy', serif; font-size: 0.9em; color: #1A1C1C; margin-bottom: 15px; text-align: right; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #E34234; padding-bottom: 6px; }
        .side-nav ul { list-style: none; padding: 0; margin: 0; text-align: right; }
        .side-nav li { margin-bottom: 4px; }
        .side-nav a { color: #888; text-decoration: none; font-size: 0.8em; transition: all 0.3s ease; display: block; padding: 2px 0; border-right: 3px solid transparent; padding-right: 10px; margin-right: -1px; }
        .side-nav a:hover { color: #F18076; }
        .side-nav li.active a { color: #E34234; border-right-color: #E34234; font-weight: 600; opacity: 1; }
        .nav-h1 { margin-bottom: 10px !important; }
        .nav-h1 a { font-weight: 700; color: #1A1C1C !important; font-size: 0.9em; }
        .nav-h2 { margin-top: 6px; }
        .nav-h2 a { font-size: 0.82em; font-weight: 500; color: #444; }
        .nav-h3 { padding-right: 0; }
        .nav-h3 a { font-size: 0.7em; opacity: 0.85; }

        /* Main Content */
        main { flex: 1; max-width: 650px; padding-left: 60px; }

        h1 { font-family: 'Sorts Mill Goudy', serif; color: #1A1C1C; margin-top: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.1em; font-weight: normal; }
        h2 { font-family: 'Montserrat', sans-serif; color: #1A1C1C; margin-top: 1.5em; font-weight: normal; border-bottom: 1px solid #D1D5D5; padding-bottom: 5px; }
        h3, h4, h5, h6 { font-family: 'Montserrat', sans-serif; color: #1A1C1C; margin-top: 1.5em; margin-bottom: 0; font-weight: normal; }
        .header-num { color: #E34234; margin-right: 0.2em; font-family: 'Montserrat', sans-serif; font-weight: normal; }
        .figure-container { margin: 40px 0; text-align: center; background: #FFFFFF; padding: 0; border-radius: 0; box-shadow: none; border: none; }
        .figure-container img { max-width: 100%; max-height: 500px; width: auto; height: auto; border-radius: 0; object-fit: contain; }
        figcaption { margin-top: 15px; font-size: 0.9em; color: #1A1C1C; text-align: left; }
        .fig-label { font-family: 'Montserrat', sans-serif; color: #E34234; font-weight: normal; font-size: 0.85em; letter-spacing: 0.1em; text-transform: uppercase; }
        .fig-ref, .eq-ref { color: #008080; font-weight: bold; text-decoration: none; border-bottom: 1px dashed #008080; }
        .fig-ref:hover, .eq-ref:hover { color: #E34234; border-bottom-style: solid; }
        .equation-wrapper { margin: 20px 0; padding: 10px 0; }
        .comment-box { background-color: #FCEBE9; border-left: 4px solid #E34234; padding: 12px 15px; margin: 20px 0; font-style: italic; color: #A6261B; }
        mark { background-color: #FCEBE9; color: #A6261B; padding: 2px 4px; border-radius: 2px; }
        .bibliography { margin-top: 60px; border-top: 2px solid #D1D5D5; padding-top: 30px; font-family: 'Montserrat', sans-serif; font-size: 0.9em; }
        .citation { font-family: 'Montserrat', sans-serif !important; font-weight: normal; color: #008080; text-decoration: none; transition: color 0.3s ease; font-size: 0.75em; vertical-align: super; }
        .citation:hover { color: #E34234; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; border: 1px solid #D1D5D5; }
        th, td { border: 1px solid #D1D5D5; padding: 8px; text-align: left; }
        th { background-color: #F0F2F2; font-family: 'Montserrat', sans-serif; font-size: 0.9em; color: #1A1C1C; }
        a { color: #008080; text-decoration: none; }
        a:hover { color: #E34234; text-decoration: underline; }

        @media (max-width: 900px) {
            .side-nav { display: none; }
            main { padding-left: 0; margin: 0 auto; }
            .layout-wrapper { padding: 40px 20px; }
        }
    </style>
</head>
<body>
    <div class="layout-wrapper">
        <nav class="side-nav">
            <div class="nav-title">{{ title }}</div>
            <ul>
                {% for item in nav_items %}
                <li class="nav-{{ item.tag }}"><a href="#{{ item.id }}">{{ item.text }}</a></li>
                {% endfor %}
            </ul>
        </nav>
        
        <main>
            <h1>{{ title }}</h1>
            {{ body }}
            
            {% if bibliography %}
            <div class="bibliography">
                <h2 id="references-section">References</h2>
                <ol>
                    {% for ref in bibliography %}
                    {{ ref }}
                    {% endfor %}
                </ol>
            </div>
            {% endif %}
        </main>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const observerOptions = {
                root: null,
                rootMargin: '-10% 0px -80% 0px',
                threshold: 0
            };

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const id = entry.target.getAttribute('id');
                        document.querySelectorAll('.side-nav li').forEach(li => {
                            li.classList.remove('active');
                            if (li.querySelector('a').getAttribute('href') === `#${id}`) {
                                li.classList.add('active');
                            }
                        });
                    }
                });
            }, observerOptions);

            document.querySelectorAll('h1, h2, h3').forEach((header) => {
                observer.observe(header);
            });
        });
    </script>
</body>
</html>
""")
        final_html = template.render(title=input_basename, body=html_body, bibliography=bibliography, nav_items=nav_items)

        with open(final_output_path, "w", encoding='utf-8') as f:
            f.write(final_html)

        console.print(f"[cyan]\\[INFO][/cyan] Rendered HTML written to {final_output_path}")
        success = True

    except Exception as e:
        console.print(f"[red]\\[ERROR][/red] {str(e)}")
        if verbose:
            console.print_exception()
        success = False
    finally:
        duration = time.time() - start_time
        print_panel_end_message(success, duration)

if __name__ == "__main__":
    main()

# Example Usage:
# python render_article.py --input-file="DNALM-313/PROJECT DNA-LM & PRS.md" --output-path="." --verbose
