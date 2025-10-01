# 🔧 Quick Command Reference

## Initial Setup

```bash
# Option 1: Use setup script (recommended)
./setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Running the Application

```bash
# 1. Activate virtual environment (if not already activated)
source venv/bin/activate

# 2. Run the Streamlit app
streamlit run app.py

# The app will open at http://localhost:8501
```

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install new packages
pip install package_name
pip freeze > requirements.txt

# Run tests
pytest tests/

# Code formatting
black excel_agent/ app.py

# Linting
flake8 excel_agent/ app.py

# Type checking
mypy excel_agent/

# Deactivate virtual environment
deactivate
```

## File Management

```bash
# Add Excel files to data directory
cp /path/to/your/file.xlsx data/

# View output
cat output/combined_results.csv
open output/combined_results.csv  # macOS
```

## Troubleshooting

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Streamlit cache
streamlit cache clear

# Check Python version
python3 --version

# Check installed packages
pip list
```

## Git Commands

```bash
# Check status
git status

# Add changes
git add .

# Commit changes
git commit -m "Your message"

# Push to remote
git push origin v0.1

# Create new branch
git checkout -b feature-name
```

## Environment Variables

Edit `.env` file:

```bash
# Open in default editor
open .env

# Or use vim/nano
vim .env
nano .env
```

Required variables:
- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `MODEL_NAME` - LLM model to use (default: gpt-4o-mini)
- `TEMPERATURE` - Model temperature (default: 0)

