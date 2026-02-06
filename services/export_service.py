"""
Export Service for InstaSchool
Provides PDF, HTML, and Markdown export functionality using pure Python libraries
"""

import os
import io
import json
import base64
import tempfile
import html
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from fpdf import FPDF
import markdown
from PIL import Image


class CurriculumPDF(FPDF):
    """Custom PDF class for curriculum export"""

    _UNICODE_REPLACEMENTS = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u00a0": " ",
    }

    def __init__(self, curriculum_title: str = "InstaSchool Curriculum"):
        super().__init__()
        self.curriculum_title = curriculum_title
        self.set_auto_page_break(auto=True, margin=15)

    def pdf_text(self, value: Any) -> str:
        """Best-effort text conversion for core PDF fonts (latin-1)."""
        if value is None:
            return ""
        text = value if isinstance(value, str) else str(value)
        for src, dst in self._UNICODE_REPLACEMENTS.items():
            text = text.replace(src, dst)
        text = self._wrap_long_runs(text, max_run=60)
        return text.encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def _wrap_long_runs(text: str, *, max_run: int = 60) -> str:
        """Insert spaces into very long runs so `multi_cell` can wrap (e.g., URLs)."""
        if not text or max_run <= 0:
            return text
        out = []
        run = ""
        for ch in text:
            if ch.isspace():
                if run:
                    out.append(run)
                    run = ""
                out.append(ch)
                continue
            run += ch
            if len(run) >= max_run:
                out.append(run)
                out.append(" ")
                run = ""
        if run:
            out.append(run)
        return "".join(out)

    def header(self):
        """Add header to each page"""
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(41, 98, 255)  # Blue color
        self.cell(0, 10, self.pdf_text(self.curriculum_title), 0, 1, "C")
        self.ln(5)

    def footer(self):
        """Add footer to each page"""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)  # Gray
        self.cell(0, 10, self.pdf_text(f"Page {self.page_no()}"), 0, 0, "C")

    def chapter_title(self, title: str, level: int = 1):
        """Add a chapter/section title"""
        self.set_font("Helvetica", "B", 16 if level == 1 else 14)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(200, 220, 255)  # Light blue background
        self.cell(0, 10, self.pdf_text(title), 0, 1, "L", 1)
        self.ln(4)

    def chapter_body(self, text: str):
        """Add body text to chapter"""
        self.set_font("Helvetica", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, self.pdf_text(text))
        self.ln(3)

    def add_image_from_base64(self, base64_data: str, w: int = 150):
        """Add image from base64 data"""
        tmp_path = None
        try:
            # Create temporary file for image
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                # Decode base64 and write to temp file
                if "," in base64_data:
                    base64_data = base64_data.split(",")[1]
                img_data = base64.b64decode(base64_data)
                tmp.write(img_data)
                tmp_path = tmp.name

            # Add image to PDF
            self.image(tmp_path, x=30, w=w)
            self.ln(5)
        except Exception as e:
            # If image fails, add error message
            self.set_font("Helvetica", "I", 10)
            self.set_text_color(255, 0, 0)
            self.cell(0, 10, self.pdf_text(f"[Image could not be loaded: {str(e)}]"), 0, 1)
            self.ln(3)
        finally:
            # Always clean up temp file, even on exception
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # Best effort cleanup


