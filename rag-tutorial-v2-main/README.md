# rag-tutorial-v2

This project is a small local RAG application built with:

- Chroma for vector storage
- Ollama for embeddings and answer generation
- PDF files in `data/` as the source documents

Right now the code uses:

- `nomic-embed-text` for embeddings
- `mistral` for final answers

## What the project does

1. `populate_database.py` reads every PDF in `data/`
2. It splits the text into chunks and stores embeddings in the local `chroma/` folder
3. `query_data.py` retrieves the most relevant chunks
4. Ollama generates a final answer using those chunks as context

## Requirements

- Python 3.10+
- Ollama installed locally

## Install Python dependencies

From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks the virtual environment activation, run this once in the same terminal and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Install Ollama

### Windows

Option A, install from PowerShell:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Option B, use the official installer:

[https://ollama.com/download/windows](https://ollama.com/download/windows)

After installation, open a new PowerShell window and verify:

```powershell
ollama --version
```

### Other platforms

- Main download page: [https://ollama.com/download](https://ollama.com/download)
- Linux install page: [https://ollama.com/download/linux](https://ollama.com/download/linux)

## Pull the required Ollama models

This repo expects these two models:

```powershell
ollama pull mistral
ollama pull nomic-embed-text
```

Notes:

- `mistral` is the answer-generation model
- `nomic-embed-text` is the embedding model used to build and search the vector database

## Add your documents

Put your PDF files into the `data/` folder.

Current example files:

- `data/monopoly.pdf`
- `data/ticket_to_ride.pdf`

Every time you replace or add documents, rebuild the vector database.

## Build the vector database

```powershell
python populate_database.py --reset
```

If you want a machine-readable response:

```powershell
python populate_database.py --reset --json
```

This creates or refreshes the local Chroma database in `chroma/`.

## Query from the command line

```powershell
python query_data.py "How much money does a player start with in Monopoly?"
```

You can also request JSON output:

```powershell
python query_data.py --json "How much money does a player start with in Monopoly?"
```

Optional flags:

- `--model` to change the Ollama generation model
- `--k` to change how many chunks are retrieved from Chroma

Example:

```powershell
python query_data.py --model mistral --k 5 "What is the longest train bonus in Ticket to Ride?"
```

## Call it from another Python process

You can now import the project directly from a server or another Python app instead of shelling out to the CLI.

### Populate the database programmatically

```python
from populate_database import populate_database

result = populate_database(reset=False)
print(result.to_dict())
```

### Query programmatically

```python
from query_data import query_rag_response

response = query_rag_response("How much money does a player start with in Monopoly?")

print(response.response_text)
print(response.sources)
print(response.to_dict())
```

If you only want the plain answer text:

```python
from query_data import query_rag

answer = query_rag("How much money does a player start with in Monopoly?")
print(answer)
```

## Important project note

The current prompt template in `query_data.py` is written like a medical triage assistant, but the sample PDFs in `data/` are board game rulebooks.

That means you should do one of these before using the project seriously:

- Replace the PDFs in `data/` with documents that match the medical prompt
- Or edit the prompt template in `query_data.py` so it matches your actual document set

## Troubleshooting

### `ModuleNotFoundError`

Make sure your virtual environment is active and rerun:

```powershell
python -m pip install -r requirements.txt
```

### `ollama` is not recognized

Ollama is not installed correctly or the terminal was opened before installation. Reopen PowerShell and run:

```powershell
ollama --version
```

If it still fails, reinstall from:
[https://ollama.com/download/windows](https://ollama.com/download/windows)

### No useful answers

- Make sure you ran `python populate_database.py --reset`
- Make sure your PDFs are actually in `data/`
- Make sure the prompt matches your documents

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ollama pull mistral
ollama pull nomic-embed-text
python populate_database.py --reset
python query_data.py "How much money does a player start with in Monopoly?"
```
