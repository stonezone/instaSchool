# InstaSchool Implementation TODO

This document provides step-by-step implementation instructions for the remediation and enhancement plan.

## 🔴 PART 1: CRITICAL BUG FIXES & ARCHITECTURAL REPAIRS

### Task 1.1: Fix wkhtmltopdf Dependency
**Priority: CRITICAL**

- [ ] 1.1.1 Update requirements.txt
  - Remove: `pdfkit>=1.0.0`
  - Add: `fpdf2>=2.7.0`
  - Add: `plotly>=5.15.0`
  - Add: `tenacity>=8.2.0`
  
- [ ] 1.1.2 Create services/export_service.py
  - Implement CurriculumPDF class extending FPDF
  - Add header() method for document header
  - Add chapter_title() method for section titles
  - Add chapter_body() method for content
  - Implement generate_pdf() function to export curriculum
  - Handle images in PDF (convert base64 to temp files)
  - Add error handling for PDF generation
  
- [ ] 1.1.3 Update main.py PDF export logic
  - Replace pdfkit calls with export_service.generate_pdf()
  - Update download button to use new PDF generator
  - Test PDF export with sample curriculum

### Task 1.2: Fix Streamlit Threading Violation
**Priority: CRITICAL**

- [ ] 1.2.1 Refactor BatchQueue to use file-based status
  - Create batch_status/ directory for status files
  - Modify BatchQueue.update_job_status() to write JSON files
  - Remove direct st.session_state writes from threads
  - Add get_batch_status() method to read from files
  
- [ ] 1.2.2 Update main.py batch UI
  - Replace thread-based progress with polling mechanism
  - Use st.empty() container for progress display
  - Add time.sleep() loop to poll batch_status files
  - Display progress from file data instead of thread updates
  
- [ ] 1.2.3 Add batch status cleanup
  - Auto-delete status files older than 24 hours
  - Add manual cleanup option in UI

### Task 1.3: Fix State Management Encapsulation
**Priority: HIGH**

- [ ] 1.3.1 Audit main.py for direct session_state access
  - Search for all `st.session_state['` patterns
  - List all direct accesses to plan refactoring
  
- [ ] 1.3.2 Replace direct access with StateManager
  - Replace `st.session_state['curriculum']` with `StateManager.get_state('curriculum')`
  - Replace `st.session_state['quiz_answers']` with `StateManager.get_state('quiz_answers')`
  - Replace all other direct accesses throughout main.py
  - Update StateManager to add get_state() and set_state() methods if missing
  
- [ ] 1.3.3 Add state validation
  - Add type hints to StateManager methods
  - Add validation for critical state keys
  - Add logging for state changes

### Task 1.4: Fix matplotlib Backend Trap
**Priority: HIGH**

- [ ] 1.4.1 Create src/__init__.py with matplotlib config
  - Add `import matplotlib` and `matplotlib.use('Agg')` as first lines
  - Ensure this runs before any other imports
  
- [ ] 1.4.2 Update main.py imports
  - Move matplotlib.use('Agg') call before main imports
  - Ensure order: os, sys, matplotlib setup, then other imports
  
- [ ] 1.4.3 Verify agent_framework.py doesn't pre-import matplotlib
  - Check for early pyplot imports
  - Ensure matplotlib only imported after backend is set

---

## 🟡 PART 2: LOGICAL ERRORS & CODE IMPROVEMENTS

### Task 2.1: Fix Image Generation Fallback Logic
**Priority: MEDIUM**

- [ ] 2.1.1 Update src/image_generator.py
  - Rename create_image() to generate_images()
  - Add 'count' parameter (default=1)
  - Handle single vs multiple image requests internally
  - Return consistent list format
  
- [ ] 2.1.2 Update src/agent_framework.py MediaAgent
  - Remove try/except AttributeError block
  - Call generate_images() directly
  - Simplify error handling
  
- [ ] 2.1.3 Test image generation
  - Test single image generation
  - Test multiple image generation
  - Verify error handling

### Task 2.2: Fix Regeneration Handler "Ghost" UI
**Priority: MEDIUM**

