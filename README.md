# Quizzard

![Quizzard Logo](https://github.com/user-attachments/assets/63050fd4-2a53-4a5a-9586-430190da14c8)
![Quizzard Interface](https://github.com/user-attachments/assets/632ef62c-2ba9-4f26-8527-aff995181ecf)

## About Quizzard

Quizzard is an intelligent educational platform developed during the CodeStorm Hackathon at UNITVB University. The platform leverages AI to revolutionize how students study and how teachers create educational materials.

### Team CodeStorm
- Madalin
- Alin
- Costin
- Marian

## 🚀 Features

### 📚 Interactive Document-Based Learning
Upload your learning materials (PDFs, documents) and interact with them through an AI-powered chat interface. Ask questions about your documents and get intelligent answers based on the content.

### 🧠 Adaptive Question Learning Environment
Practice with questions that adapt to your knowledge level. If you answer incorrectly, Quizzard adjusts and provides additional questions until you master the concept. This creates a personalized learning path for each student.

### 📝 Custom Quiz Generation for Educators
Teachers can quickly generate custom quizzes based on specific topics, choosing from multiple question formats:
- Multiple choice questions
- Single choice questions
- True/False questions

## 🛠️ Technology Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python with Flask
- **AI Models**:
  - Ollama integration
  - Mistral
  - Gemma B2
- **Vector Database**: Chroma DB for document retrieval
- **Document Processing**:
  - LangChain for document handling and text splitting
  - Various PDF and text loaders for different file formats

## 🧩 System Architecture

Quizzard consists of two main components:

1. **RAG System (Retrieval-Augmented Generation)**:
   - Document ingestion and processing
   - Vector embedding for semantic search
   - Context-based question answering

2. **Web Interface**:
   - Intuitive UI for students and teachers
   - Real-time chat interface
   - Quiz creation and management tools

## 💡 The Idea Behind Quizzard

Quizzard was born from the need to make learning more accessible and personalized. Traditional educational approaches often follow a one-size-fits-all model, but we believe that AI can transform education by:

1. **Personalizing the learning experience** through adaptive questioning
2. **Reducing teacher workload** by automating quiz creation
3. **Making study materials more interactive** through conversational AI

Our solution brings advanced AI capabilities into the classroom in an accessible way, helping both students and educators get more from their educational materials.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Flask
- Ollama (running locally)

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/quizzard.git
cd quizzard
