# Full Retreival Augmented Generaion (RAG) App
A minimal implementation of a RAG pipeline for Question Answering (QA)

## Setup the Environment
1. Installing Python 3.10 or later.

2. Creating a venv environment for the porject using `python venv -m venv_name`.

3. Activating the venv
    - For linux-based systems `source venv_dir/bin/activate`
    - For windows `venv_dir\Scripts\activate` 

4. Installing requirements: `pip install -r requirements.txt`

5. Copying the .env.example into .env file: `cp .env.example .env`

6. Putting the required API Sectet keys into .env

7. Run the app from the run.sh file:
    - Making the file executable on Windows: `chmod +x run.sh`
    - Run the file: `./run.sh`