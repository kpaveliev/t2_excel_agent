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
    Chat with an AI assistant that can help you process Excel files. The agent can:
    - 📋 List and explore Excel files
    - 🔍 Identify relevant columns using AI
    - 📊 Extract and save data
    - 💡 Provide insights and guidance
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
        st.info(f"**Data directory:** `{DATA_DIR}`")
        st.info(f"**Output directory:** `{OUTPUT_DIR}`")
        
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
            # Add a special message to trigger processing
            mode_text = {
                "fully_automatic": "fully automatic mode",
                "ask_when_unsure": "careful mode (ask when unsure)",
                "manual_review": "manual review mode"
            }[st.session_state.processing_mode]
            
            prompt = f"Start processing all Excel files in {mode_text}"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.pending_message = prompt  # Mark as pending for processing
            st.rerun()
        
        if st.button("📁 List Files", use_container_width=True):
            excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
            if excel_files:
                files_text = "\n".join([f"- {f.name}" for f in excel_files])
                st.code(files_text)
            else:
                st.warning("No Excel files found")
        
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
        st.subheader("💡 Example Prompts")
        st.markdown("""
        **Quick Actions:**
        - *"List all Excel files"*
        - *"Process all files"*
        - *"Process report.xlsx"*
        
        **With Caution:**
        - *"Process files but ask me when unsure"*
        - *"Process in manual review mode"*
        - *"Show me what you found and wait for confirmation"*
        
        **Information:**
        - *"What files did you process?"*
        - *"Show me the last processing results"*
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

