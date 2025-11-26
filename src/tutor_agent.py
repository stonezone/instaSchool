"""
Socratic Tutor Agent for InstaSchool Student Mode
Provides contextual, lesson-focused help through guided questioning
"""

from typing import Dict, List, Optional, Any
from src.core.types import BaseAgent
import json


class TutorAgent(BaseAgent):
    """
    Socratic tutor that helps students understand lesson content.
    Uses guided questioning and stays strictly within lesson context.
    """

    def __init__(self, client, model: str = "gpt-4.1-nano"):
        """
        Initialize the Tutor Agent.

        Args:
            client: OpenAI client instance
            model: Model to use (defaults to gpt-4.1-nano for efficiency)
        """
        super().__init__(client, model)
        self.current_context = None
        self.conversation_history = []
        self.max_history = 5  # Configurable conversation memory limit
        # Default persona settings
        self.persona_name = "a friendly tutor"
        self.persona_style = "an encouraging, supportive style"
        self.difficulty_level = 3  # Default to standard (1-5 scale)

    def set_lesson_context(self, unit_content: str, unit_title: str, subject: str, grade: str,
                           persona_name: Optional[str] = None, persona_style: Optional[str] = None):
        """
        Update the tutor's context when the student changes units.

        Args:
            unit_content: The markdown content of the current unit
            unit_title: Title of the current unit
            subject: Subject being studied
            grade: Grade level
            persona_name: Optional persona name (e.g., "Albert Einstein")
            persona_style: Optional teaching style (e.g., "curious, wonder-filled style")
        """
        self.current_context = {
            'unit_content': unit_content,
            'unit_title': unit_title,
            'subject': subject,
            'grade': grade
        }
        # Update persona if provided
        if persona_name:
            self.persona_name = persona_name
        if persona_style:
            self.persona_style = persona_style
        # Clear conversation history when context changes
        self.conversation_history = []

    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []

    def get_system_prompt(self) -> str:
        """
        Generate the system prompt for the tutor.

        Returns:
            System prompt string with current context
        """
        if not self.current_context:
            return "You are a helpful tutor. Please ask the student to select a lesson first."

        grade = self.current_context['grade']

        return f"""You are {self.persona_name}. Speak in {self.persona_style}, but keep explanations simple for a {grade} student.

You are helping a {grade} student understand "{self.current_context['unit_title']}" in {self.current_context['subject']}.

CRITICAL RULES:
1. ONLY answer questions about this specific lesson content
2. Use the Socratic method - guide with questions rather than giving direct answers
3. Keep responses concise (max 3-4 sentences)
4. Be encouraging and supportive
5. If asked about unrelated topics, gently redirect to the lesson
6. Use age-appropriate language for {grade} students

LESSON CONTENT:
{self.current_context['unit_content']}

TEACHING APPROACH:
- Start with encouragement appropriate to your persona
- Ask guiding questions like "What do you think would happen if...?"
- Help students discover answers themselves
- Connect concepts to things they already know
- Celebrate their thinking process, not just correct answers"""

    def get_response(self, student_question: str, temperature: float = 0.7) -> str:
        """
        Generate a tutor response to a student question.

        Args:
            student_question: The student's question or message
            temperature: Creativity level (0.7 default for balanced responses)

        Returns:
            The tutor's response string
        """
        if not self.current_context:
            return "📚 Please select a lesson first! Once you choose a unit from the menu, I'll be ready to help you understand it better."

        # Add student question to history
        self.conversation_history.append({
            "role": "user",
            "content": student_question
        })

        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            # Keep only the last max_history exchanges
            self.conversation_history = self.conversation_history[-(self.max_history * 2):]

        # Build messages for the API
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]

        # Add conversation history
        messages.extend(self.conversation_history)

        try:
            # Make the API call with token limit
            response = self._call_model(
                messages=messages,
                temperature=temperature
            )

            if response and response.choices:
                tutor_response = response.choices[0].message.content

                # Limit response length (approximately 500 tokens)
                if len(tutor_response) > 500:
                    tutor_response = tutor_response[:500].rsplit('.', 1)[0] + '.'

                # Add tutor response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": tutor_response
                })

                return tutor_response
            else:
                return "🤔 I'm having trouble thinking right now. Can you try asking your question again?"

        except Exception as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Tutor response generation")
            return "😅 Oops! Something went wrong. Let's try that again - can you rephrase your question?"

    def get_example_questions(self) -> List[str]:
        """
        Generate example questions based on current lesson context.

        Returns:
            List of example questions students could ask
        """
        if not self.current_context:
            return [
                "What is this topic about?",
                "Can you help me understand this?",
                "Why is this important?"
            ]

        # Generate contextual examples based on the unit title
        unit_title = self.current_context.get('unit_title', '')

        examples = [
            f"What's the main idea of {unit_title}?",
            f"Can you give me an example of this?",
            f"Why do we need to learn about {unit_title}?",
            f"I'm confused about this part, can you help?",
            f"How does this connect to what we learned before?"
        ]

        return examples[:3]  # Return top 3 most relevant

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current conversation.

        Returns:
            Dictionary with conversation statistics
        """
        return {
            'message_count': len(self.conversation_history),
            'current_unit': self.current_context.get('unit_title', 'No unit selected') if self.current_context else 'No unit selected',
            'history': self.conversation_history
        }