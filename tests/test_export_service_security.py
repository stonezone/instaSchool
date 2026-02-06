"""
Security regression tests for HTML export sanitization.
"""

from services.export_service import CurriculumExporter


def test_generate_html_escapes_untrusted_html():
    exporter = CurriculumExporter()
    curriculum = {
        "meta": {
            "subject": "<script>alert(1)</script>",
            "grade": "5",
        },
        "units": [
            {
                "title": "<img src=x onerror=alert(2)>",
                "introduction": "Intro <script>evil()</script>",
                "content": "Body <b>safe?</b> <script>boom()</script>",
                "quiz": {
                    "questions": [
                        {
                            "question": "<script>q()</script>",
                            "options": ["<img src=x onerror=1>", "A"],
                        }
                    ]
                },
                "resources": [
                    "<script>r()</script>",
                    {"title": "<script>t()</script>", "url": "javascript:alert(9)"},
                ],
            }
        ],
    }

    html = exporter.generate_html(curriculum)

    assert "<script>alert(1)</script>" not in html
    assert "<script>evil()</script>" not in html
    assert "<script>boom()</script>" not in html
    assert "<script>q()</script>" not in html
    assert "<script>r()</script>" not in html
    assert "javascript:alert(9)" not in html

    # Escaped content should be present as text.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(2)&gt;" in html


def test_generate_html_allows_safe_resource_links():
    exporter = CurriculumExporter()
    curriculum = {
        "meta": {"subject": "Science", "grade": "5"},
        "units": [
            {
                "title": "Unit 1",
                "resources": {
                    "links": [
                        {"title": "Good", "url": "https://example.com"},
                        {"title": "Mail", "url": "mailto:test@example.com"},
                    ]
                },
            }
        ],
    }

    html = exporter.generate_html(curriculum)
    assert 'href="https://example.com"' in html
    assert 'href="mailto:test@example.com"' in html
