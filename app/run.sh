
# Venv
WIN_PATH='D:\Focus\_____Active_______\AI\venvs\rag_langchain_wsl\bin\activate'
LNX_PATH=$(wslpath "$WIN_PATH")
source "$LNX_PATH"

# install requirements 
# pip install -r requirements.txt

# run the app
uvicorn main:app --reload