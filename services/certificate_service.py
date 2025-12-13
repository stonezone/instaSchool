"""
Certificate Service - Printable Achievement Certificates

Generates beautiful PDF certificates for:
- Curriculum completion
- Monthly progress
- Custom certificates (parent can edit text)

No blockchain, no verification servers - just nice PDFs to print and display.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fpdf import FPDF


class CertificatePDF(FPDF):
    """Custom PDF class for certificates with decorative borders"""

    _UNICODE_REPLACEMENTS = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u00A0": " ",
    }

    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')  # Landscape
        self.set_auto_page_break(auto=False)

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
        """Insert spaces into very long runs so `cell` can wrap safely."""
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

    def add_decorative_border(self):
        """Add decorative border to certificate"""
        # Outer border
        self.set_draw_color(41, 98, 255)  # Blue
        self.set_line_width(2)
        self.rect(10, 10, 277, 190)

        # Inner border
        self.set_line_width(0.5)
        self.rect(15, 15, 267, 180)

        # Corner decorations
        self.set_fill_color(41, 98, 255)
        corners = [(15, 15), (277, 15), (15, 190), (277, 190)]
        for x, y in corners:
            self.ellipse(x - 3, y - 3, 6, 6, 'F')

    def add_header_decoration(self):
        """Add decorative header elements"""
        # Simple decorative markers (ASCII only to avoid font issues)
        self.set_font('Helvetica', '', 24)
        self.set_text_color(255, 193, 7)  # Gold
        self.set_xy(30, 25)
        self.cell(0, 10, self.pdf_text('*'), 0, 0, 'L')
        self.set_xy(247, 25)
        self.cell(0, 10, self.pdf_text('*'), 0, 0, 'L')


class CertificateService:
    """Service for generating achievement certificates"""

    def generate_completion_certificate(
        self,
        student_name: str,
        curriculum_title: str,
        subject: str = "",
        completion_date: Optional[str] = None,
        total_xp: int = 0,
        level: int = 0
    ) -> bytes:
        """Generate curriculum completion certificate

        Args:
            student_name: Name of the student
            curriculum_title: Title of completed curriculum
            subject: Subject area
            completion_date: Date of completion (defaults to today)
            total_xp: Total XP earned
            level: Student's level

        Returns:
            PDF bytes
        """
        if not completion_date:
            completion_date = datetime.now().strftime("%B %d, %Y")

        pdf = CertificatePDF()
        pdf.add_page()
        pdf.add_decorative_border()
        pdf.add_header_decoration()

        # Title
        pdf.set_font('Helvetica', 'B', 36)
        pdf.set_text_color(41, 98, 255)
        pdf.set_xy(0, 35)
        pdf.cell(297, 15, pdf.pdf_text('Certificate of Completion'), 0, 1, 'C')

        # Subtitle
        pdf.set_font('Helvetica', 'I', 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(297, 8, pdf.pdf_text('This certificate is proudly presented to'), 0, 1, 'C')

        # Student name
        pdf.set_font('Helvetica', 'B', 32)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        pdf.cell(297, 15, pdf.pdf_text(student_name), 0, 1, 'C')

        # Decorative line
        pdf.set_draw_color(255, 193, 7)
        pdf.set_line_width(1)
        pdf.line(80, pdf.get_y() + 2, 217, pdf.get_y() + 2)

        # Completion text
        pdf.set_font('Helvetica', '', 14)
        pdf.set_text_color(60, 60, 60)
        pdf.ln(10)
        pdf.cell(297, 8, pdf.pdf_text('for successfully completing'), 0, 1, 'C')

        # Curriculum title
        pdf.set_font('Helvetica', 'B', 24)
        pdf.set_text_color(41, 98, 255)
        pdf.cell(297, 12, pdf.pdf_text(curriculum_title), 0, 1, 'C')

        # Subject if provided
        if subject:
            pdf.set_font('Helvetica', 'I', 12)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(297, 6, pdf.pdf_text(f"Subject: {subject}"), 0, 1, 'C')

        # Achievement stats
        pdf.ln(8)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(60, 60, 60)
        stats_text = f"Level {level} | {total_xp:,} XP Earned"
        pdf.cell(297, 6, pdf.pdf_text(stats_text), 0, 1, 'C')

        # Date
        pdf.ln(10)
        pdf.set_font('Helvetica', 'I', 12)
        pdf.cell(297, 6, pdf.pdf_text(f"Awarded on {completion_date}"), 0, 1, 'C')

        # Footer
        pdf.set_xy(0, 175)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(41, 98, 255)
        pdf.cell(297, 6, pdf.pdf_text('InstaSchool'), 0, 1, 'C')
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(297, 5, pdf.pdf_text('Personalized Learning Achievement'), 0, 1, 'C')

        return bytes(pdf.output())

    def generate_progress_certificate(
        self,
        student_name: str,
        period: str = "Monthly",
        sections_completed: int = 0,
        xp_earned: int = 0,
        streak_days: int = 0,
        quizzes_passed: int = 0
    ) -> bytes:
        """Generate progress certificate for a time period

        Args:
            student_name: Name of the student
            period: Time period (e.g., "November 2025", "Fall Semester")
            sections_completed: Sections completed in period
            xp_earned: XP earned in period
            streak_days: Best streak in period
            quizzes_passed: Number of quizzes passed

        Returns:
            PDF bytes
        """
        pdf = CertificatePDF()
        pdf.add_page()
        pdf.add_decorative_border()
        pdf.add_header_decoration()

        # Title
        pdf.set_font('Helvetica', 'B', 32)
        pdf.set_text_color(41, 98, 255)
        pdf.set_xy(0, 35)
        pdf.cell(297, 15, pdf.pdf_text('Progress Certificate'), 0, 1, 'C')

        # Period
        pdf.set_font('Helvetica', 'I', 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(297, 8, pdf.pdf_text(period), 0, 1, 'C')

        # Student name
        pdf.set_font('Helvetica', 'B', 28)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(8)
        pdf.cell(297, 12, pdf.pdf_text(student_name), 0, 1, 'C')

        # Decorative line
        pdf.set_draw_color(255, 193, 7)
        pdf.set_line_width(1)
        pdf.line(80, pdf.get_y() + 2, 217, pdf.get_y() + 2)

        # Achievement summary
        pdf.ln(12)
        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(297, 6, pdf.pdf_text('has demonstrated outstanding dedication to learning'), 0, 1, 'C')

        # Stats boxes
        pdf.ln(10)
        box_width = 55
        start_x = 45
        box_y = pdf.get_y()

        stats = [
            ("Sections", str(sections_completed)),
            ("XP Earned", f"{xp_earned:,}"),
            ("Best Streak", f"{streak_days} days"),
            ("Quizzes", str(quizzes_passed)),
        ]

        for i, (label, value) in enumerate(stats):
            x = start_x + (i * 55)

            # Box background
            pdf.set_fill_color(240, 245, 255)
            pdf.rect(x, box_y, box_width - 5, 25, 'F')

            # Icon and value
            pdf.set_xy(x, box_y + 3)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(41, 98, 255)
            pdf.cell(box_width - 5, 8, pdf.pdf_text(value), 0, 1, 'C')

            # Label
            pdf.set_xy(x, box_y + 14)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(box_width - 5, 6, pdf.pdf_text(label), 0, 1, 'C')

        # Encouragement
        pdf.set_xy(0, box_y + 40)
        pdf.set_font('Helvetica', 'I', 11)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(297, 6, pdf.pdf_text('Keep up the amazing work!'), 0, 1, 'C')

        # Date
        pdf.ln(8)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(297, 6, pdf.pdf_text(f"Generated on {datetime.now().strftime('%B %d, %Y')}"), 0, 1, 'C')

        # Footer
        pdf.set_xy(0, 175)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(41, 98, 255)
        pdf.cell(297, 6, pdf.pdf_text('InstaSchool'), 0, 1, 'C')
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(297, 5, pdf.pdf_text('Personalized Learning Achievement'), 0, 1, 'C')

        return bytes(pdf.output())

    def generate_custom_certificate(
        self,
        student_name: str,
        title: str,
        main_text: str,
        subtitle: str = "",
        footer_text: str = ""
    ) -> bytes:
        """Generate custom certificate with user-defined text

        Args:
            student_name: Name of the student
            title: Certificate title
            main_text: Main body text
            subtitle: Optional subtitle
            footer_text: Optional footer text

        Returns:
            PDF bytes
        """
        pdf = CertificatePDF()
        pdf.add_page()
        pdf.add_decorative_border()
        pdf.add_header_decoration()

        # Title
        pdf.set_font('Helvetica', 'B', 32)
        pdf.set_text_color(41, 98, 255)
        pdf.set_xy(0, 35)
        pdf.cell(297, 15, pdf.pdf_text(title), 0, 1, 'C')

        # Subtitle
        if subtitle:
            pdf.set_font('Helvetica', 'I', 14)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(297, 8, pdf.pdf_text(subtitle), 0, 1, 'C')

        # Student name
        pdf.set_font('Helvetica', 'B', 28)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)
        pdf.cell(297, 12, pdf.pdf_text(student_name), 0, 1, 'C')

        # Decorative line
        pdf.set_draw_color(255, 193, 7)
        pdf.set_line_width(1)
        pdf.line(80, pdf.get_y() + 2, 217, pdf.get_y() + 2)

        # Main text
        pdf.ln(15)
        pdf.set_font('Helvetica', '', 14)
        pdf.set_text_color(60, 60, 60)

        # Handle multi-line main text
        lines = main_text.split('\n')
        for line in lines:
            pdf.cell(297, 8, pdf.pdf_text(line.strip()), 0, 1, 'C')

        # Date
        pdf.ln(15)
        pdf.set_font('Helvetica', 'I', 11)
        pdf.cell(297, 6, pdf.pdf_text(f"Awarded on {datetime.now().strftime('%B %d, %Y')}"), 0, 1, 'C')

        # Footer
        pdf.set_xy(0, 170)
        if footer_text:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(297, 5, pdf.pdf_text(footer_text), 0, 1, 'C')

        pdf.set_xy(0, 180)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(41, 98, 255)
        pdf.cell(297, 6, pdf.pdf_text('InstaSchool'), 0, 1, 'C')

        return bytes(pdf.output())


# Singleton instance
_certificate_service_instance = None


def get_certificate_service() -> CertificateService:
    """Get or create the certificate service singleton

    Returns:
        CertificateService instance
    """
    global _certificate_service_instance
    if _certificate_service_instance is None:
        _certificate_service_instance = CertificateService()
    return _certificate_service_instance
