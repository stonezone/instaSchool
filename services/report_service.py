"""
Report Service - Progress Report PDF Generation

Generates beautiful PDF progress reports for individual children
or family-wide summaries.
"""

import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF

from services.family_service import FamilyService


class ProgressReportPDF(FPDF):
    """Custom PDF class for progress reports"""

    def __init__(self, title: str = "Progress Report"):
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add header to each page"""
        self.set_font('Arial', 'B', 18)
        self.set_text_color(41, 98, 255)  # Blue
        self.cell(0, 10, 'InstaSchool', 0, 1, 'C')
        self.set_font('Arial', '', 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, self.report_title, 0, 1, 'C')
        self.ln(8)

    def footer(self):
        """Add footer to each page"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated {datetime.now().strftime("%b %d, %Y")}', 0, 0, 'C')

    def section_title(self, title: str):
        """Add a section title with background"""
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(41, 98, 255)  # Blue background
        self.cell(0, 10, f'  {title}', 0, 1, 'L', fill=True)
        self.ln(4)

    def stat_box(self, label: str, value: str, color: tuple = (41, 98, 255)):
        """Add a stat box with label and value"""
        self.set_font('Arial', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(40, 6, label, 0, 0)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(*color)
        self.cell(0, 6, str(value), 0, 1)

    def progress_bar(self, label: str, percent: int, width: int = 100):
        """Draw a progress bar"""
        self.set_font('Arial', '', 10)
        self.set_text_color(60, 60, 60)
        self.cell(60, 8, label, 0, 0)

        # Draw progress bar background
        x = self.get_x()
        y = self.get_y() + 2
        self.set_fill_color(230, 230, 230)
        self.rect(x, y, width, 5, 'F')

        # Draw progress fill
        fill_width = (percent / 100) * width
        if percent >= 80:
            self.set_fill_color(76, 175, 80)  # Green
        elif percent >= 50:
            self.set_fill_color(255, 193, 7)  # Yellow
        else:
            self.set_fill_color(244, 67, 54)  # Red
        self.rect(x, y, fill_width, 5, 'F')

        # Add percentage text
        self.set_x(x + width + 5)
        self.cell(20, 8, f'{percent}%', 0, 1)

    def body_text(self, text: str):
        """Add body text"""
        self.set_font('Arial', '', 11)
        self.set_text_color(60, 60, 60)
        try:
            self.multi_cell(0, 6, text)
        except Exception:
            safe_text = text.encode('ascii', 'ignore').decode('ascii')
            self.multi_cell(0, 6, safe_text)
        self.ln(2)


class ReportService:
    """Service for generating progress reports"""

    def __init__(self, db_path: str = "instaschool.db"):
        self.family_service = FamilyService(db_path)

    def generate_child_report(self, user_id: str) -> bytes:
        """Generate PDF progress report for a single child

        Args:
            user_id: Child's user ID

        Returns:
            PDF file as bytes
        """
        summary = self.family_service.get_child_summary(user_id)
        curricula = self.family_service.get_child_curricula_progress(user_id)

        # Create PDF
        pdf = ProgressReportPDF(f"Progress Report - {summary.get('username', 'Student')}")
        pdf.add_page()

        # Student Overview Section
        pdf.section_title("Student Overview")
        pdf.stat_box("Student Name:", summary.get('username', 'Unknown'))
        pdf.stat_box("Total XP:", f"{summary.get('total_xp', 0):,}", (76, 175, 80))
        pdf.stat_box("Current Level:", str(summary.get('level', 0)))
        pdf.stat_box("Study Streak:", f"{summary.get('current_streak', 0)} days", (255, 152, 0))
        pdf.stat_box("Due Reviews:", str(summary.get('due_cards', 0)))
        pdf.stat_box("Last Active:", summary.get('last_active', 'Never'))
        pdf.ln(5)

        # Curricula Progress Section
        if curricula:
            pdf.section_title("Curriculum Progress")
            for curr in curricula:
                title = curr.get('title', 'Unknown Curriculum')
                subject = curr.get('subject', '')
                grade = curr.get('grade', '')
                progress = curr.get('progress_percent', 0)
                xp = curr.get('xp', 0)

                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(41, 98, 255)
                pdf.cell(0, 8, title, 0, 1)

                if subject or grade:
                    pdf.set_font('Arial', 'I', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 5, f"{subject} | {grade}", 0, 1)

                pdf.progress_bar("Progress:", progress)
                pdf.stat_box("XP Earned:", f"{xp:,}")
                pdf.ln(3)

        # Summary Statistics
        pdf.section_title("Summary Statistics")
        pdf.stat_box("Total Curricula:", str(summary.get('total_curricula', 0)))
        pdf.stat_box("Completed:", str(summary.get('completed_curricula', 0)))
        pdf.stat_box("Sections Completed:", str(summary.get('total_sections_completed', 0)))

        return pdf.output()

    def generate_family_report(self) -> bytes:
        """Generate PDF progress report for entire family

        Returns:
            PDF file as bytes
        """
        family = self.family_service.get_family_summary()
        children = family.get('children', [])
        totals = family.get('totals', {})

        # Create PDF
        pdf = ProgressReportPDF("Family Progress Report")
        pdf.add_page()

        # Family Overview
        pdf.section_title("Family Overview")
        pdf.stat_box("Total Children:", str(len(children)))
        pdf.stat_box("Active Today:", str(totals.get('active_today', 0)))
        pdf.stat_box("Family Total XP:", f"{totals.get('total_xp', 0):,}", (76, 175, 80))
        pdf.stat_box("Total Curricula:", str(totals.get('total_curricula', 0)))
        pdf.stat_box("Sections Completed:", str(totals.get('total_sections', 0)))
        pdf.stat_box("Due Reviews:", str(totals.get('total_due_cards', 0)))
        pdf.ln(5)

        # Individual Child Summaries
        pdf.section_title("Children's Progress")

        for child in children:
            username = child.get('username', 'Unknown')
            total_xp = child.get('total_xp', 0)
            level = child.get('level', 0)
            streak = child.get('current_streak', 0)
            last_active = child.get('last_active', 'Never')
            due_cards = child.get('due_cards', 0)

            # Child header
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(41, 98, 255)
            pdf.cell(0, 10, f"{username}", 0, 1)

            # Child stats in two columns
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(60, 60, 60)

            col_width = 90
            pdf.cell(col_width, 6, f"Level: {level} ({total_xp:,} XP)", 0, 0)
            pdf.cell(col_width, 6, f"Streak: {streak} days", 0, 1)
            pdf.cell(col_width, 6, f"Last Active: {last_active}", 0, 0)
            pdf.cell(col_width, 6, f"Due Reviews: {due_cards}", 0, 1)

            pdf.ln(3)

            # Separator line
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

        # Recommendations Section
        pdf.section_title("Recommendations")

        # Generate personalized recommendations
        recommendations = self._generate_recommendations(children)
        for rec in recommendations:
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(5, 6, "-", 0, 0)
            pdf.multi_cell(0, 6, rec)
            pdf.ln(1)

        return pdf.output()

    def _generate_recommendations(self, children: List[Dict[str, Any]]) -> List[str]:
        """Generate personalized recommendations based on progress data"""
        recommendations = []

        for child in children:
            username = child.get('username', 'Unknown')
            streak = child.get('current_streak', 0)
            due_cards = child.get('due_cards', 0)
            last_active = child.get('last_active', 'Never')

            # Streak recommendations
            if streak == 0:
                recommendations.append(f"{username} should start a study streak! Even 10 minutes daily builds habits.")
            elif streak >= 7:
                recommendations.append(f"Great job {username}! {streak}-day streak. Keep up the momentum!")

            # Due reviews
            if due_cards > 10:
                recommendations.append(f"{username} has {due_cards} due reviews. A quick review session would help retention.")

            # Activity check
            if last_active not in ['Today', 'Yesterday']:
                recommendations.append(f"Encourage {username} to get back to learning - it's been a while!")

        # Add general recommendations if list is short
        if len(recommendations) < 3:
            recommendations.append("Consider setting daily learning goals for each child.")
            recommendations.append("Regular review sessions help with long-term retention.")

        return recommendations[:5]  # Limit to 5 recommendations


# Singleton instance
_report_service_instance = None


def get_report_service(db_path: str = "instaschool.db") -> ReportService:
    """Get or create the report service singleton

    Args:
        db_path: Path to database

    Returns:
        ReportService instance
    """
    global _report_service_instance
    if _report_service_instance is None:
        _report_service_instance = ReportService(db_path)
    return _report_service_instance