- [ ] 2.2.1 Update utils/regeneration_fix.py
  - Remove st.empty() and st.container() from callbacks
  - Callbacks should only update StateManager
  - Add 'just_regenerated_unit' flag to state
  - Set regeneration context (unit_id, type)
  
- [ ] 2.2.2 Update main.py to display regeneration success
  - Check for 'just_regenerated_unit' flag in main flow
  - Display st.success() message in main UI
  - Clear flag after displaying message
  
- [ ] 2.2.3 Test regeneration flow
  - Verify success message appears
  - Verify message persists after re-run

### Task 2.3: Fix Circular Dependency Risk
**Priority: MEDIUM**

- [ ] 2.3.1 Create src/core/types.py
  - Move BaseAgent class to types module
  - Move shared type definitions
  - Keep minimal dependencies
  
- [ ] 2.3.2 Update imports across project
  - Update agent_framework.py to import from types
  - Update services to import from types
  - Update tests to use new import paths
  
- [ ] 2.3.3 Verify no circular dependencies
  - Run tests to ensure imports work
  - Check for circular import errors

---

## 🟢 PART 3: ENHANCEMENTS (THE "FUN" FACTOR)

### Task 3.1: Interactive Student Mode (Gamification)
**Priority: HIGH**

- [ ] 3.1.1 Add mode selection to main.py sidebar
  - Add radio button: "Teacher (Editor)" vs "Student (Learn)"
  - Store selection in StateManager
  - Add session state for student progress
  
- [ ] 3.1.2 Create src/student_view.py
  - Implement show_student_view() function
  - Hide Edit/Regenerate/Settings buttons
  - Create card-based UI for content presentation
  - Add navigation: Previous/Next buttons
  
