# Batch UI Implementation for main.py
# This code should be added to main.py

"""
BATCH GENERATION UI WITH POLLING MECHANISM

Location: Add as a new tab (tab5) or within tab4 (Templates)

Key Implementation Details:
1. Initialize BatchManager in session state
2. Create UI for batch creation
3. Use polling loop with st.empty() for progress display
4. Read status from files via get_batch_status()
5. Display progress without writing to session_state from threads
"""

# ==================== INITIALIZATION (Add after template_manager init) ====================
# Initialize batch manager
if "batch_manager" not in st.session_state:
    try:
        from services.batch_service import BatchManager
        st.session_state.batch_manager = BatchManager(max_concurrent=2)
    except ImportError:
        sys.stderr.write("Warning: batch_service not available\n")
        st.session_state.batch_manager = None
    except Exception as e:
        st.error(f"Failed to initialize batch manager: {e}")
        st.session_state.batch_manager = None

# Initialize batch state
if "active_batch_id" not in st.session_state:
    st.session_state.active_batch_id = None
if "batch_polling" not in st.session_state:
    st.session_state.batch_polling = False


# ==================== ADD NEW TAB (Modify tab creation line 721) ====================
# REPLACE:
# tab1, tab2, tab3, tab4 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates"])

# WITH:
# tab1, tab2, tab3, tab4, tab5 = st.tabs(["✨ Generate", "✏️ View & Edit", "📤 Export", "📋 Templates", "🔄 Batch"])


