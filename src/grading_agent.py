"""
AI Grading Agent for InstaSchool
Provides intelligent feedback on student short-answer responses.
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from openai import APIError, RateLimitError, APIConnectionError

# Import logger
try:
    from src.verbose_logger import get_logger
    _logger = get_logger()
except ImportError:
    _logger = None


@dataclass
class GradingResult:
    """Result of grading a student's answer"""
    score: float  # 0.0 to 1.0
    feedback: str  # Constructive feedback
    is_correct: bool  # Simplified correct/incorrect
    strengths: List[str]  # What the student did well
    improvements: List[str]  # Areas to improve
    model_answer: Optional[str] = None  # Example correct answer
    graded: bool = True  # Whether the answer was actually graded by AI


class GradingAgent:
    """
    AI agent that grades open-ended student responses
    and provides constructive, educational feedback.
    """

    GRADING_PROMPT = """You are an encouraging educational grading assistant. Your job is to evaluate a student's answer and provide helpful, constructive feedback.

CONTEXT:
- Subject: {subject}
- Grade Level: {grade}
- Unit Topic: {unit_title}
- Lesson Content Summary: {lesson_summary}

QUESTION:
{question}

STUDENT'S ANSWER:
{student_answer}

GRADING CRITERIA:
{criteria}

Please evaluate the student's answer and respond in the following JSON format:
{{
    "score": <0.0 to 1.0>,
    "is_correct": <true if score >= 0.6, false otherwise>,
    "feedback": "<2-3 sentences of constructive feedback, encouraging tone>",
    "strengths": ["<what the student did well>", "..."],
    "improvements": ["<specific suggestion for improvement>", "..."],
    "model_answer": "<brief example of a good answer>"
}}

IMPORTANT:
- Be encouraging, not discouraging
- Focus on what the student understands, not just mistakes
- Provide specific, actionable feedback
- Match feedback complexity to the grade level
- If the answer shows any understanding, acknowledge it"""

    def __init__(self, client, model: str = "gpt-4.1-nano", config: Optional[Dict] = None):
        """
        Initialize the grading agent.

        Args:
            client: OpenAI client instance
            model: Model to use for grading (default: gpt-4.1-nano for cost efficiency)
            config: Optional configuration dictionary
        """
        self.client = client
        self.model = model
        self.config = config or {}

        # Default grading criteria if not provided
        self.default_criteria = """
        - Understanding of key concepts (40%)
        - Accuracy of information (30%)
        - Clarity of explanation (20%)
        - Use of relevant examples or details (10%)
        """

    def grade_answer(
        self,
        question: str,
        student_answer: str,
        unit_title: str,
        lesson_content: str,
        subject: str = "General",
        grade: str = "K-12",
        criteria: Optional[str] = None
    ) -> GradingResult:
        """
        Grade a student's open-ended answer.

        Args:
            question: The question asked
            student_answer: The student's response
            unit_title: Title of the current unit
            lesson_content: Content of the lesson for context
            subject: Subject being studied
            grade: Grade level
            criteria: Optional custom grading criteria

        Returns:
            GradingResult with score, feedback, and suggestions
        """
        # Truncate lesson content to avoid token limits
        lesson_summary = lesson_content[:1500] + "..." if len(lesson_content) > 1500 else lesson_content

        prompt = self.GRADING_PROMPT.format(
            subject=subject,
            grade=grade,
            unit_title=unit_title,
            lesson_summary=lesson_summary,
            question=question,
            student_answer=student_answer,
            criteria=criteria or self.default_criteria
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            data = json.loads(result)

            return GradingResult(
                score=float(data.get('score', 0.5)),
                feedback=data.get('feedback', 'Thank you for your answer!'),
                is_correct=data.get('is_correct', False),
                strengths=data.get('strengths', []),
                improvements=data.get('improvements', []),
                model_answer=data.get('model_answer'),
                graded=True
            )

        except (APIError, RateLimitError, APIConnectionError) as api_err:
            # API-specific errors - log and fallback
            if _logger:
                _logger.log_error(error=api_err, model=self.model, context="Grading API call")
            return GradingResult(
                score=0.0,
                feedback="Grading service temporarily unavailable. Please try again.",
                is_correct=False,
                strengths=[],
                improvements=["Grading service unavailable"],
                model_answer=None,
                graded=False
            )
        except json.JSONDecodeError as json_err:
            # JSON parsing error - log and fallback
            if _logger:
                _logger.log_error(error=json_err, model=self.model, context="Grading response parsing")
            return GradingResult(
                score=0.0,
                feedback="Unable to process grading response. Please try again.",
                is_correct=False,
                strengths=[],
                improvements=["Response processing error"],
                model_answer=None,
                graded=False
            )
        except Exception as e:
            # Unexpected errors - log with full context and fallback
            if _logger:
                _logger.log_error(error=e, model=self.model, context="Grading unexpected error", include_traceback=True)
            return GradingResult(
                score=0.0,
                feedback="An unexpected error occurred during grading. Please try again.",
                is_correct=False,
                strengths=[],
                improvements=["Grading service unavailable"],
                model_answer=None,
                graded=False
            )

    def generate_short_answer_questions(
        self,
        unit_content: str,
        unit_title: str,
        subject: str,
        grade: str,
        num_questions: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate short-answer questions for a unit.

        Args:
            unit_content: Content of the unit
            unit_title: Title of the unit
            subject: Subject being studied
            grade: Grade level
            num_questions: Number of questions to generate

        Returns:
            List of question dictionaries
        """
        prompt = f"""Generate {num_questions} short-answer questions for students based on this lesson.

Subject: {subject}
Grade Level: {grade}
Unit: {unit_title}

Lesson Content:
{unit_content[:2000]}

Generate questions that:
1. Test understanding, not just memorization
2. Are appropriate for {grade} level students
3. Can be answered in 1-3 sentences
4. Have clear evaluation criteria

Respond in JSON format:
{{
    "questions": [
        {{
            "question": "<the question>",
            "type": "short_answer",
            "points": 10,
            "criteria": "<what makes a good answer>",
            "sample_answer": "<example of a good answer>"
        }}
    ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            data = json.loads(result)
            return data.get('questions', [])

        except (APIError, RateLimitError, APIConnectionError) as api_err:
            # API-specific errors - log and return fallback
            if _logger:
                _logger.log_error(error=api_err, model=self.model, context="Question generation API call")
            return self._fallback_questions(unit_title)
        except json.JSONDecodeError as json_err:
            # JSON parsing error - log and return fallback
            if _logger:
                _logger.log_error(error=json_err, model=self.model, context="Question generation parsing")
            return self._fallback_questions(unit_title)
        except Exception as e:
            # Unexpected errors - log with traceback and return fallback
            if _logger:
                _logger.log_error(error=e, model=self.model, context="Question generation unexpected error", include_traceback=True)
            return self._fallback_questions(unit_title)

    def _fallback_questions(self, unit_title: str) -> List[Dict[str, Any]]:
        """Return fallback questions when generation fails."""
        return [{
            "question": f"What did you learn about {unit_title}?",
            "type": "short_answer",
            "points": 10,
            "criteria": "Shows understanding of key concepts",
            "sample_answer": "A thoughtful summary of the main points."
        }]
