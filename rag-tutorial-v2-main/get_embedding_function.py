from __future__ import annotations

DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"


def get_embedding_function(model_name: str = DEFAULT_EMBEDDING_MODEL):
   from langchain_community.embeddings.ollama import OllamaEmbeddings

   return OllamaEmbeddings(model=model_name)