class CurriculumExporter:
    """Main export service for curricula"""

    VERSION = "1.0.0"

    # Quality presets: (max_width, jpeg_quality)
    QUALITY_PRESETS = {
        "high": (800, 90),  # Printing, archival
        "medium": (600, 85),  # General sharing (default)
        "low": (400, 75),  # Email, mobile viewing
    }

    def __init__(self):
        self.temp_files = []

    @staticmethod
    def _escape_text(value: Any) -> str:
        """Escape untrusted text for safe HTML embedding."""
        if value is None:
            return ""
        return html.escape(str(value), quote=True)

    @classmethod
    def _markdown_to_safe_html(cls, value: Any) -> str:
        """Render markdown from untrusted input while escaping raw HTML tags."""
        escaped = cls._escape_text(value)
        return markdown.markdown(escaped)

    @staticmethod
    def _safe_url(url: Any) -> Optional[str]:
        """Allow only safe URL schemes in exported links."""
        if not isinstance(url, str):
            return None

        candidate = url.strip()
        if not candidate:
            return None

        parsed = urlparse(candidate)
        if parsed.scheme.lower() in {"http", "https", "mailto"}:
            return candidate
        return None

    @staticmethod
    def _json_for_script(value: Any) -> str:
        """Safely embed JSON payloads inside <script> blocks."""
        raw = json.dumps(value, ensure_ascii=False)
        return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    def _optimize_image(
        self,
        base64_data: str,
        max_width: int = 600,
        quality: int = 85,
    ) -> str:
        """
        Optimize a base64 image for export by resizing and compressing.

        Args:
            base64_data: Base64 encoded image (with or without data URI prefix)
            max_width: Maximum width in pixels (maintains aspect ratio)
            quality: JPEG quality (1-100)

        Returns:
            Optimized base64 string (without data URI prefix)
        """
        try:
            # Strip data URI prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            # Decode base64 to image
            img_bytes = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_bytes))

            # Convert RGBA to RGB if needed (JPEG doesn't support alpha)
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if wider than max_width
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            # Save as JPEG with compression
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            buffer.seek(0)

            # Return base64 encoded
            return base64.b64encode(buffer.read()).decode("utf-8")

        except Exception as e:
            # If optimization fails, return original (without prefix)
            if "," in base64_data:
                return base64_data.split(",")[1]
            return base64_data

    def generate_pdf(self, curriculum: Dict[str, Any], quality: str = "medium") -> bytes:
        """
        Generate PDF from curriculum data using fpdf2

        Args:
            curriculum: Curriculum dictionary with metadata and units
            quality: Image quality preset ("high", "medium", "low")

        Returns:
            PDF file as bytes
        """
        max_width, jpeg_quality = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["medium"])
        try:
            meta = curriculum.get("meta") or curriculum.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}

            # Extract curriculum info
            title = meta.get("subject") or meta.get("title") or "Curriculum"
            grade = meta.get("grade") or meta.get("grade_level") or ""

            # Create PDF
            pdf = CurriculumPDF(curriculum_title=f"{title} - {grade}")
            pdf.add_page()

            # Add title page
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(41, 98, 255)
            pdf.cell(0, 20, pdf.pdf_text(title), 0, 1, "C")
            pdf.set_font("Helvetica", "", 14)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, pdf.pdf_text(f"Grade Level: {grade}"), 0, 1, "C")

            # Add select metadata (exclude internal/generation fields)
            # Keys to exclude: plan (generation prompt), style, language, extra, and already-shown fields
            EXCLUDED_META_KEYS = {
                "subject",
                "grade",
                "grade_level",
                "title",  # Already shown in header
                "plan",
                "style",
                "language",
                "extra",  # Internal generation config
                "prompt",
                "system_prompt",
                "raw_response",  # Debug/internal data
            }
            display_meta = {k: v for k, v in meta.items() if k not in EXCLUDED_META_KEYS and v}
            if display_meta:
                pdf.ln(10)
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, pdf.pdf_text("Curriculum Details"), 0, 1, "L")
                pdf.set_font("Helvetica", "", 11)

                for key, value in display_meta.items():
                    try:
                        display_value = (
                            json.dumps(value, ensure_ascii=False)
                            if isinstance(value, (dict, list))
                            else str(value)
                        )
                    except Exception:
                        display_value = str(value)
                    # Truncate very long values (e.g., if something slipped through)
                    if len(display_value) > 200:
                        display_value = display_value[:200] + "..."
                    pdf.multi_cell(
                        0,
                        6,
                        pdf.pdf_text(f"{key.replace('_', ' ').title()}: {display_value}"),
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )

            # Add units
            units = curriculum.get("units", [])
            for idx, unit in enumerate(units, 1):
                pdf.add_page()

                # Unit title
                pdf.chapter_title(f"Unit {idx}: {unit.get('title', 'Untitled')}", level=1)

                # Introduction
                if unit.get("introduction"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Introduction"), 0, 1)
                    pdf.chapter_body(unit["introduction"])

                # Main content
                if unit.get("content"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Content"), 0, 1)
                    pdf.chapter_body(unit["content"])

                # Images - Check both 'selected_image_b64' (new) and 'image' (legacy)
                img_b64 = unit.get("selected_image_b64") or unit.get("image")
                if img_b64:
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Illustration"), 0, 1)
                    optimized_img = self._optimize_image(img_b64, max_width, jpeg_quality)
                    pdf.add_image_from_base64(optimized_img)

                # Chart
                if unit.get("chart"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Data Visualization"), 0, 1)
                    chart = unit.get("chart")
                    chart_b64 = None
                    if isinstance(chart, dict):
                        chart_b64 = chart.get("b64")
                    elif isinstance(chart, str):
                        chart_b64 = chart
                    if chart_b64:
                        optimized_chart = self._optimize_image(chart_b64, max_width, jpeg_quality)
                        pdf.add_image_from_base64(optimized_chart)

                # Quiz
                if unit.get("quiz"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Assessment Questions"), 0, 1)
                    quiz = unit["quiz"]

                    # Handle both list format and dict format
                    if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                        questions = quiz.get("quiz", [])
                    else:
                        questions = quiz if isinstance(quiz, list) else quiz.get("questions", [])

                    for q_idx, question in enumerate(questions, 1):
                        if not isinstance(question, dict):
                            continue
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.cell(0, 8, pdf.pdf_text(f"Question {q_idx}:"), 0, 1)
                        pdf.set_font("Helvetica", "", 11)
                        pdf.multi_cell(
                            0,
                            6,
                            pdf.pdf_text(question.get("question", "")),
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )

                        # Options
                        options = question.get("options")
                        if isinstance(options, list) and options:
                            for opt in options:
                                pdf.cell(0, 6, pdf.pdf_text(f"  - {opt}"), 0, 1)

                        pdf.ln(3)

                # Summary
                if unit.get("summary"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Summary"), 0, 1)
                    pdf.chapter_body(unit["summary"])

                # Resources
                if unit.get("resources"):
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, pdf.pdf_text("Additional Resources"), 0, 1)
                    pdf.set_font("Helvetica", "", 11)
                    resources = unit.get("resources")
                    if isinstance(resources, str):
                        pdf.chapter_body(resources)
                    elif isinstance(resources, list):
                        for resource in resources:
                            pdf.multi_cell(
                                0,
                                6,
                                pdf.pdf_text(f"- {resource}"),
                                new_x="LMARGIN",
                                new_y="NEXT",
                            )
                        pdf.ln(3)
                    elif isinstance(resources, dict):
                        for resource_type, resource_list in resources.items():
                            if not resource_list:
                                continue
                            pdf.set_font("Helvetica", "B", 11)
                            pdf.cell(0, 7, pdf.pdf_text(str(resource_type).title()), 0, 1)
                            pdf.set_font("Helvetica", "", 11)
                            if isinstance(resource_list, str):
                                pdf.chapter_body(resource_list)
                            elif isinstance(resource_list, list):
                                for resource in resource_list:
                                    if isinstance(resource, dict):
                                        title = resource.get("title", "Resource")
                                        url = resource.get("url")
                                        line = f"- {title} ({url})" if url else f"- {title}"
                                        pdf.multi_cell(
                                            0,
                                            6,
                                            pdf.pdf_text(line),
                                            new_x="LMARGIN",
                                            new_y="NEXT",
                                        )
                                    else:
                                        pdf.multi_cell(
                                            0,
                                            6,
                                            pdf.pdf_text(f"- {resource}"),
                                            new_x="LMARGIN",
                                            new_y="NEXT",
                                        )
                    pdf.ln(3)

            # Add metadata footer
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, pdf.pdf_text("Export Metadata"), 0, 1)
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(0, 8, pdf.pdf_text(f"Generator: InstaSchool v{self.VERSION}"), 0, 1)
            generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pdf.cell(0, 8, pdf.pdf_text(f"Exported: {generated_at}"), 0, 1)
            model_info = meta.get("model") or meta.get("ai_model") or "Not specified"
            pdf.cell(0, 8, pdf.pdf_text(f"Model: {model_info}"), 0, 1)

            # Return PDF as bytes
            return bytes(pdf.output())

        except Exception as e:
            raise Exception(f"PDF generation failed: {str(e)}")

    def generate_html(self, curriculum: Dict[str, Any], quality: str = "medium") -> str:
        """
        Generate HTML from curriculum data

        Args:
            curriculum: Curriculum dictionary
            quality: Image quality preset ("high", "medium", "low")

        Returns:
            HTML string
        """
        max_width, jpeg_quality = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["medium"])
        meta = curriculum.get("meta") or curriculum.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        title = meta.get("subject") or meta.get("title") or "Curriculum"
        grade = meta.get("grade") or meta.get("grade_level") or ""
        safe_title = self._escape_text(title)
        safe_grade = self._escape_text(grade)

        units = curriculum.get("units", []) or []
        needs_plotly = any(
            isinstance(u, dict)
            and isinstance(u.get("chart"), dict)
            and u.get("chart", {}).get("plotly_config")
            for u in units
        )
        plotly_script = (
            '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
            if needs_plotly
            else ""
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} - {safe_grade}</title>
    {plotly_script}
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            color: #2962ff;
            border-bottom: 3px solid #2962ff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1565c0;
            margin-top: 30px;
        }}
        h3 {{
            color: #0d47a1;
        }}
        .unit {{
            margin-bottom: 50px;
            border: 1px solid #e0e0e0;
            padding: 20px;
            border-radius: 8px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
        }}
        .quiz {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .question {{
            margin: 15px 0;
        }}
        /* Print-friendly styles */
        @media print {{
            body {{
                max-width: 100%;
                padding: 0;
                font-size: 11pt;
            }}
            h1 {{
                color: #000;
                border-bottom-color: #000;
            }}
            h2, h3 {{
                color: #000;
            }}
            .unit {{
                border: 1px solid #ccc;
                page-break-inside: avoid;
                break-inside: avoid;
            }}
            .quiz {{
                background-color: #f0f0f0 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            img {{
                max-width: 80%;
                page-break-inside: avoid;
            }}
            h2 {{
                page-break-after: avoid;
            }}
        }}
    </style>
</head>
<body>
    <h1>{safe_title}</h1>
    <p><strong>Grade Level:</strong> {safe_grade}</p>
        """

        # Add units
        for idx, unit in enumerate(units, 1):
            if not isinstance(unit, dict):
                continue
            unit_title = self._escape_text(unit.get("title", "Untitled"))
            html += f'\n<div class="unit">\n'
            html += f"<h2>Unit {idx}: {unit_title}</h2>\n"

            if unit.get("introduction"):
                html += f"<h3>Introduction</h3>\n{self._markdown_to_safe_html(unit.get('introduction', ''))}\n"

            if unit.get("content"):
                html += (
                    f"<h3>Content</h3>\n{self._markdown_to_safe_html(unit.get('content', ''))}\n"
                )

            img_b64 = unit.get("selected_image_b64") or unit.get("image")
            if img_b64:
                optimized_img = self._optimize_image(img_b64, max_width, jpeg_quality)
                html += f'<h3>Illustration</h3>\n<img src="data:image/jpeg;base64,{optimized_img}" alt="Unit illustration">\n'

            if unit.get("chart"):
                chart = unit.get("chart")
                html += f"<h3>Data Visualization</h3>\n"
                if isinstance(chart, dict):
                    chart_b64 = chart.get("b64")
                    if chart_b64:
                        optimized_chart = self._optimize_image(chart_b64, max_width, jpeg_quality)
                        html += (
                            f'<img src="data:image/jpeg;base64,{optimized_chart}" alt="Chart">\n'
                        )
                    elif chart.get("plotly_config"):
                        chart_id = f"chart_{idx}"
                        fig_json = self._json_for_script(chart.get("plotly_config"))
                        html += f'<div id="{chart_id}" style="width: 100%; height: 420px;"></div>\n'
                        html += f'<script>const fig_{idx} = {fig_json}; Plotly.newPlot("{chart_id}", fig_{idx}.data, fig_{idx}.layout);</script>\n'
                elif isinstance(chart, str):
                    optimized_chart = self._optimize_image(chart, max_width, jpeg_quality)
                    html += f'<img src="data:image/jpeg;base64,{optimized_chart}" alt="Chart">\n'

            if unit.get("quiz"):
                html += '<div class="quiz">\n<h3>Assessment Questions</h3>\n'
                quiz = unit["quiz"]
                if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                    questions = quiz.get("quiz", [])
                else:
                    questions = quiz if isinstance(quiz, list) else quiz.get("questions", [])
                for q_idx, question in enumerate(questions, 1):
                    if not isinstance(question, dict):
                        continue
                    safe_question = self._escape_text(question.get("question", ""))
                    html += f'<div class="question">\n<strong>Question {q_idx}:</strong> {safe_question}<br>\n'
                    options = question.get("options")
                    if isinstance(options, list) and options:
                        for opt in options:
                            html += f"• {self._escape_text(opt)}<br>\n"
                    html += "</div>\n"
                html += "</div>\n"

            if unit.get("summary"):
                html += (
                    f"<h3>Summary</h3>\n{self._markdown_to_safe_html(unit.get('summary', ''))}\n"
                )

            if unit.get("resources"):
                html += "<h3>Additional Resources</h3>\n"
                resources = unit.get("resources")
                if isinstance(resources, str):
                    html += self._markdown_to_safe_html(resources) + "\n"
                elif isinstance(resources, list):
                    html += "<ul>\n"
                    for resource in resources:
                        if isinstance(resource, dict):
                            r_title = resource.get("title", "Resource")
                            url = resource.get("url")
                            safe_url = self._safe_url(url)
                            if safe_url:
                                html += (
                                    f'<li><a href="{self._escape_text(safe_url)}">'
                                    f"{self._escape_text(r_title)}</a></li>\n"
                                )
                            else:
                                html += f"<li>{self._escape_text(r_title)}</li>\n"
                        else:
                            html += f"<li>{self._escape_text(resource)}</li>\n"
                    html += "</ul>\n"
                elif isinstance(resources, dict):
                    for resource_type, resource_list in resources.items():
                        if not resource_list:
                            continue
                        html += f"<h4>{self._escape_text(str(resource_type).title())}</h4>\n"
                        if isinstance(resource_list, str):
                            html += self._markdown_to_safe_html(resource_list) + "\n"
                        elif isinstance(resource_list, list):
                            html += "<ul>\n"
                            for resource in resource_list:
                                if isinstance(resource, dict):
                                    r_title = resource.get("title", "Resource")
                                    url = resource.get("url")
                                    safe_url = self._safe_url(url)
                                    if safe_url:
                                        html += (
                                            f'<li><a href="{self._escape_text(safe_url)}">'
                                            f"{self._escape_text(r_title)}</a></li>\n"
                                        )
                                    else:
                                        html += f"<li>{self._escape_text(r_title)}</li>\n"
                                else:
                                    html += f"<li>{self._escape_text(resource)}</li>\n"
                            html += "</ul>\n"

            html += "</div>\n"

        # Add metadata footer
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        model_info = meta.get("model") or meta.get("ai_model") or "Not specified"
        safe_model_info = self._escape_text(model_info)
        safe_generated_at = self._escape_text(generated_at)
        html += f"""
    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 0.85em; color: #666;">
        <p><strong>Export Metadata</strong></p>
        <ul style="list-style: none; padding: 0; margin: 0;">
            <li>Generator: InstaSchool v{self.VERSION}</li>
            <li>Exported: {safe_generated_at}</li>
            <li>Model: {safe_model_info}</li>
        </ul>
    </footer>
</body>
</html>"""

        return html

    def generate_markdown(self, curriculum: Dict[str, Any], include_images: bool = True) -> str:
        """
        Generate Markdown from curriculum data

        Args:
            curriculum: Curriculum dictionary
            include_images: Whether to include image/chart placeholders

        Returns:
            Markdown string
        """
        meta = curriculum.get("meta") or curriculum.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        title = meta.get("subject") or meta.get("title") or "Curriculum"
        grade = meta.get("grade") or meta.get("grade_level") or ""

        md = f"# {title}\n\n"
        md += f"**Grade Level:** {grade}\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"

        # Add units
        units = curriculum.get("units", []) or []
        for idx, unit in enumerate(units, 1):
            if not isinstance(unit, dict):
                continue
            md += f"## Unit {idx}: {unit.get('title', 'Untitled')}\n\n"

            if unit.get("introduction"):
                md += f"### Introduction\n\n{unit['introduction']}\n\n"

            if unit.get("content"):
                md += f"### Content\n\n{unit['content']}\n\n"

            if include_images:
                img_b64 = unit.get("selected_image_b64") or unit.get("image")
                if img_b64:
                    md += "### Illustration\n\n"
                    md += f"*![Illustration: {unit.get('title', 'Topic')}]*\n\n"

                chart = unit.get("chart")
                chart_b64 = None
                if isinstance(chart, dict):
                    chart_b64 = chart.get("b64")
                elif isinstance(chart, str):
                    chart_b64 = chart
                if chart_b64:
                    md += "### Data Visualization\n\n"
                    md += f"*![Chart: {unit.get('title', 'Topic')}]*\n\n"

            if unit.get("quiz"):
                md += "### Assessment Questions\n\n"
                quiz = unit["quiz"]
                if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                    questions = quiz.get("quiz", [])
                else:
                    questions = quiz if isinstance(quiz, list) else quiz.get("questions", [])
                for q_idx, question in enumerate(questions, 1):
                    if not isinstance(question, dict):
                        continue
                    md += f"**Question {q_idx}:** {question.get('question', '')}\n\n"
                    options = question.get("options")
                    if isinstance(options, list) and options:
                        for opt in options:
                            md += f"- {opt}\n"
                    md += "\n"

            if unit.get("summary"):
                md += f"### Summary\n\n{unit['summary']}\n\n"

            if unit.get("resources"):
                md += "### Additional Resources\n\n"
                resources = unit.get("resources")
                if isinstance(resources, str):
                    md += resources.strip() + "\n"
                elif isinstance(resources, list):
                    for resource in resources:
                        md += f"- {resource}\n"
                elif isinstance(resources, dict):
                    for resource_type, resource_list in resources.items():
                        if not resource_list:
                            continue
                        md += f"**{str(resource_type).title()}**\n\n"
                        if isinstance(resource_list, str):
                            md += resource_list.strip() + "\n\n"
                        elif isinstance(resource_list, list):
                            for resource in resource_list:
                                if isinstance(resource, dict):
                                    r_title = resource.get("title", "Resource")
                                    url = resource.get("url")
                                    md += f"- {r_title} ({url})\n" if url else f"- {r_title}\n"
                                else:
                                    md += f"- {resource}\n"
                md += "\n"

            md += "---\n\n"

        return md


# Singleton instance
_exporter_instance = None


def get_exporter() -> CurriculumExporter:
    """Get or create the exporter singleton"""
    global _exporter_instance
    if _exporter_instance is None:
        _exporter_instance = CurriculumExporter()
    return _exporter_instance
