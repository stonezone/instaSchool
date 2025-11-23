"""
Agent Framework for Curriculum Generation
Implements an orchestrator-worker pattern where a coordinator agent delegates tasks to specialized agents
"""

import os
import json
import time
import base64
import httpx
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Try to import matplotlib, but provide a fallback for testing
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    print("Warning: matplotlib not installed, chart generation will not work.")
    MATPLOTLIB_AVAILABLE = False

# Import caching system
try:
    from services.cache_service import SmartCache
    CACHE_AVAILABLE = True
except ImportError:
    print("Warning: cache_service not available, caching disabled.")
    CACHE_AVAILABLE = False

# Import retry system
try:
    from services.retry_service import RetryHandler, with_retry, GracefulDegradation
    RETRY_AVAILABLE = True
except ImportError:
    print("Warning: retry_service not available, retry disabled.")
    RETRY_AVAILABLE = False

class BaseAgent:
    """Base class for all agents with common functionality"""
    def __init__(self, client, model="gpt-4.1"):
        self.client = client
        self.model = model
        
        # Initialize caching
        if CACHE_AVAILABLE:
            self.cache = SmartCache()
        else:
            self.cache = None
        
        # Initialize retry handler
        if RETRY_AVAILABLE:
            self.retry_handler = RetryHandler()
        else:
            self.retry_handler = None
        
        # Try to import the logger
        try:
            from src.verbose_logger import get_logger
            self.logger = get_logger()
            # Pass logger to retry handler
            if self.retry_handler:
                self.retry_handler.logger = self.logger
        except ImportError:
            self.logger = None
            print("Warning: Could not import verbose_logger. API call logging will be disabled.")
    
    def _call_model_cached(self, content_type: str, cache_params: Dict[str, Any], 
                          messages: List[Dict[str, str]], response_format=None, temperature=0.7):
        """Call model with caching support
        
        Args:
            content_type: Type of content being generated (for cache key)
            cache_params: Parameters to use for cache key generation
            messages: Messages for the API call
            response_format: Optional response format
            temperature: Temperature setting
            
        Returns:
            API response or cached content
        """
        # Try cache first if available
        if self.cache:
            cached_content = self.cache.get_similar_content(content_type, cache_params)
            if cached_content:
                # Create a mock response object for consistency
                class CachedResponse:
                    def __init__(self, content):
                        self.choices = [type('obj', (object,), {'message': type('obj', (object,), {'content': content})()})]
                        
                return CachedResponse(cached_content)
        
        # If no cache hit, make the API call
        response = self._call_model(messages, response_format, temperature)
        
        # Cache the response if successful
        if response and response.choices and self.cache:
            content = response.choices[0].message.content
            self.cache.content_cache.cache_content(content_type, cache_params, content)
            
        return response
    
    def _call_model(self, messages, response_format=None, temperature=0.7):
        """Call the model with standard parameters and retry logic"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            params["response_format"] = response_format
        
        # Create a safe copy of params for logging
        if self.logger:
            log_params = params.copy()
            # Truncate messages to avoid overwhelming logs
            if 'messages' in log_params and isinstance(log_params['messages'], list):
                truncated_messages = []
                for msg in log_params['messages']:
                    truncated_msg = msg.copy()
                    if 'content' in truncated_msg and isinstance(truncated_msg['content'], str) and len(truncated_msg['content']) > 500:
                        truncated_msg['content'] = truncated_msg['content'][:500] + "... [content truncated]"
                    truncated_messages.append(truncated_msg)
                log_params['messages'] = truncated_messages
            
            # Log the API request
            self.logger.log_api_request(model=self.model, endpoint="chat.completions", params=log_params)
        
        # Define the API call function for retry
        def make_api_call():
            response = self.client.chat.completions.create(**params)
            
            # Log the response if logger is available
            if self.logger:
                self.logger.log_api_response(model=self.model, response=response)
                
            return response
        
        try:
            # Use retry handler if available
            if self.retry_handler:
                return self.retry_handler.retry_with_backoff(
                    make_api_call,
                    context=f"{self.model} API call"
                )
            else:
                return make_api_call()
                
        except Exception as e:
            error_msg = str(e)
            print(f"Model call error: {e}")
            
            # Log the error if logger is available
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="API call")
            
            # Check for quota error and display in UI
            if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                try:
                    import streamlit as st
                    st.error("⚠️ OpenAI API quota exceeded. Please check your billing details or try again later.")
                except ImportError:
                    pass
            
            return None


class OrchestratorAgent(BaseAgent):
    """Main agent that coordinates the curriculum generation process"""
    
    def __init__(self, client, model="gpt-4.1", worker_model="gpt-4.1-mini"):
        super().__init__(client, model)
        self.worker_model = worker_model
        
    def create_curriculum(self, subject, grade, style, language, extra, config):
        """Main entry point for curriculum generation"""
        # Try to access the streamlit session state to check for cancellation
        try:
            import streamlit as st
            has_cancellation_check = True
        except ImportError:
            has_cancellation_check = False
        
        # Create a plan for curriculum generation
        plan = self._create_generation_plan(subject, grade, style, language, extra)
        
        # Check for cancellation
        if has_cancellation_check and not st.session_state.get("generating", True):
            print("Generation cancelled during planning phase")
            return {"meta": {"cancelled": True}, "units": []}
        
        # Initialize worker agents with appropriate models
        outline_agent = OutlineAgent(self.client, self.worker_model, config)
        content_agent = ContentAgent(self.client, self.worker_model, config)
        media_agent = MediaAgent(self.client, config)  # Note: MediaAgent uses image models, not text models
        chart_agent = ChartAgent(self.client, self.worker_model, config)
        quiz_agent = QuizAgent(self.client, self.worker_model, config)
        summary_agent = SummaryAgent(self.client, self.worker_model, config)
        resource_agent = ResourceAgent(self.client, self.worker_model, config)
        
        # Step 1: Generate outline
        topics = outline_agent.generate_outline(
            subject, grade, style, extra, 
            config["defaults"]["min_topics"], 
            config["defaults"]["max_topics"], 
            language
        )
        
        # Check for cancellation
        if has_cancellation_check and not st.session_state.get("generating", True):
            print("Generation cancelled after outline phase")
            return {"meta": {"cancelled": True}, "units": []}
        
        # Initialize curriculum structure
        curriculum = {
            "meta": {
                "subject": subject,
                "grade": grade,
                "style": style,
                "language": language,
                "extra": extra,
                "plan": plan,
                "include_quizzes": config["defaults"]["include_quizzes"],
                "include_summary": config["defaults"]["include_summary"],
                "include_resources": config["defaults"]["include_resources"],
                "include_keypoints": config["defaults"]["include_keypoints"],
                "media_richness": config["defaults"]["media_richness"],
            },
            "units": []
        }
        
        # Process each topic concurrently or sequentially as needed
        for i, topic in enumerate(topics):
            # Check for cancellation
            if has_cancellation_check and not st.session_state.get("generating", True):
                print(f"Generation cancelled after processing {i} of {len(topics)} topics")
                return curriculum  # Return what we have so far
            
            # Provide detailed instructions to content agent based on plan
            unit = self._process_topic(
                topic, subject, grade, style, language, extra, 
                content_agent, media_agent, chart_agent, quiz_agent, 
                summary_agent, resource_agent, config
            )
            curriculum["units"].append(unit)
            
            # Update progress in session state after each unit
            if has_cancellation_check:
                # Calculate total progress (planning + outline = 0.3, each topic = (0.9-0.3)/num_topics)
                topic_progress = 0.6 / len(topics)
                st.session_state.progress = 0.3 + (i + 1) * topic_progress
        
        # Check for cancellation before refinement
        if has_cancellation_check and not st.session_state.get("generating", True):
            print("Generation cancelled before refinement")
            return curriculum
            
        # Final review and refinement
        curriculum = self._refine_curriculum(curriculum)
        return curriculum
    
    def _create_generation_plan(self, subject, grade, style, language, extra):
        """Create a detailed plan for generating the curriculum"""
        messages = [
            {"role": "system", "content": 
                "You are a curriculum planning specialist. Create a detailed plan for generating an educational curriculum."},
            {"role": "user", "content": 
                f"Create a detailed plan for generating a {style} curriculum for {subject} at grade {grade} in {language}. "
                f"Additional guidelines: {extra}\n\n"
                f"The plan should include: 1) How topics should be structured, 2) What teaching approaches to use, "
                f"3) What visual aids would be most effective, 4) How to assess understanding, and 5) How topics should build on each other."
            }
        ]
        
        response = self._call_model(messages)
        if response and response.choices:
            return response.choices[0].message.content
        return "Standard curriculum generation plan"
    
    def _process_topic(self, topic, subject, grade, style, language, extra, 
                      content_agent, media_agent, chart_agent, quiz_agent, 
                      summary_agent, resource_agent, config):
        """Process a single topic with specialized agents"""
        topic_title = topic.get("title", "Untitled Topic")
        
        # Initialize unit structure
        unit = {
            "title": topic_title,
            "content": "",
            "images": [],
            "selected_image_b64": None,
            "chart": None,
            "chart_suggestion": None,
            "quiz": None,
            "summary": "",
            "resources": ""
        }
        
        # Generate content with enhanced context
        unit["content"] = content_agent.generate_content(
            topic_title, subject, grade, style, extra, language, 
            config["defaults"]["include_keypoints"]
        )
        
        # Generate images if media richness allows
        media_richness = config["defaults"]["media_richness"]
        if media_richness >= 2 and unit["content"]:
            num_images = 3 if media_richness >= 5 else 1
            
            # First generate a content-aware image prompt using the ImagePromptAgent
            custom_prompt = None
            try:
                # Create an image prompt agent with the same model as the worker
                image_prompt_agent = ImagePromptAgent(self.client, self.worker_model, config)
                
                # Generate a custom prompt based on the actual content
                custom_prompt = image_prompt_agent.create_image_prompt(
                    unit["content"], topic_title, subject, grade, style, language
                )
                
                if not custom_prompt:
                    print("Warning: Could not generate custom image prompt, using default template")
            except Exception as e:
                print(f"Error generating custom image prompt: {e}")
                
            # Generate images using MediaAgent
            try:
                unit["images"] = media_agent.create_images(
                    topic_title, subject, grade, style, language, 
                    n=num_images, custom_prompt=custom_prompt
                )
            except Exception as e:
                print(f"Error generating images: {e}")
                unit["images"] = []
                    
            # Safer handling of image selection
            if unit["images"]:
                # Find the first valid image with b64 data
                for img in unit["images"]:
                    if img.get("b64"):
                        unit["selected_image_b64"] = img["b64"]
                        break
        
        # Generate chart if needed (media_richness >= 3)
        if media_richness >= 3:
            suggestion = chart_agent.suggest_chart(
                topic_title, subject, grade, style, language
            )
            if suggestion:
                unit["chart_suggestion"] = suggestion
                unit["chart"] = chart_agent.create_chart(suggestion)
        
        # Generate additional components as needed
        if config["defaults"]["include_quizzes"]:
            unit["quiz"] = quiz_agent.generate_quiz(
                topic_title, subject, grade, style, language
            )
        
        if config["defaults"]["include_summary"]:
            unit["summary"] = summary_agent.generate_summary(
                topic_title, subject, grade, language
            )
        
        if config["defaults"]["include_resources"]:
            unit["resources"] = resource_agent.generate_resources(
                topic_title, subject, grade, language
            )
        
        return unit
    
    def _refine_curriculum(self, curriculum):
        """Perform final refinements on the entire curriculum"""
        messages = [
            {"role": "system", "content": 
                "You are a curriculum review specialist. Review this curriculum for coherence and consistency."},
            {"role": "user", "content": 
                f"Review this curriculum for {curriculum['meta']['subject']} at grade {curriculum['meta']['grade']}. "
                f"Check that topics build on each other logically, content is appropriate for the grade level, "
                f"and all components follow a consistent style and approach.\n\n"
                f"Curriculum topics: {[unit['title'] for unit in curriculum['units']]}"
            }
        ]
        
        response = self._call_model(messages)
        if response and response.choices:
            curriculum["meta"]["review_notes"] = response.choices[0].message.content
        
        return curriculum


class OutlineAgent(BaseAgent):
    """Agent responsible for generating the curriculum outline and topics"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("outline", "")
    
    def generate_outline(self, subject, grade, style, extra, min_topics, max_topics, language) -> List[Dict[str, Any]]:
        # Create cache parameters
        cache_params = {
            'subject': subject,
            'grade': grade,
            'style': style,
            'extra': extra,
            'min_topics': min_topics,
            'max_topics': max_topics,
            'language': language
        }
        
        sys_prompt = self.prompt_template.format(
            subject=subject, grade=grade, style=style, extra=extra,
            min_topics=min_topics, max_topics=max_topics, language=language)
        
        try:
            response = self._call_model_cached(
                "outlines",
                cache_params,
                [{"role": "system", "content": sys_prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    topics_list = data.get("topics", [])
                    return [{"title": topic} for topic in topics_list]
                except json.JSONDecodeError:
                    print(f"JSON decode error: {content}")
            return []
        except Exception as e:
            print(f"Outline generation error: {e}")
            return []


class ContentAgent(BaseAgent):
    """Agent responsible for generating the main lesson content"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("content", "")
    
    def generate_content(self, topic, subject, grade, style, extra, language, include_keypoints) -> str:
        # Create cache parameters
        cache_params = {
            'topic': topic,
            'subject': subject,
            'grade': grade,
            'style': style,
            'extra': extra,
            'language': language,
            'include_keypoints': include_keypoints
        }
        
        keypoints_instruction = "Include a concise list of key takeaways or learning points at the end, formatted with Markdown bullet points." if include_keypoints else ""
        
        sys_prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            style=style or "[Style Missing]",
            extra=extra or "[No Extra Guidelines]",
            language=language or "English",
            include_keypoints_instruction=keypoints_instruction
        )
        
        try:
            response = self._call_model_cached(
                "content",
                cache_params,
                [{"role": "system", "content": sys_prompt}],
                temperature=0.7
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Content generation error: {e}")
            return f"[Error: Content generation failed - {str(e)}]"


class MediaAgent:
    """Agent responsible for generating images using ImageGenerator"""
    
    def __init__(self, client, config):
        self.config = config  # Store full config to access defaults
        self.prompt_template = config["prompts"].get("image", "")
        self.client = client
        
        # Initialize ImageGenerator with proper model
        from src.image_generator import ImageGenerator
        default_model = config["defaults"].get("image_model", "dall-e-3")
        self.image_generator = ImageGenerator(client, default_model)
        
        # Try to import the logger
        try:
            from src.verbose_logger import get_logger
            self.logger = get_logger()
        except ImportError:
            self.logger = None

    def create_images(self, topic, subject, grade, style="educational", language="English", n=1, 
                      model_name=None, custom_prompt=None) -> List[Dict[str, Optional[str]]]:
        """Delegate image generation to ImageGenerator for consistency
        
        Args:
            topic: The topic to generate images for
            subject: The subject area
            grade: The grade level
            style: The teaching style
            language: The language
            n: Number of images to generate
            model_name: Optional model name override
            custom_prompt: Optional custom prompt that takes precedence over the template
            
        Returns:
            List of dictionaries with image data
        """
        if not topic:
            return []

        # Use the custom prompt if provided, otherwise generate from template
        if custom_prompt:
            prompt = custom_prompt
            print(f"Using custom image prompt based on lesson content analysis")
        else:
            prompt = self.prompt_template.format(
                topic=topic, subject=subject, grade=grade, style=style, language=language
            )
            print(f"Using standard template-based image prompt")
        
        # Get image size from config if available
        config_size = self.config["defaults"].get("image_size") if self.config and "defaults" in self.config else None
        
        # Delegate to ImageGenerator for actual image creation
        return self.image_generator.create_image(
            prompt=prompt,
            model=model_name,
            size=config_size,
            n=n,
            topic=topic,
            subject=subject,
            grade=grade,
            style=style,
            language=language
        )


class ChartAgent(BaseAgent):
    """Agent responsible for generating chart suggestions and visualizations"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("chart", "")
    
    def suggest_chart(self, topic, subject, grade, style, language) -> Optional[Dict[str, Any]]:
        prompt = self.prompt_template.format(
            topic=topic, subject=subject, grade=grade, style=style, language=language
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    # Add the suggestion text for reference
                    data["suggestion_text"] = f"Chart type: {data.get('chart_type', 'unknown')}, Title: {data.get('title', 'untitled')}"
                    return data
                except json.JSONDecodeError:
                    print(f"Chart JSON decode error: {content}")
            return None
        except Exception as e:
            print(f"Chart suggestion error: {e}")
            return None
    
    def create_chart(self, chart_info: Optional[Dict[str, Any]]) -> Optional[Dict[str, Optional[str]]]:
        """Creates a chart using Matplotlib based on the suggestion."""
        if not chart_info:
            return None

        # Check if matplotlib is available
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot create chart: matplotlib is not installed.")
            try:
                import streamlit as st
                st.warning("Chart generation requires matplotlib which is not installed.")
            except ImportError:
                pass  # Can't import streamlit, skip UI notification
            return {"title": chart_info.get("title", "Chart"), "b64": None, "error": "matplotlib not installed"}

        # Safely extract data with defaults
        chart_type = chart_info.get("chart_type", "Bar").capitalize()
        title = chart_info.get("title", "Generated Chart")
        data = chart_info.get("data", {})
        labels = data.get("labels", [])
        values = data.get("values", [])
        x_label = chart_info.get("x_label", "")
        y_label = chart_info.get("y_label", "Values")

        # Validation before plotting
        if not labels or not values:
            error_msg = f"Cannot create chart '{title}': Missing labels or values."
            print(error_msg)
            try:
                import streamlit as st
                st.warning(f"Chart generation issue: {error_msg}")
            except ImportError:
                pass
            return None

        try:
            # Attempt to convert values to numeric, handle potential errors
            numeric_values = []
            for v in values:
                try:
                    # Handle negative values properly
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    # Use a small positive value as fallback for non-numeric data
                    numeric_values.append(0.1)
                    print(f"Warning: Non-numeric value '{v}' in chart data, using placeholder.")
        except Exception as e:
            error_msg = f"Cannot create chart '{title}': Values contain non-numeric data ({values}). Error: {e}"
            print(error_msg)
            try:
                import streamlit as st
                st.warning(f"Chart generation issue: {error_msg}")
            except ImportError:
                pass
            return None

        # Plotting (only if matplotlib is available)
        fig = None
        try:
            fig, ax = plt.subplots(figsize=(6, 4))

            # For pie charts, ensure all values are positive
            if chart_type == "Pie":
                # Convert any negative values to positive for pie charts
                numeric_values = [max(0.1, abs(v)) for v in numeric_values]

            if chart_type == "Bar":
                ax.bar(labels, numeric_values, color='skyblue')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                # Add value labels on top of bars
                for i, v in enumerate(numeric_values):
                    ax.text(i, v, str(v), ha='center', va='bottom')
            elif chart_type == "Line":
                ax.plot(labels, numeric_values, marker='o', linestyle='-', color='green')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                # Add data point labels
                for i, v in enumerate(numeric_values):
                    ax.text(i, v, str(v), ha='center', va='bottom')
            elif chart_type == "Pie":
                try:
                    # Handle case where all values are 0
                    if all(v == 0 for v in numeric_values):
                        numeric_values = [1] * len(numeric_values)
                    
                    ax.pie(numeric_values, labels=labels, autopct='%1.1f%%', 
                           shadow=True, startangle=90)
                    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                except Exception as pie_error:
                    print(f"Error with pie chart, falling back to bar: {pie_error}")
                    # Fall back to bar chart if pie chart fails
                    ax.clear()
                    ax.bar(labels, numeric_values, color='skyblue')
                    ax.set_xlabel(x_label)
                    ax.set_ylabel(y_label)
            else:
                # Default to bar chart if unrecognized type
                ax.bar(labels, numeric_values, color='skyblue')
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)

            ax.set_title(title)
            plt.tight_layout()

            # Save to bytes
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            plt.close(fig)  # Close figure to avoid memory leaks

            # Convert to base64
            image_b64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            return {"b64": image_b64, "title": title}

        except Exception as e:
            error_msg = f"Error creating chart: {e}"
            print(error_msg)
            if fig:
                plt.close(fig)  # Close figure to avoid memory leaks
            
            try:
                import streamlit as st
                st.warning(f"Chart generation issue: {error_msg}")
            except ImportError:
                pass
                
            return None


class QuizAgent(BaseAgent):
    """Agent responsible for generating quiz questions"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("quiz", "")
    
    def generate_quiz(self, topic, subject, grade, style, language) -> Optional[List[Dict[str, Any]]]:
        prompt = self.prompt_template.format(
            topic=topic, subject=subject, grade=grade, style=style, language=language
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                try:
                    data = json.loads(content)
                    return data.get("quiz", [])
                except json.JSONDecodeError:
                    print(f"Quiz JSON decode error: {content}")
            return None
        except Exception as e:
            print(f"Quiz generation error: {e}")
            return None


class SummaryAgent(BaseAgent):
    """Agent responsible for generating lesson summaries"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("summary", "")
    
    def generate_summary(self, topic, subject, grade, language) -> str:
        prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            language=language or "English"
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                temperature=0.7
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Summary generation error: {e}")
            return ""


class ResourceAgent(BaseAgent):
    """Agent responsible for suggesting further resources"""
    
    def __init__(self, client, model, config):
        super().__init__(client, model)
        self.prompt_template = config["prompts"].get("resources", "")
    
    def generate_resources(self, topic, subject, grade, language) -> str:
        prompt = self.prompt_template.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            language=language or "English"
        )
        
        try:
            response = self._call_model(
                [{"role": "system", "content": prompt}],
                temperature=0.7
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            print(f"Resources generation error: {e}")
            return ""


class ImagePromptAgent(BaseAgent):
    """Agent that analyzes lesson content and generates tailored image prompts"""
    
    def __init__(self, client, model, config=None):
        super().__init__(client, model)
        # Default prompt if not in config
        self.default_prompt = """
        You are an expert at creating educational image prompts that perfectly match lesson content.
        
        You'll be given a lesson about "{topic}" in {subject} for grade {grade} students.
        
        Your task is to:
        1. Analyze the specific concepts, examples, and explanations in the lesson
        2. Identify the most important visual elements that would enhance understanding
        3. Create a detailed, specific image prompt (200-250 words) that would generate an illustration
           directly supporting this exact lesson content - not just the general topic
        
        Important:
        - Focus on the specific content actually mentioned in the lesson, not general knowledge about the topic
        - Be concrete and detailed, describing specific elements that should appear in the image
        - Include age-appropriate complexity for grade {grade} students
        - Incorporate the lesson's teaching style: {style}
        - Consider cultural context for: {language}
        - Include colors, composition details, and mood of the image
        
        Your prompt should produce an image that:
        - Directly supports the learning objectives in the content
        - Visualizes the most difficult or abstract concept from the lesson
        - Would make sense to a student after reading this exact lesson
        """
    
    def create_image_prompt(self, content, topic, subject, grade, style, language) -> str:
        """Analyze content and create a tailored image prompt
        
        Args:
            content: The lesson content to analyze
            topic: The topic title
            subject: The subject
            grade: The grade level
            style: The teaching style
            language: The language
            
        Returns:
            str: A detailed image prompt based on the content
        """
        # Format the system prompt with metadata
        system_prompt = self.default_prompt.format(
            topic=topic or "[Topic Missing]",
            subject=subject or "[Subject Missing]",
            grade=grade or "[Grade Missing]",
            style=style or "[Style Missing]",
            language=language or "English"
        )
        
        # Create a user prompt with the content to analyze
        user_prompt = f"""
        TOPIC: {topic}
        SUBJECT: {subject}
        GRADE: {grade}
        
        LESSON CONTENT TO ANALYZE:
        {content[:3000]}  # Use first 3000 chars for analysis
        
        Based on this specific lesson content, create a detailed, education-focused image prompt that would 
        generate an illustration perfectly matched to what students are learning in this text.
        """
        
        try:
            # Make the API call
            response = self._call_model(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            # Process the response
            if response and response.choices:
                custom_prompt = response.choices[0].message.content
                
                # Log for debugging
                if self.logger:
                    self.logger.log_debug(f"Generated custom image prompt: {custom_prompt[:100]}...")
                print(f"Generated custom image prompt based on lesson content: {custom_prompt[:100]}...")
                
                return custom_prompt
            
            # Fallback if API call fails
            return None
        except Exception as e:
            print(f"Image prompt generation error: {e}")
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Image prompt generation")
            return None