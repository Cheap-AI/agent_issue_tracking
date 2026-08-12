Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
pip install -r backend/requirements.txt

cd frontend && npm install && cd ..