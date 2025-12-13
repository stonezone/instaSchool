"""
Export Service for InstaSchool
Provides PDF, HTML, and Markdown export functionality using pure Python libraries
"""

import os
import json
import base64
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from fpdf import FPDF
import markdown


class CurriculumPDF(FPDF):
    """Custom PDF class for curriculum export"""
    
    def __init__(self, curriculum_title: str = "InstaSchool Curriculum"):
        super().__init__()
        self.curriculum_title = curriculum_title
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        """Add header to each page"""
        self.set_font('Arial', 'B', 16)
        self.set_text_color(41, 98, 255)  # Blue color
        self.cell(0, 10, self.curriculum_title, 0, 1, 'C')
        self.ln(5)
        
    def footer(self):
        """Add footer to each page"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)  # Gray
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        
    def chapter_title(self, title: str, level: int = 1):
        """Add a chapter/section title"""
        self.set_font('Arial', 'B', 16 if level == 1 else 14)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(200, 220, 255)  # Light blue background
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)
        
    def chapter_body(self, text: str):
        """Add body text to chapter"""
        self.set_font('Arial', '', 11)
        self.set_text_color(0, 0, 0)
        # Handle potential unicode issues
        try:
            self.multi_cell(0, 6, text)
        except Exception:
            # Fallback: remove problematic characters
            safe_text = text.encode('ascii', 'ignore').decode('ascii')
            self.multi_cell(0, 6, safe_text)
        self.ln(3)
        
    def add_image_from_base64(self, base64_data: str, w: int = 150):
        """Add image from base64 data"""
        try:
            # Create temporary file for image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                # Decode base64 and write to temp file
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                img_data = base64.b64decode(base64_data)
                tmp.write(img_data)
                tmp_path = tmp.name
            
            # Add image to PDF
            self.image(tmp_path, x=30, w=w)
            self.ln(5)
            
            # Clean up temp file
            os.unlink(tmp_path)
        except Exception as e:
            # If image fails, add error message
            self.set_font('Arial', 'I', 10)
            self.set_text_color(255, 0, 0)
            self.cell(0, 10, f'[Image could not be loaded: {str(e)}]', 0, 1)
            self.ln(3)


class CurriculumExporter:
    """Main export service for curricula"""
    
    def __init__(self):
        self.temp_files = []
        
    def generate_pdf(self, curriculum: Dict[str, Any]) -> bytes:
        """
        Generate PDF from curriculum data using fpdf2
        
        Args:
            curriculum: Curriculum dictionary with metadata and units
            
        Returns:
            PDF file as bytes
        """
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
            pdf.set_font('Arial', 'B', 24)
            pdf.set_text_color(41, 98, 255)
            pdf.cell(0, 20, title, 0, 1, 'C')
            pdf.set_font('Arial', '', 14)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, f"Grade Level: {grade}", 0, 1, 'C')
            
            # Add metadata
            if meta:
                pdf.ln(10)
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, 'Curriculum Details', 0, 1, 'L')
                pdf.set_font('Arial', '', 11)
                
                for key, value in meta.items():
                    if key not in ['subject', 'grade', 'grade_level']:
                        try:
                            display_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                        except Exception:
                            display_value = str(value)
                        pdf.cell(0, 8, f"{key.replace('_', ' ').title()}: {display_value}", 0, 1)
            
            # Add units
            units = curriculum.get('units', [])
            for idx, unit in enumerate(units, 1):
                pdf.add_page()
                
                # Unit title
                pdf.chapter_title(f"Unit {idx}: {unit.get('title', 'Untitled')}", level=1)
                
                # Introduction
                if unit.get('introduction'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Introduction', 0, 1)
                    pdf.chapter_body(unit['introduction'])
                
                # Main content
                if unit.get('content'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Content', 0, 1)
                    pdf.chapter_body(unit['content'])
                
                # Images - Check both 'selected_image_b64' (new) and 'image' (legacy)
                img_b64 = unit.get('selected_image_b64') or unit.get('image')
                if img_b64:
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Illustration', 0, 1)
                    pdf.add_image_from_base64(img_b64)
                
                # Chart
                if unit.get('chart'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Data Visualization', 0, 1)
                    chart = unit.get("chart")
                    chart_b64 = None
                    if isinstance(chart, dict):
                        chart_b64 = chart.get("b64")
                    elif isinstance(chart, str):
                        chart_b64 = chart
                    if chart_b64:
                        pdf.add_image_from_base64(chart_b64)
                
                # Quiz
                if unit.get('quiz'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Assessment Questions', 0, 1)
                    quiz = unit['quiz']

                    # Handle both list format and dict format
                    if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                        questions = quiz.get("quiz", [])
                    else:
                        questions = quiz if isinstance(quiz, list) else quiz.get('questions', [])

                    for q_idx, question in enumerate(questions, 1):
                        if not isinstance(question, dict):
                            continue
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 8, f"Question {q_idx}:", 0, 1)
                        pdf.set_font('Arial', '', 11)
                        pdf.multi_cell(0, 6, question.get('question', ''))
                        
                        # Options
                        options = question.get("options")
                        if isinstance(options, list) and options:
                            for opt in options:
                                pdf.cell(0, 6, f"  • {opt}", 0, 1)
                        
                        pdf.ln(3)
                
                # Summary
                if unit.get('summary'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Summary', 0, 1)
                    pdf.chapter_body(unit['summary'])
                
                # Resources
                if unit.get('resources'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Additional Resources', 0, 1)
                    pdf.set_font('Arial', '', 11)
                    resources = unit.get("resources")
                    if isinstance(resources, str):
                        pdf.chapter_body(resources)
                    elif isinstance(resources, list):
                        for resource in resources:
                            pdf.multi_cell(0, 6, f"• {resource}")
                        pdf.ln(3)
                    elif isinstance(resources, dict):
                        for resource_type, resource_list in resources.items():
                            if not resource_list:
                                continue
                            pdf.set_font('Arial', 'B', 11)
                            pdf.cell(0, 7, str(resource_type).title(), 0, 1)
                            pdf.set_font('Arial', '', 11)
                            if isinstance(resource_list, str):
                                pdf.chapter_body(resource_list)
                            elif isinstance(resource_list, list):
                                for resource in resource_list:
                                    if isinstance(resource, dict):
                                        title = resource.get("title", "Resource")
                                        url = resource.get("url")
                                        pdf.multi_cell(0, 6, f"• {title} ({url})" if url else f"• {title}")
                                    else:
                                        pdf.multi_cell(0, 6, f"• {resource}")
                    pdf.ln(3)
            
            # Return PDF as bytes
            return pdf.output(dest='S').encode('latin-1')
            
        except Exception as e:
            raise Exception(f"PDF generation failed: {str(e)}")
    
    def generate_html(self, curriculum: Dict[str, Any]) -> str:
        """
        Generate HTML from curriculum data
        
        Args:
            curriculum: Curriculum dictionary
            
        Returns:
            HTML string
        """
        meta = curriculum.get("meta") or curriculum.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        title = meta.get("subject") or meta.get("title") or "Curriculum"
        grade = meta.get("grade") or meta.get("grade_level") or ""

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
    <title>{title} - {grade}</title>
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
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p><strong>Grade Level:</strong> {grade}</p>
        """
        
        # Add units
        for idx, unit in enumerate(units, 1):
            if not isinstance(unit, dict):
                continue
            html += f'\n<div class="unit">\n'
            html += f'<h2>Unit {idx}: {unit.get("title", "Untitled")}</h2>\n'
            
            if unit.get('introduction'):
                html += f'<h3>Introduction</h3>\n{markdown.markdown(unit.get("introduction", ""))}\n'
            
            if unit.get('content'):
                html += f'<h3>Content</h3>\n{markdown.markdown(unit.get("content", ""))}\n'
            
            img_b64 = unit.get('selected_image_b64') or unit.get('image')
            if img_b64:
                src = img_b64 if isinstance(img_b64, str) and img_b64.startswith("data:") else f"data:image/png;base64,{img_b64}"
                html += f'<h3>Illustration</h3>\n<img src="{src}" alt="Unit illustration">\n'
            
            if unit.get('chart'):
                chart = unit.get("chart")
                html += f'<h3>Data Visualization</h3>\n'
                if isinstance(chart, dict):
                    chart_b64 = chart.get("b64")
                    if chart_b64:
                        src = chart_b64 if str(chart_b64).startswith("data:") else f"data:image/png;base64,{chart_b64}"
                        html += f'<img src="{src}" alt="Chart">\n'
                    elif chart.get("plotly_config"):
                        chart_id = f"chart_{idx}"
                        fig_json = json.dumps(chart.get("plotly_config"))
                        html += f'<div id="{chart_id}" style="width: 100%; height: 420px;"></div>\n'
                        html += f'<script>const fig_{idx} = {fig_json}; Plotly.newPlot("{chart_id}", fig_{idx}.data, fig_{idx}.layout);</script>\n'
                elif isinstance(chart, str):
                    src = chart if chart.startswith("data:") else f"data:image/png;base64,{chart}"
                    html += f'<img src="{src}" alt="Chart">\n'
            
            if unit.get('quiz'):
                html += '<div class="quiz">\n<h3>Assessment Questions</h3>\n'
                quiz = unit['quiz']
                if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                    questions = quiz.get("quiz", [])
                else:
                    questions = quiz if isinstance(quiz, list) else quiz.get('questions', [])
                for q_idx, question in enumerate(questions, 1):
                    if not isinstance(question, dict):
                        continue
                    html += f'<div class="question">\n<strong>Question {q_idx}:</strong> {question.get("question", "")}<br>\n'
                    options = question.get("options")
                    if isinstance(options, list) and options:
                        for opt in options:
                            html += f'• {opt}<br>\n'
                    html += '</div>\n'
                html += '</div>\n'
            
            if unit.get('summary'):
                html += f'<h3>Summary</h3>\n{markdown.markdown(unit.get("summary", ""))}\n'
            
            if unit.get('resources'):
                html += '<h3>Additional Resources</h3>\n'
                resources = unit.get("resources")
                if isinstance(resources, str):
                    html += markdown.markdown(resources) + "\n"
                elif isinstance(resources, list):
                    html += '<ul>\n'
                    for resource in resources:
                        html += f'<li>{resource}</li>\n'
                    html += '</ul>\n'
                elif isinstance(resources, dict):
                    for resource_type, resource_list in resources.items():
                        if not resource_list:
                            continue
                        html += f"<h4>{str(resource_type).title()}</h4>\n"
                        if isinstance(resource_list, str):
                            html += markdown.markdown(resource_list) + "\n"
                        elif isinstance(resource_list, list):
                            html += "<ul>\n"
                            for resource in resource_list:
                                if isinstance(resource, dict):
                                    r_title = resource.get("title", "Resource")
                                    url = resource.get("url")
                                    html += f"<li><a href=\"{url}\">{r_title}</a></li>\n" if url else f"<li>{r_title}</li>\n"
                                else:
                                    html += f"<li>{resource}</li>\n"
                            html += "</ul>\n"
            
            html += '</div>\n'
        
        html += """
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
        units = curriculum.get('units', []) or []
        for idx, unit in enumerate(units, 1):
            if not isinstance(unit, dict):
                continue
            md += f"## Unit {idx}: {unit.get('title', 'Untitled')}\n\n"
            
            if unit.get('introduction'):
                md += f"### Introduction\n\n{unit['introduction']}\n\n"
            
            if unit.get('content'):
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
            
            if unit.get('quiz'):
                md += "### Assessment Questions\n\n"
                quiz = unit['quiz']
                if isinstance(quiz, dict) and isinstance(quiz.get("quiz"), list):
                    questions = quiz.get("quiz", [])
                else:
                    questions = quiz if isinstance(quiz, list) else quiz.get('questions', [])
                for q_idx, question in enumerate(questions, 1):
                    if not isinstance(question, dict):
                        continue
                    md += f"**Question {q_idx}:** {question.get('question', '')}\n\n"
                    options = question.get("options")
                    if isinstance(options, list) and options:
                        for opt in options:
                            md += f"- {opt}\n"
                    md += "\n"
            
            if unit.get('summary'):
                md += f"### Summary\n\n{unit['summary']}\n\n"
            
            if unit.get('resources'):
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