# ==================== BATCH TAB IMPLEMENTATION ====================
with tab5:
    st.markdown("### Batch Curriculum Generation")

    if not st.session_state.batch_manager:
        st.error("Batch generation service is not available. Please check the installation.")
    else:
        # Sub-tabs for different batch operations
        batch_tab1, batch_tab2, batch_tab3 = st.tabs(["➕ Create Batch", "📊 Active Batches", "📜 History"])

        with batch_tab1:
            st.markdown("#### Create New Batch")
            st.markdown("Generate multiple curricula in one batch operation.")

            # Batch creation method selection
            creation_method = st.radio(
                "Creation Method",
                ["From Template", "Custom Combinations"],
                help="Choose how to create your batch jobs"
            )

            if creation_method == "From Template":
                if not st.session_state.template_manager:
                    st.warning("Template manager not available.")
                else:
                    # Template selection
                    templates = st.session_state.template_manager.list_templates()

                    if templates:
                        template_options = {t.name: t.id for t in templates}
                        selected_template_name = st.selectbox(
                            "Select Template",
                            options=list(template_options.keys())
                        )
                        selected_template_id = template_options[selected_template_name]

                        # Subject and grade selection
                        st.markdown("**Select Subjects and Grades**")
                        col1, col2 = st.columns(2)

                        with col1:
                            batch_subjects = st.multiselect(
                                "Subjects",
                                config["defaults"]["subjects"],
                                default=[config["defaults"]["subject"]]
                            )

                        with col2:
                            batch_grades = st.multiselect(
                                "Grades",
                                config["defaults"]["grades"],
                                default=[config["defaults"]["grade"]]
                            )

                        # Show job count
                        total_jobs = len(batch_subjects) * len(batch_grades)
                        st.info(f"This will create **{total_jobs}** curriculum generation jobs.")

                        # Batch name and description
                        batch_name = st.text_input(
                            "Batch Name",
                            value=f"Batch: {selected_template_name}",
                            help="Give your batch a meaningful name"
                        )

                        batch_description = st.text_area(
                            "Description (Optional)",
                            help="Describe this batch generation"
                        )

                        # Cost estimation
                        if total_jobs > 0 and st.session_state.curriculum_service:
                            with st.expander("💰 Cost Estimation", expanded=False):
                                # Estimate cost for one job
                                estimation_params = {
                                    "media_richness": media_richness,
                                    "include_quizzes": include_quizzes,
                                    "include_summary": include_summary,
                                    "include_resources": include_resources,
                                    "image_model": image_model,
                                    "text_model": text_model
                                }
                                single_cost = st.session_state.curriculum_service.estimate_costs(estimation_params)
                                total_cost = single_cost['total_cost'] * total_jobs

                                st.metric("Total Estimated Cost", f"${total_cost:.2f}")
                                st.caption(f"${single_cost['total_cost']:.2f} per curriculum × {total_jobs} jobs")

                        # Create batch button
                        if st.button("🚀 Create Batch", type="primary", disabled=total_jobs == 0):
                            try:
                                # Create batch
                                batch_id = st.session_state.batch_manager.create_batch_from_template(
                                    template_id=selected_template_id,
                                    subjects=batch_subjects,
                                    grades=batch_grades,
                                    template_manager=st.session_state.template_manager,
                                    name=batch_name,
                                    description=batch_description
                                )

                                # Define generator function
                                def generator_func(params):
                                    """Generator function for batch jobs"""
                                    if st.session_state.curriculum_service:
                                        return st.session_state.curriculum_service.generate_curriculum(params)
                                    else:
                                        # Fallback to orchestrator
                                        return orchestrator.create_curriculum(
                                            params.get("subject_str"),
                                            params.get("grade"),
                                            params.get("lesson_style"),
                                            params.get("language"),
                                            params.get("custom_prompt", ""),
                                            config
                                        )

                                # Start batch processing
                                success = st.session_state.batch_manager.start_batch(batch_id, generator_func)

                                if success:
                                    st.success(f"Batch '{batch_name}' created and started!")
                                    st.session_state.active_batch_id = batch_id
                                    st.session_state.batch_polling = True
                                    st.rerun()
                                else:
                                    st.error("Failed to start batch processing")

                            except Exception as e:
                                st.error(f"Error creating batch: {e}")
                                sys.stderr.write(f"Batch creation error: {e}\n")
                                sys.stderr.write(traceback.format_exc() + "\n")

                    else:
                        st.info("No templates available. Create templates in the Templates tab first.")

            else:  # Custom Combinations
                st.markdown("**Custom Batch Configuration**")
                st.info("Custom batch creation will be available in a future update.")

        with batch_tab2:
            st.markdown("#### Active Batches")

            # Get active batches
            active_batches = st.session_state.batch_manager.list_batches()
            running_batches = [b for b in active_batches if b.status.value in ["pending", "running"]]

            if not running_batches:
                st.info("No active batches. Create a new batch to get started.")
            else:
                for batch in running_batches:
                    with st.expander(f"📦 {batch.name}", expanded=True):
                        # Batch metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Jobs", batch.total_jobs)
                        with col2:
                            st.metric("Completed", batch.completed_jobs)
                        with col3:
                            st.metric("Failed", batch.failed_jobs)

                        # Progress bar
                        progress = batch.completed_jobs / batch.total_jobs if batch.total_jobs > 0 else 0
                        st.progress(progress, text=f"Progress: {int(progress*100)}%")

                        # Polling mechanism for this batch
                        if st.session_state.active_batch_id == batch.id and st.session_state.batch_polling:
                            # Create polling loop
                            progress_container = st.empty()
                            stop_polling = False

                            # Polling interval
                            poll_interval = 1.5  # seconds

                            # Poll for updates
                            while st.session_state.batch_polling and not stop_polling:
                                # Read status from file (safe for UI thread)
                                updated_batch = st.session_state.batch_manager.get_batch_status(batch.id)

                                if updated_batch:
                                    with progress_container.container():
                                        # Display job statuses
                                        st.markdown("**Job Status:**")
                                        for i, job in enumerate(updated_batch.jobs):
                                            status_icon = {
                                                "pending": "⏳",
                                                "running": "🔄",
                                                "completed": "✅",
                                                "failed": "❌",
                                                "cancelled": "🚫"
                                            }.get(job.status.value, "❓")

                                            st.markdown(f"{status_icon} **{job.name}** - {job.status.value}")
                                            if job.progress > 0:
                                                st.progress(job.progress)

                                    # Check if batch is complete
                                    if updated_batch.status.value in ["completed", "failed", "cancelled"]:
                                        st.session_state.batch_polling = False
                                        stop_polling = True
                                        st.success(f"Batch {updated_batch.status.value}!")
                                        st.rerun()

                                # Wait before next poll
                                if not stop_polling:
                                    time.sleep(poll_interval)

                            # Stop polling button
                            if st.button("⏸️ Stop Monitoring", key=f"stop_{batch.id}"):
                                st.session_state.batch_polling = False
                                st.rerun()

                        else:
                            # Show job details without polling
                            st.markdown("**Jobs:**")
                            for job in batch.jobs:
                                status_icon = {
                                    "pending": "⏳",
                                    "running": "🔄",
                                    "completed": "✅",
                                    "failed": "❌",
                                    "cancelled": "🚫"
                                }.get(job.status.value, "❓")
                                st.markdown(f"{status_icon} {job.name} - {job.status.value}")

                            # Monitor button
                            if st.button("👁️ Monitor Progress", key=f"monitor_{batch.id}"):
                                st.session_state.active_batch_id = batch.id
                                st.session_state.batch_polling = True
                                st.rerun()

                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🗑️ Cancel Batch", key=f"cancel_{batch.id}"):
                                if st.session_state.batch_manager.cancel_batch(batch.id):
                                    st.success("Batch cancelled")
                                    st.session_state.batch_polling = False
                                    st.rerun()

                        with col2:
                            if batch.status.value == "completed":
                                if st.button("📥 Download Results", key=f"download_{batch.id}"):
                                    st.info("Download functionality coming soon!")

        with batch_tab3:
            st.markdown("#### Batch History")

            # Get completed/failed batches
            all_batches = st.session_state.batch_manager.list_batches()
            completed_batches = [b for b in all_batches if b.status.value in ["completed", "failed", "cancelled"]]

            if not completed_batches:
                st.info("No completed batches yet.")
            else:
                for batch in completed_batches:
                    with st.expander(f"📦 {batch.name} - {batch.status.value}"):
                        st.markdown(f"**Description:** {batch.description}")
                        st.markdown(f"**Created:** {batch.created_at}")
                        st.markdown(f"**Completed:** {batch.completed_at}")

                        # Stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Jobs", batch.total_jobs)
                        with col2:
                            st.metric("Completed", batch.completed_jobs)
                        with col3:
                            st.metric("Failed", batch.failed_jobs)

                        # View results
                        if batch.status.value == "completed":
                            if st.button("📄 View Results", key=f"view_{batch.id}"):
                                results = st.session_state.batch_manager.get_batch_results(batch.id)
                                st.json(results)

                        # Delete batch
                        if st.button("🗑️ Delete Batch", key=f"delete_{batch.id}"):
                            if st.session_state.batch_manager.delete_batch(batch.id):
                                st.success("Batch deleted")
                                st.rerun()


# ==================== KEY POINTS ====================
"""
1. NO thread-based st.session_state updates
2. Polling uses get_batch_status() which reads from files
3. Progress display uses st.empty() containers
4. Poll interval is 1.5 seconds
5. Stop button cancels polling loop
6. All status updates come from file system, not threads
7. Use st.rerun() to refresh UI after state changes
"""
