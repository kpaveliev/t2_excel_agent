"""Streamlit Chat Interface for React Agent."""

import streamlit as st
from pathlib import Path
from excel_agent.config import OPENAI_API_KEY, DATA_DIR, OUTPUT_DIR, DEFAULT_THREAD_ID, logger
from excel_agent.react_agent import get_react_agent


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = DEFAULT_THREAD_ID
    if "processing_mode" not in st.session_state:
        st.session_state.processing_mode = "ask_when_unsure"
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None
    if "selected_files" not in st.session_state:
        st.session_state.selected_files = []
    if "branch_code" not in st.session_state:
        st.session_state.branch_code = ""
    if "contractor_name" not in st.session_state:
        st.session_state.contractor_name = ""


def display_chat_message(role: str, content: str):
    """Display a chat message."""
    avatar = "🤖" if role == "assistant" else "👤"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def main():
    st.set_page_config(
        page_title="Excel Agent Chat",
        page_icon="💬",
        layout="wide"
    )
    
    st.title("💬 Excel Agent Chat Interface")
    st.markdown("""
    Chat with an AI assistant that can help you process Excel files.
    
    **👈 Start by configuring files and metadata in the sidebar, then click "Start Processing"**
    """)
    
    # Check API key
    if not OPENAI_API_KEY:
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
        st.stop()
    
    # Initialize session state
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        st.markdown("---")
        
        # File Selection
        st.subheader("📁 File Selection")
        
        # Get available Excel files
        excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        
        if not excel_files:
            st.warning("⚠️ No Excel files found in data directory")
            st.info(f"Add files to: `{DATA_DIR}`")
        else:
            # Option to select files
            file_selection_mode = st.radio(
                "Select files to process:",
                options=["all", "specific"],
                format_func=lambda x: "All files" if x == "all" else "Select specific files",
                horizontal=True
            )
            
            if file_selection_mode == "specific":
                file_names = [f.name for f in excel_files]
                selected = st.multiselect(
                    "Choose files:",
                    options=file_names,
                    default=st.session_state.selected_files if st.session_state.selected_files else file_names[:1]
                )
                st.session_state.selected_files = selected
            else:
                st.session_state.selected_files = [f.name for f in excel_files]
            
            st.caption(f"Selected: {len(st.session_state.selected_files)} file(s)")
        
        st.markdown("---")
        
        # Metadata Input
        st.subheader("📋 Document Metadata")
        
        branch_code = st.text_input(
            "Код филиала:",
            value=st.session_state.branch_code,
            placeholder="Например: BRN001",
            help="Branch code for the documents"
        )
        st.session_state.branch_code = branch_code
        
        contractor_name = st.text_input(
            "Наименование подрядчика:",
            value=st.session_state.contractor_name,
            placeholder="Например: ООО «Подрядчик»",
            help="Contractor/counterparty name"
        )
        st.session_state.contractor_name = contractor_name
        
        st.markdown("---")
        
        # Processing Mode Selection
        st.subheader("🎛️ Processing Mode")
        mode = st.radio(
            "Select mode:",
            options=["fully_automatic", "ask_when_unsure", "manual_review"],
            format_func=lambda x: {
                "fully_automatic": "🚀 Fully Automatic",
                "ask_when_unsure": "🤔 Ask When Unsure",
                "manual_review": "👁️ Manual Review"
            }[x],
            index=1,  # Default to "ask_when_unsure"
            help="""
            **Fully Automatic**: Process everything automatically
            **Ask When Unsure**: Stop for review when confidence is not high
            **Manual Review**: Review each file before processing
            """
        )
        st.session_state.processing_mode = mode
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        
        # Start Processing button
        if st.button("▶️ Start Processing", use_container_width=True, type="primary"):
            # Validate inputs
            if not st.session_state.selected_files:
                st.error("⚠️ Please select at least one file")
            elif not st.session_state.branch_code:
                st.error("⚠️ Please enter Код филиала")
            elif not st.session_state.contractor_name:
                st.error("⚠️ Please enter Наименование подрядчика")
            else:
                # Add a special message to trigger processing
                mode_text = {
                    "fully_automatic": "fully automatic mode",
                    "ask_when_unsure": "careful mode (ask when unsure)",
                    "manual_review": "manual review mode"
                }[st.session_state.processing_mode]
                
                # Format file list
                if len(st.session_state.selected_files) == 1:
                    files_text = f"file '{st.session_state.selected_files[0]}'"
                elif len(st.session_state.selected_files) <= 3:
                    files_text = f"files: {', '.join(st.session_state.selected_files)}"
                else:
                    files_text = f"{len(st.session_state.selected_files)} files"
                
                prompt = f"""Start processing {files_text} in {mode_text}.

Metadata:
- Код филиала: {st.session_state.branch_code}
- Наименование подрядчика: {st.session_state.contractor_name}"""
                
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.session_state.pending_message = prompt  # Mark as pending for processing
                st.rerun()
        
        st.markdown("---")
        
        # Show current selection summary
        if st.session_state.selected_files and st.session_state.branch_code and st.session_state.contractor_name:
            with st.expander("📋 Current Configuration", expanded=False):
                st.write(f"**Files:** {len(st.session_state.selected_files)}")
                for f in st.session_state.selected_files[:5]:
                    st.text(f"  • {f}")
                if len(st.session_state.selected_files) > 5:
                    st.text(f"  ... and {len(st.session_state.selected_files) - 5} more")
                st.write(f"**Branch:** {st.session_state.branch_code}")
                st.write(f"**Contractor:** {st.session_state.contractor_name}")
        
        st.markdown("---")
        
        # Thread ID display
        st.info(f"**Thread ID:** `{st.session_state.thread_id}`")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            # Create new thread ID for fresh conversation
            import uuid
            st.session_state.thread_id = f"chat_{uuid.uuid4().hex[:8]}"
            st.rerun()
        
        st.markdown("---")
        
        # Example prompts
        st.subheader("💡 Tips")
        st.markdown("""
        **Getting Started:**
        1. Select files to process
        2. Enter branch code
        3. Enter contractor name
        4. Choose processing mode
        5. Click "▶️ Start Processing"
        
        **During Processing:**
        - Agent will extract data automatically
        - If unsure, agent will ask questions
        - Results saved to output/ directory
        """)
    
    # Initialize agent (lazy loading)
    if st.session_state.agent is None:
        with st.spinner("Initializing agent..."):
            try:
                st.session_state.agent = get_react_agent()
                logger.info("Agent initialized successfully")
            except Exception as e:
                st.error(f"Failed to initialize agent: {str(e)}")
                logger.error(f"Agent initialization error: {str(e)}")
                st.stop()
    
    # Display chat history
    for message in st.session_state.messages:
        display_chat_message(message["role"], message["content"])
    
    # Check if there's a pending message from button click
    if st.session_state.pending_message:
        prompt = st.session_state.pending_message
        st.session_state.pending_message = None  # Clear the pending message
        
        # Get agent response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    # Invoke the agent with thread_id for memory persistence
                    config = {"configurable": {"thread_id": st.session_state.thread_id}}
                    response = st.session_state.agent.invoke(
                        {"messages": [("user", prompt)]},
                        config=config
                    )
                    
                    # Extract the last message from the agent
                    agent_messages = response.get("messages", [])
                    if agent_messages:
                        last_message = agent_messages[-1]
                        
                        # Handle different message types
                        if hasattr(last_message, "content"):
                            assistant_response = last_message.content
                        else:
                            assistant_response = str(last_message)
                    else:
                        assistant_response = "I apologize, but I couldn't generate a response."
                    
                    st.markdown(assistant_response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Agent invocation error: {str(e)}", exc_info=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        
        # Force rerun to show the input field again
        st.rerun()
    
    # Chat input - always show it
    if prompt := st.chat_input("Ask me anything about your Excel files..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_chat_message("user", prompt)
        
        # Get agent response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    # Invoke the agent with thread_id for memory persistence
                    config = {"configurable": {"thread_id": st.session_state.thread_id}}
                    response = st.session_state.agent.invoke(
                        {"messages": [("user", prompt)]},
                        config=config
                    )
                    
                    # Extract the last message from the agent
                    agent_messages = response.get("messages", [])
                    if agent_messages:
                        last_message = agent_messages[-1]
                        
                        # Handle different message types
                        if hasattr(last_message, "content"):
                            assistant_response = last_message.content
                        else:
                            assistant_response = str(last_message)
                    else:
                        assistant_response = "I apologize, but I couldn't generate a response."
                    
                    st.markdown(assistant_response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Agent invocation error: {str(e)}", exc_info=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


if __name__ == "__main__":
    main()