- [ ] 3.1.3 Implement XP System
  - Track completed sections in state
  - Award XP for reading (10 pts) and quiz completion (50 pts)
  - Display progress bar with level/XP
  - Calculate level from total XP (level = XP // 100)
  
- [ ] 3.1.4 Add quiz celebration
  - Check quiz score when submitted
  - If 100%, trigger st.balloons()
  - Display achievement message
  - Award bonus XP
  
- [ ] 3.1.5 Add student progress persistence
  - Save progress to JSON file
  - Load progress on student mode entry
  - Track per-curriculum progress

### Task 3.2: Audio/TTS Integration
**Priority: MEDIUM**

- [ ] 3.2.1 Add AudioAgent to src/agent_framework.py
  - Create AudioAgent class
  - Implement generate_audio() method using OpenAI TTS
  - Use tts-1 model with configurable voice
  - Handle 4096 character limit (chunk if needed)
  
- [ ] 3.2.2 Update services/curriculum_service.py
  - Add generate_audio_for_unit() method
  - Cache audio files in audio/ directory
  - Return file path for st.audio()
  
- [ ] 3.2.3 Update UI to display audio player
  - Add audio player above each unit content
  - Add "Generate Audio" button for teacher mode
  - Auto-play option in student mode
  - Voice selection dropdown (alloy, echo, fable, onyx, nova, shimmer)
  
- [ ] 3.2.4 Update config.yaml
  - Add TTS settings section
  - Add default voice selection
  - Add audio generation toggle

### Task 3.3: Interactive Charts with Plotly
**Priority: MEDIUM**

- [ ] 3.3.1 Update src/agent_framework.py ChartAgent
  - Change output from matplotlib to Plotly JSON
  - Update prompt to generate Plotly configs
  - Return plotly.graph_objects dict
  
- [ ] 3.3.2 Update main.py chart display
  - Replace plt.figure() with st.plotly_chart()
  - Parse JSON config from ChartAgent
  - Add interactivity (hover, zoom, pan)
  
- [ ] 3.3.3 Keep matplotlib as fallback
  - Catch plotly errors
  - Fall back to matplotlib if plotly fails
  - Log which system was used

### Task 3.4: Socratic Tutor Chatbot
**Priority: MEDIUM**

- [ ] 3.4.1 Create src/tutor_chatbot.py
  - Implement TutorAgent class
  - Use current unit content as context
  - Limit responses to lesson material only
  - Add conversation memory (last 5 messages)
  
- [ ] 3.4.2 Add chat interface to student view
  - Use st.chat_message() for display
  - Add chat input at bottom of student view
  - Display tutor responses with avatar
  - Store chat history in session state
  
- [ ] 3.4.3 Add context management
  - Update tutor context when unit changes
  - Clear chat history on curriculum change
  - Add "Clear Chat" button
  
- [ ] 3.4.4 Add helpful prompts
  - Show example questions student can ask
  - "Explain this concept differently"
  - "Give me another example"
  - "I don't understand [specific part]"

---

## 🔧 PART 4: SUPPORTING UPDATES

### Task 4.1: Update config.yaml
**Priority: HIGH**

- [ ] 4.1.1 Add new teaching styles
  - Add "Socratic (Question based)"
  - Add "Storyteller (Narrative)"
  - Add "Comedian (Fun/Engaging)"
  - Add "5-Year-Old (ELI5)"
  
- [ ] 4.1.2 Add TTS configuration
  - Add tts_enabled: true/false
  - Add default_voice: "alloy"
  - Add available_voices list
  
- [ ] 4.1.3 Add student mode configuration
  - Add xp_per_section: 10
  - Add xp_per_quiz: 50
  - Add xp_per_level: 100
  
- [ ] 4.1.4 Update model defaults
  - Ensure gpt-4.1 is primary model
  - Set gpt-4.1-mini for worker agents
  - Set gpt-4.1-nano for development/testing

### Task 4.2: Update requirements.txt
**Priority: CRITICAL**

- [ ] 4.2.1 Replace requirements.txt content
  ```
  streamlit>=1.24.0
  openai>=1.0.0
  pyyaml>=6.0
  matplotlib>=3.5.0
  pillow>=9.0.0
  python-dotenv>=0.19.0
  fpdf2>=2.7.0
  plotly>=5.15.0
  tenacity>=8.2.0
  httpx>=0.23.0
  markdown>=3.4.0
  ```

### Task 4.3: Documentation Updates
**Priority: LOW**

- [ ] 4.3.1 Update README.md
  - Document Student Mode feature
  - Document TTS integration
  - Update installation instructions (remove wkhtmltopdf)
  - Add new dependencies
  
- [ ] 4.3.2 Update CLAUDE.md
  - Add student mode patterns
  - Update architecture section
  - Document new agents (AudioAgent, TutorAgent)
  
- [ ] 4.3.3 Create ARCHITECTURE.md
  - Document agent framework
  - Document state management
  - Document service layer
  - Add diagrams if helpful

---

## ✅ PART 5: TESTING & VALIDATION

### Task 5.1: Create Test Suite for New Features
**Priority: HIGH**

- [ ] 5.1.1 Create tests/test_export_service.py
  - Test PDF generation
  - Test PDF with images
  - Test error handling
  
- [ ] 5.1.2 Create tests/test_student_mode.py
  - Test XP calculation
  - Test progress tracking
  - Test state persistence
  
- [ ] 5.1.3 Create tests/test_audio_agent.py
  - Test TTS generation
  - Test audio caching
  - Test chunking for long text
  
- [ ] 5.1.4 Create tests/test_tutor_chatbot.py
  - Test context management
  - Test response generation
  - Test conversation history

### Task 5.2: Integration Testing
**Priority: HIGH**

- [ ] 5.2.1 Test complete curriculum generation flow
  - Generate sample curriculum
  - Verify all agents work
  - Check PDF export
  - Validate audio generation
  
- [ ] 5.2.2 Test student mode flow
  - Navigate through curriculum
  - Complete quizzes
  - Check XP accumulation
  - Verify progress persistence
  
- [ ] 5.2.3 Test batch processing
  - Create batch job
  - Monitor status via polling
  - Verify completion
  - Check for race conditions

### Task 5.3: Manual QA Checklist
**Priority: HIGH**

- [ ] 5.3.1 Teacher Mode Testing
  - [ ] Create new curriculum
  - [ ] Edit existing curriculum
  - [ ] Regenerate units
  - [ ] Export to PDF (fpdf2)
  - [ ] Export to HTML
  - [ ] Generate audio for units
  - [ ] View interactive charts
  
- [ ] 5.3.2 Student Mode Testing
  - [ ] Switch to student mode
  - [ ] Navigate through lessons
  - [ ] Complete quizzes
  - [ ] Earn XP and level up
  - [ ] See celebration on perfect quiz
  - [ ] Use tutor chatbot
  - [ ] Listen to audio lessons
  
- [ ] 5.3.3 Performance Testing
  - [ ] Test with large curriculum (10+ units)
  - [ ] Monitor memory usage
  - [ ] Check audio file sizes
  - [ ] Verify caching works
  
- [ ] 5.3.4 Error Handling Testing
  - [ ] Test with invalid API key
  - [ ] Test with API rate limits
  - [ ] Test with network errors
  - [ ] Verify graceful degradation

---

## 🚀 IMPLEMENTATION ORDER (RECOMMENDED)

**Phase 1: Critical Fixes (Week 1)**
1. Task 4.2 - Update requirements.txt
2. Task 1.1 - Fix PDF dependency
3. Task 1.4 - Fix matplotlib backend
4. Task 1.3 - Fix state management
5. Task 2.1 - Fix image generation

**Phase 2: Architecture Repairs (Week 1-2)**
6. Task 1.2 - Fix threading violations
7. Task 2.2 - Fix regeneration UI
8. Task 2.3 - Fix circular dependencies

**Phase 3: Core Enhancements (Week 2-3)**
9. Task 4.1 - Update config.yaml
10. Task 3.1 - Student mode (basic)
11. Task 3.3 - Plotly charts

**Phase 4: Advanced Features (Week 3-4)**
12. Task 3.2 - TTS/Audio integration
13. Task 3.4 - Tutor chatbot
14. Task 3.1.3-3.1.5 - XP system and gamification

**Phase 5: Testing & Polish (Week 4)**
15. Task 5.1 - Unit tests
16. Task 5.2 - Integration tests
17. Task 5.3 - Manual QA
18. Task 4.3 - Documentation

---

## 📝 NOTES & CONSIDERATIONS

### Development Environment
- Use gpt-4.1-nano during development/testing
- Switch to gpt-4.1 for production testing
- Always test with API key in .env file

### API Costs
- TTS costs: ~$15 per 1M characters
- Image generation: Variable by model
- Text generation: Monitor token usage
- Consider adding cost warnings in UI

### Deployment Considerations
- Test on Streamlit Cloud before deploying
- Ensure all dependencies are pure Python
- Verify no OS-level dependencies remain
- Test on clean environment

### Student Privacy
- Don't store PII in progress files
- Use anonymous IDs for student tracking
- Add data export feature for students
- Consider COPPA/FERPA compliance

---

## 🎯 SUCCESS CRITERIA

The implementation is complete when:

1. ✅ PDF export works on any machine without binary dependencies
2. ✅ No threading violations or race conditions in batch processing
3. ✅ All state access goes through StateManager
4. ✅ Student mode provides engaging, gamified learning experience
5. ✅ Audio lessons available for accessibility
6. ✅ Interactive Plotly charts enhance data visualization
7. ✅ Tutor chatbot provides contextual help
8. ✅ All tests pass
9. ✅ Documentation is complete and accurate
10. ✅ Application deploys successfully to Streamlit Cloud

---

## 🔄 ROLLBACK PLAN

If critical issues arise:

1. Create backup branch before starting: `git checkout -b backup-pre-remediation`
2. Work on feature branch: `git checkout -b remediation-implementation`
3. Keep commits atomic and well-documented
4. If rollback needed: `git checkout main && git reset --hard backup-pre-remediation`

---

## 📞 SUPPORT RESOURCES

- Streamlit Docs: https://docs.streamlit.io
- OpenAI API Docs: https://platform.openai.com/docs
- FPDF2 Docs: https://pyfpdf.github.io/fpdf2/
- Plotly Docs: https://plotly.com/python/

---

**Last Updated:** 2025-11-23
**Version:** 1.0
**Status:** Ready for Implementation
