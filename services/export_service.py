"""
Export Service for InstaSchool
Provides PDF, HTML, and Markdown export functionality using pure Python libraries
"""

import os
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
            # Extract curriculum info
            title = curriculum.get('metadata', {}).get('subject', 'Curriculum')
            grade = curriculum.get('metadata', {}).get('grade_level', '')
            
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
            metadata = curriculum.get('metadata', {})
            if metadata:
                pdf.ln(10)
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, 'Curriculum Details', 0, 1, 'L')
                pdf.set_font('Arial', '', 11)
                
                for key, value in metadata.items():
                    if key not in ['subject', 'grade_level']:
                        pdf.cell(0, 8, f"{key.replace('_', ' ').title()}: {value}", 0, 1)
            
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
                
                # Images
                if unit.get('image'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Illustration', 0, 1)
                    pdf.add_image_from_base64(unit['image'])
                
                # Chart
                if unit.get('chart'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Data Visualization', 0, 1)
                    pdf.add_image_from_base64(unit['chart'])
                
                # Quiz
                if unit.get('quiz'):
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, 'Assessment Questions', 0, 1)
                    quiz = unit['quiz']
                    
                    for q_idx, question in enumerate(quiz.get('questions', []), 1):
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 8, f"Question {q_idx}:", 0, 1)
                        pdf.set_font('Arial', '', 11)
                        pdf.multi_cell(0, 6, question.get('question', ''))
                        
                        # Options
                        for opt_key in ['a', 'b', 'c', 'd']:
                            if opt_key in question:
                                pdf.cell(0, 6, f"  {opt_key.upper()}) {question[opt_key]}", 0, 1)
                        
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
                    for resource in unit['resources']:
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
        title = curriculum.get('metadata', {}).get('subject', 'Curriculum')
        grade = curriculum.get('metadata', {}).get('grade_level', '')
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {grade}</title>
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
        units = curriculum.get('units', [])
        for idx, unit in enumerate(units, 1):
            html += f'\n<div class="unit">\n'
            html += f'<h2>Unit {idx}: {unit.get("title", "Untitled")}</h2>\n'
            
            if unit.get('introduction'):
                html += f'<h3>Introduction</h3>\n<p>{unit["introduction"]}</p>\n'
            
            if unit.get('content'):
                html += f'<h3>Content</h3>\n<p>{unit["content"]}</p>\n'
            
            if unit.get('image'):
                html += f'<h3>Illustration</h3>\n<img src="{unit["image"]}" alt="Unit illustration">\n'
            
            if unit.get('chart'):
                html += f'<h3>Data Visualization</h3>\n<img src="{unit["chart"]}" alt="Chart">\n'
            
            if unit.get('quiz'):
                html += '<div class="quiz">\n<h3>Assessment Questions</h3>\n'
                for q_idx, question in enumerate(unit['quiz'].get('questions', []), 1):
                    html += f'<div class="question">\n<strong>Question {q_idx}:</strong> {question.get("question", "")}<br>\n'
                    for opt_key in ['a', 'b', 'c', 'd']:
                        if opt_key in question:
                            html += f'{opt_key.upper()}) {question[opt_key]}<br>\n'
                    html += '</div>\n'
                html += '</div>\n'
            
            if unit.get('summary'):
                html += f'<h3>Summary</h3>\n<p>{unit["summary"]}</p>\n'
            
            if unit.get('resources'):
                html += '<h3>Additional Resources</h3>\n<ul>\n'
                for resource in unit['resources']:
                    html += f'<li>{resource}</li>\n'
                html += '</ul>\n'
            
            html += '</div>\n'
        
        html += """
</body>
</html>"""
        
        return html
    
    def generate_markdown(self, curriculum: Dict[str, Any]) -> str:
        """
        Generate Markdown from curriculum data
        
        Args:
            curriculum: Curriculum dictionary
            
        Returns:
            Markdown string
        """
        title = curriculum.get('metadata', {}).get('subject', 'Curriculum')
        grade = curriculum.get('metadata', {}).get('grade_level', '')
        
        md = f"# {title}\n\n"
        md += f"**Grade Level:** {grade}\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"
        
        # Add units
        units = curriculum.get('units', [])
        for idx, unit in enumerate(units, 1):
            md += f"## Unit {idx}: {unit.get('title', 'Untitled')}\n\n"
            
            if unit.get('introduction'):
                md += f"### Introduction\n\n{unit['introduction']}\n\n"
            
            if unit.get('content'):
                md += f"### Content\n\n{unit['content']}\n\n"
            
            if unit.get('quiz'):
                md += "### Assessment Questions\n\n"
                for q_idx, question in enumerate(unit['quiz'].get('questions', []), 1):
                    md += f"**Question {q_idx}:** {question.get('question', '')}\n\n"
                    for opt_key in ['a', 'b', 'c', 'd']:
                        if opt_key in question:
                            md += f"- {opt_key.upper()}) {question[opt_key]}\n"
                    md += "\n"
            
            if unit.get('summary'):
                md += f"### Summary\n\n{unit['summary']}\n\n"
            
            if unit.get('resources'):
                md += "### Additional Resources\n\n"
                for resource in unit['resources']:
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
