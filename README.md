### MessageRetrieval ###

This repository contains the novel SQL generation prompt templates and iMessage table schema for pseudo-RAG with iMessage data. The goal of this work is to be able to ask questions to your text messages, using SQL translation to retrieve information from a database with simple natural language requests instead of embedding the entire database in a vector store.

Requirements:
- You will need a llama model from HuggingFace (link TBD)
- ggml
- LangChain (version)
- You will need to copy your chat.db file from `~/Library/Messages/chat.db` to a new location (ideally this repo)

## Update

I have added some initial code for a text2SQL pipeline with the iMessage `chat.db` file to index over texts with natural language. The pipeline uses an LLM-as-Judge pattern for scoring and ranking retrieved messages with respect to the original query. More updates to come soon here.

There will be more updates made with this repository, as it is in very early stages. Updates coming soon.
