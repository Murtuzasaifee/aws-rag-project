<div align="center">

# 🚀 AWS RAG Platform

</div>


<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://aws.amazon.com/"><img src="https://img.shields.io/badge/AWS-FF9900?logo=amazon-aws&logoColor=white" alt="AWS"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/vrajpatel2891/aws-rag-platform/releases"><img src="https://img.shields.io/badge/Version-0.1.0-blue.svg" alt="Version"></a>
</p>

> Production-ready AWS-native Retrieval-Augmented Generation (RAG) application built with FastAPI

## 📖 Overview

AWS RAG Platform is a modern, scalable backend service for building Retrieval-Augmented Generation applications on AWS. It provides a robust API for integrating large language models (LLMs) with your data, enabling intelligent question-answering systems, document search, and knowledge base applications.

## ✨ Features

- **🔌 FastAPI Backend** - High-performance async API built with FastAPI
- **☁️ AWS Native** - Designed for seamless deployment on AWS infrastructure
- **📚 RAG Architecture** - Built-in support for Retrieval-Augmented Generation
- **🔒 Production Ready** - Includes CORS middleware, health checks, and error handling
- **📁 File Upload Support** - Built-in support for uploading documents to `data/uploads`
- **🛠️ Extensible** - Modular architecture for easy customization and extension
- **📖 API Documentation** - Auto-generated docs with Swagger UI and ReDoc

## 🧩 Chunking Technique

This project uses a modular, token-aware chunking service in `src/ragapp/services/chunking.py`.

- Default strategy: `FixedWindowChunker`
  - token-based chunk size: `512` tokens
  - overlap: `50` tokens
  - tries to split at paragraph and sentence boundaries
- Structured strategy: `RecursiveChunker`
  - detects document blocks like code, tables, lists, and paragraphs
  - recursively splits large blocks while preserving document hierarchy
- Uses the same tokenizer as the embedding model (`amazon.titan-embed-text-v2`)
  - ensures chunks fit Bedrock input limits
- Each chunk carries metadata:
  - `document_id`
  - `chunk_index`
  - `page_number`
  - `character_offsets`
  - `source_metadata`

## 🛠️ Tech Stack

| Category          | Technology             |
| ----------------- | ---------------------- |
| **Framework**     | FastAPI                |
| **Language**      | Python 3.12+           |
| **Server**        | Uvicorn                |
| **Validation**    | Pydantic               |
| **Configuration** | Pydantic Settings      |
| **Deployment**    | AWS (ECS, Lambda, EC2) |

## 📋 Prerequisites

- Python 3.12 or higher
- AWS Account (for cloud deployment)
- API Keys for LLM providers (optional)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Murtuzasaifee/aws-rag-project.git
cd aws-rag-project
```

### 2. Create Virtual Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using virtualenv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Application Settings

PORT=8000

```

### 5. Run the Application

```bash
# Development mode
uvicorn app:app --reload

# Or using the Python script
python app.py
```

The API will be available at:

- **API Base URL**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Docs**: `http://localhost:8000/redoc`


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
