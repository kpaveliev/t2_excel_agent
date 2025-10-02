"""Quick verification script for the chat interface setup."""

import sys
from pathlib import Path

def verify_setup():
    """Verify that the chat interface is properly set up."""
    print("🔍 Verifying Chat Interface Setup...\n")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Files exist
    checks_total += 1
    print("✓ Check 1: Required files")
    files_to_check = [
        "excel_agent/react_agent.py",
        "chat_app.py",
        "CHAT_INTERFACE_README.md"
    ]
    
    all_files_exist = True
    for file in files_to_check:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            all_files_exist = False
    
    if all_files_exist:
        checks_passed += 1
        print("  ✓ All required files exist\n")
    else:
        print("  ✗ Some files are missing\n")
    
    # Check 2: Import modules
    checks_total += 1
    print("✓ Check 2: Module imports")
    try:
        from excel_agent.config import OPENAI_API_KEY
        print("  ✓ Config module")
        checks_passed += 1
    except Exception as e:
        print(f"  ✗ Error importing config: {e}\n")
        return
    
    # Check 3: API Key
    checks_total += 1
    print("✓ Check 3: OpenAI API Key")
    if OPENAI_API_KEY:
        print(f"  ✓ API key is set (length: {len(OPENAI_API_KEY)})")
        checks_passed += 1
    else:
        print("  ✗ API key is not set. Please add OPENAI_API_KEY to .env file")
    print()
    
    # Check 4: React agent can be imported
    checks_total += 1
    print("✓ Check 4: React Agent module")
    try:
        from excel_agent import react_agent
        print("  ✓ react_agent module imported")
        checks_passed += 1
    except Exception as e:
        print(f"  ✗ Error importing react_agent: {e}")
    print()
    
    # Check 5: Tools are defined
    checks_total += 1
    print("✓ Check 5: Agent tools")
    try:
        from excel_agent.react_agent import (
            list_excel_files,
            get_excel_sheets,
            get_sheet_columns,
            preview_sheet_data,
            find_columns_with_llm,
            extract_data
        )
        tools_list = [
            "list_excel_files",
            "get_excel_sheets", 
            "get_sheet_columns",
            "preview_sheet_data",
            "find_columns_with_llm",
            "extract_data"
        ]
        for tool_name in tools_list:
            print(f"  ✓ {tool_name}")
        checks_passed += 1
    except Exception as e:
        print(f"  ✗ Error importing tools: {e}")
    print()
    
    # Check 6: Agent creation (only if API key is set)
    if OPENAI_API_KEY:
        checks_total += 1
        print("✓ Check 6: Agent creation")
        try:
            from excel_agent.react_agent import create_excel_react_agent
            agent = create_excel_react_agent()
            print("  ✓ React agent created successfully")
            print(f"  ✓ Agent type: {type(agent).__name__}")
            checks_passed += 1
        except Exception as e:
            print(f"  ✗ Error creating agent: {e}")
        print()
    
    # Summary
    print("=" * 50)
    print(f"📊 Summary: {checks_passed}/{checks_total} checks passed")
    
    if checks_passed == checks_total:
        print("✅ All checks passed! The chat interface is ready to use.")
        print("\nTo start the chat interface, run:")
        print("  streamlit run chat_app.py")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(verify_setup())

