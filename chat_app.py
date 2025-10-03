"""Streamlit Chat Interface for React Agent."""

import streamlit as st
import uuid
from datetime import datetime, date
from excel_agent.config import OPENAI_API_KEY, DATA_DIR, DEFAULT_THREAD_ID, logger
from excel_agent.react_agent import get_react_agent


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = DEFAULT_THREAD_ID
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "branch_code" not in st.session_state:
        st.session_state.branch_code = ""
    if "contractor_name" not in st.session_state:
        st.session_state.contractor_name = ""
    if "period" not in st.session_state:
        st.session_state.period = None


def display_chat_message(role: str, content: str):
    """Display a chat message."""
    avatar = "🤖" if role == "assistant" else "👤"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def main():
    st.set_page_config(
        page_title="Чат с Excel агентом",
        page_icon="💬",
        layout="wide"
    )
    
    st.title("💬 Чат с Excel агентом")
    st.markdown("""
    Общайтесь с AI-ассистентом, который поможет обработать ваши Excel файлы.
    
    **👈 Настройте файлы и метаданные на боковой панели, затем нажмите "Начать обработку"**
    """)
    
    # Check API key
    if not OPENAI_API_KEY:
        st.error("⚠️ OpenAI API ключ не найден. Пожалуйста, установите OPENAI_API_KEY в файле .env")
        st.stop()
    
    # Initialize session state
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        # File Upload
        st.subheader("📁 Загрузка файлов")
        
        uploaded_files = st.file_uploader(
            "Выберите Excel файлы:",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            help="Загрузите один или несколько Excel файлов для обработки"
        )
        
        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            st.caption(f"Загружено: {len(uploaded_files)} файл(ов)")
            for f in uploaded_files:
                st.text(f"  • {f.name}")
        elif st.session_state.uploaded_files:
            st.caption(f"Загружено: {len(st.session_state.uploaded_files)} файл(ов)")
        
        st.markdown("---")
        
        # Metadata Input
        st.subheader("📋 Метаданные документов")
        
        # Period selection (month and year)
        col1, col2 = st.columns(2)
        with col1:
            months = {
                "Январь": 1, "Февраль": 2, "Март": 3, "Апрель": 4,
                "Май": 5, "Июнь": 6, "Июль": 7, "Август": 8,
                "Сентябрь": 9, "Октябрь": 10, "Ноябрь": 11, "Декабрь": 12
            }
            selected_month_name = st.selectbox(
                "Месяц:",
                options=list(months.keys()),
                index=datetime.now().month - 1 if st.session_state.period is None else list(months.values()).index(st.session_state.period.month) if hasattr(st.session_state.period, 'month') else datetime.now().month - 1
            )
            selected_month = months[selected_month_name]
        
        with col2:
            current_year = datetime.now().year
            years = list(range(current_year - 5, current_year + 2))
            selected_year = st.selectbox(
                "Год:",
                options=years,
                index=years.index(current_year) if st.session_state.period is None else years.index(st.session_state.period.year) if hasattr(st.session_state.period, 'year') and st.session_state.period.year in years else years.index(current_year)
            )
        
        # Store as date object (first day of the month)
        period = date(selected_year, selected_month, 1)
        st.session_state.period = period
        
        branch_code = st.text_input(
            "Код филиала:",
            value=st.session_state.branch_code,
            placeholder="Например: BRN001",
            help="Код филиала для документов"
        )
        st.session_state.branch_code = branch_code
        
        contractor_name = st.text_input(
            "Наименование подрядчика:",
            value=st.session_state.contractor_name,
            placeholder="Например: ООО «Подрядчик»",
            help="Наименование контрагента/подрядчика"
        )
        st.session_state.contractor_name = contractor_name
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("🚀 Быстрые действия")
        
        # Start Processing button
        if st.button("▶️ Начать обработку", use_container_width=True, type="primary"):
            # Validate inputs
            if not st.session_state.uploaded_files:
                st.error("⚠️ Пожалуйста, загрузите хотя бы один файл")
            elif not st.session_state.period:
                st.error("⚠️ Пожалуйста, укажите отчетный период")
            elif not st.session_state.branch_code:
                st.error("⚠️ Пожалуйста, укажите код филиала")
            elif not st.session_state.contractor_name:
                st.error("⚠️ Пожалуйста, укажите наименование подрядчика")
            else:
                # Save uploaded files to data directory
                saved_files = []
                for uploaded_file in st.session_state.uploaded_files:
                    file_path = DATA_DIR / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    saved_files.append(uploaded_file.name)
                
                # Format file list
                if len(saved_files) == 1:
                    files_text = f"файл '{saved_files[0]}'"
                elif len(saved_files) <= 3:
                    files_text = f"файлы: {', '.join(saved_files)}"
                else:
                    files_text = f"{len(saved_files)} файлов"
                
                # Format period as "Месяц YYYY"
                months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
                period_str = f"{months_ru[st.session_state.period.month - 1]} {st.session_state.period.year}"
                
                prompt = f"""Начни обработку {files_text}.

Метаданные:
- Отчетный период: {period_str}
- Код филиала: {st.session_state.branch_code}
- Наименование подрядчика: {st.session_state.contractor_name}"""
                
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.session_state.pending_message = prompt  # Mark as pending for processing
                st.rerun()
        
        st.markdown("---")
        
        # Show current selection summary
        if st.session_state.uploaded_files and st.session_state.period and st.session_state.branch_code and st.session_state.contractor_name:
            with st.expander("📋 Текущая конфигурация", expanded=False):
                st.write(f"**Файлов:** {len(st.session_state.uploaded_files)}")
                for f in st.session_state.uploaded_files[:5]:
                    st.text(f"  • {f.name}")
                if len(st.session_state.uploaded_files) > 5:
                    st.text(f"  ... ещё {len(st.session_state.uploaded_files) - 5}")
                # Format period
                months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
                period_str = f"{months_ru[st.session_state.period.month - 1]} {st.session_state.period.year}"
                st.write(f"**Период:** {period_str}")
                st.write(f"**Филиал:** {st.session_state.branch_code}")
                st.write(f"**Подрядчик:** {st.session_state.contractor_name}")
        
        st.markdown("---")
        
        # Thread ID display
        st.info(f"**Thread ID:** `{st.session_state.thread_id}`")
        
        # Clear chat button
        if st.button("🗑️ Очистить чат", use_container_width=True):
            st.session_state.messages = []
            # Create new thread ID for fresh conversation
            st.session_state.thread_id = f"chat_{uuid.uuid4().hex[:8]}"
            st.rerun()
        
        st.markdown("---")
        
        # Example prompts
        st.subheader("💡 Подсказки")
        st.markdown("""
        **Начало работы:**
        1. Загрузите Excel файлы
        2. Укажите отчетный период
        3. Укажите код филиала
        4. Укажите наименование подрядчика
        5. Нажмите "▶️ Начать обработку"
        
        **Во время обработки:**
        - Агент автоматически извлечёт данные
        - При неуверенности агент задаст вопросы
        - Результаты сохраняются в папку output/
        """)
    
    # Initialize agent (lazy loading)
    if st.session_state.agent is None:
        with st.spinner("Инициализация агента..."):
            try:
                st.session_state.agent = get_react_agent()
                logger.info("Agent initialized successfully")
            except Exception as e:
                st.error(f"Ошибка инициализации агента: {str(e)}")
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
            with st.spinner("Думаю..."):
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
                        assistant_response = "Извините, не удалось сгенерировать ответ."
                    
                    st.markdown(assistant_response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                except Exception as e:
                    error_msg = f"Ошибка: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Agent invocation error: {str(e)}", exc_info=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        
        # Force rerun to show the input field again
        st.rerun()
    
    # Chat input - always show it
    if prompt := st.chat_input("Задайте любой вопрос о ваших Excel файлах..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_chat_message("user", prompt)
        
        # Get agent response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Думаю..."):
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
                        assistant_response = "Извините, не удалось сгенерировать ответ."
                    
                    st.markdown(assistant_response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                except Exception as e:
                    error_msg = f"Ошибка: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Agent invocation error: {str(e)}", exc_info=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


if __name__ == "__main__":
    main()

