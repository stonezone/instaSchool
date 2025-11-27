# InstaSchool Curriculum Generator

An AI-powered educational curriculum generator that creates complete, media-rich learning materials for students across multiple subjects and grade levels.

![InstaSchool](https://img.shields.io/badge/InstaSchool-Curriculum_Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT_4.1-lightblue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

InstaSchool Curriculum Generator is a powerful tool that leverages advanced AI models to create comprehensive educational curriculum materials. Using a sophisticated agentic framework, the application generates coherent, age-appropriate content with illustrations, charts, quizzes, and supporting resources for a wide range of subjects and grade levels.

### Key Features

- **Agentic AI Framework**: Coordinated AI agents collaborate to create cohesive curriculum components
- **High-Quality Illustrations**: Advanced image generation with gpt-image-1 and gpt-image-1-mini
- **Interactive Content**: Quizzes with automatic feedback for student assessment
- **Data Visualization**: Relevant charts and graphs to support learning concepts
- **Multi-Subject Support**: Science, Math, Language Arts, Social Studies, and more
- **Grade-Appropriate Content**: From preschool through high school
- **Multiple Teaching Styles**: Standard, inquiry-based, project-based, story-based, and more
- **Full Export Options**: Export in HTML, Markdown, or PDF formats
- **Mobile Responsive**: Automatically adapts to mobile devices for on-the-go curriculum development

## Installation

### Prerequisites

- Python 3.9 or higher (required for OpenAI SDK 2.x)
- OpenAI API key with access to GPT-4.1 and image generation models
- Optional: Kimi/Moonshot API key for Kimi K2 models
- pip (Python package manager)

### Required Packages

```
streamlit>=1.51.0
openai>=2.8.1
pyyaml>=6.0
matplotlib>=3.5.0
pillow>=9.0.0
python-dotenv>=0.19.0
fpdf2>=2.7.0
plotly>=5.15.0
tenacity>=8.2.0
httpx>=0.23.0
markdown>=3.4.0
requests>=2.28.0
```

PDF export now uses the pure-Python `fpdf2` library and does not require any external OS binaries like `wkhtmltopdf`.

### Installation Steps

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/instaschool-curriculum-generator.git
cd instaschool-curriculum-generator
```

2. **Set up a virtual environment (recommended)**

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Install wkhtmltopdf** (optional, for PDF export)

- **macOS**:
  ```bash
  brew install wkhtmltopdf
  ```

- **Windows**:
  Download from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html) and add to PATH

- **Linux**:
  ```bash
  sudo apt-get install wkhtmltopdf
  ```

5. **Set up your OpenAI API key**

Create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_api_key_here
```

Or set it as an environment variable:
```bash
# On Windows (PowerShell)
$env:OPENAI_API_KEY="your_api_key_here"

# On macOS/Linux
export OPENAI_API_KEY="your_api_key_here"
```

## Usage

### Starting the Application

From the `release` directory, run:

```bash
streamlit run main.py
```

This will start a local web server and open the application in your default web browser (typically at http://localhost:8501).

#### Verbose Mode

You can enable verbose mode to see detailed API call logs:

```bash
streamlit run main.py -- --verbose
```

You can also specify a custom log file path:

```bash
streamlit run main.py -- --verbose --log-file=path/to/logfile.log
```

This will display all API requests and responses in the terminal and log them to the specified file.

#### Testing Logger Functionality

A test script is included to verify logger functionality:

```bash
python test_logger.py --verbose
```

This script simulates API calls and demonstrates how the logging works.

### Generating a Curriculum

1. **Configure Settings**
   - In the sidebar, select:
     - **Subject**: Choose from Science, Math, Language Arts, etc.
     - **Grade Level**: Select from Preschool through high school
     - **Style**: Choose a teaching approach (Standard, Inquiry-based, etc.)
     - **Language**: Select content language
     - **Advanced Settings**: Configure AI models, media richness, and component toggles

2. **Generate Content**
   - Navigate to the "Generate" tab
   - Enter any specific guidelines or focus for your curriculum (optional)
   - Check the cost estimation to understand token usage and approximate costs
   - Click the "🚀 Generate New Curriculum" button
   - Wait for the generation process to complete (typically 1-3 minutes)

3. **View and Edit**
   - Navigate to the "View & Edit" tab to see your generated curriculum
   - Toggle "Edit Mode" to make changes to any component
   - Select between multiple generated images
   - Try the interactive quizzes
   - Regenerate specific components as needed

4. **Export Your Curriculum**
   - Navigate to the "Export" tab
   - Choose to export as Markdown, HTML, or PDF
   - Select whether to include images in the export
   - Download the exported file

### Configuration

The application is highly configurable through the `config.yaml` file:

- **Prompts**: Customize the instructions for each AI agent
- **Default Settings**: Change default values for the UI
- **Model Selection**: Configure which AI models to use for text and images

## Troubleshooting

### Common Issues

#### API Key Issues

**Error**: "OPENAI_API_KEY not set in environment variable or .env file"
- **Solution**: Check that your API key is correctly set in the .env file or as an environment variable

**Error**: "Error: 401 - Unauthorized"
- **Solution**: Your API key may be invalid or expired. Check your OpenAI account to ensure your key is active.

**Error**: "⚠️ OpenAI API quota exceeded"
- **Solution**: You have reached your OpenAI API usage limit. Check your OpenAI account billing section and add credits if needed.

#### Generation Errors

**Error**: "Error generating curriculum"
- **Solution**: This could be due to API rate limits or network issues. Wait a few minutes and try again.

**Error**: "Error creating chart"
- **Solution**: Ensure matplotlib is properly installed. Try `pip install --force-reinstall matplotlib`.

**Error**: "Image generation failed" or "Image generation parameter issue"
- **Solution**: Check that you have access to the selected image model in your OpenAI account.
- **Alternative Solution**: Try switching to a different image model. DALL-E-2 and GPT-Image-1 have different parameter requirements.

#### Export Issues

**Error**: "PDF export is not available"
- **Solution**: Ensure wkhtmltopdf is correctly installed and in your PATH.

### Dependencies Issues

If you encounter issues with dependencies, try reinstalling them individually:

```bash
pip install --upgrade streamlit openai pyyaml matplotlib pillow python-dotenv fpdf2 plotly tenacity httpx markdown
```

### Resource Usage

- **High Token Usage Warning**: Generation of full curricula can consume a significant number of API tokens, especially when using high-quality models. Monitor your OpenAI API usage.

- **Slow Generation**: If generation is very slow, consider:
  - Reducing the media richness level
  - Reducing the number of topics
  - Using faster models in the advanced settings

## Advanced Configuration

### Custom Prompts

The `config.yaml` file contains all prompts used by the AI agents. You can modify these to achieve different results:

- **Content Style**: Adjust the content prompt to change the writing style
- **Image Guidance**: Modify the image prompt to get different illustration styles
- **Quiz Complexity**: Change the quiz prompt to alter the difficulty and format

### Cost Estimation

The application includes a cost estimation feature to help you understand token usage and API costs:

- **Estimated Tokens**: See the approximate number of tokens that will be used
- **Breakdown by Component**: Understand how content, images, charts, and quizzes contribute to total costs
- **Model-Specific Costs**: Different costs are calculated based on the selected models
- **Preview Before Generation**: Check estimated costs before generating to manage your API budget

Cost estimates are based on current OpenAI pricing and represent approximate values that may vary based on actual content generation.

### Model Selection

For best results:
- **Text Content**: Use GPT-4.1 for high-quality content (GPT-4o is a good alternative)
- **Worker Agents**: GPT-4.1-mini provides a good balance of quality and speed
- **Image Generation**: 
  - **GPT-Imagegen-1**: Highest quality educational illustrations (recommended)
  - **DALL-E 3**: High quality with creative elements
  - **DALL-E 2**: Basic illustrations, faster generation

## Architecture

The application is built on a sophisticated agentic framework:

- **OrchestratorAgent**: Coordinates the overall curriculum creation process
- **ContentAgent**: Generates the main lesson text
- **MediaAgent**: Creates educational illustrations
- **ChartAgent**: Produces data visualizations
- **QuizAgent**: Creates interactive assessment questions
- **SummaryAgent**: Provides concise lesson summaries
- **ResourceAgent**: Suggests additional learning resources

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI for the GPT and image generation models
- Streamlit for the powerful web app framework
- Contributors and testers who helped improve the application
