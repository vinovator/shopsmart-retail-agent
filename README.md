# 🛒 ShopSmart Retail Agent

An intelligent customer support agent capable of handling orders, modified with human-in-the-loop flows for high-value refunds. Built with **PydanticAI**, **FastAPI**, and **SQLModel**.

## 🚀 Features

- **Intelligent Chat**: Uses Google's Gemini-Flash to understand natural language queries.
- **Database Integration**: Direct access to customer and order history via SQLModel (SQLite).
- **Tool Use**: Agent can look up orders, check status, and request refunds.
- **Human-in-the-Loop**: High-value refund requests (>$50) trigger a review ticket system for admin approval.
- **Frontend Dashboard**: A comprehensive UI for both Customers (Chat) and Managers (Approval Console).
- **Semantic Product Search**: Vector-based search using `Qdrant` and `Google Gen AI` to find products by meaning (e.g., "winter clothes").
- **REST API**: FastAPI endpoints for chat interaction and admin dashboard actions.

## 📂 Project Structure

```text
shopsmart-retail-agent/
├── app/
│   ├── __init__.py           # Makes 'app' a Python package (Crucial for imports)
│   ├── main.py               # THE DOORMAN.
│   │                         # - Receives HTTP requests (POST /chat)
│   │                         # - Handles errors (404, 500)
│   │                         # - Connects the Agent to the Web
│   │
│   ├── dependencies.py       # THE SECURITY GUARD.
│   │                         # - Checks "User-ID" header
│   │                         # - Opens/Closes DB sessions safely
│   │                         # - Passes 'SupportDeps' to the Agent
│   │
│   ├── agent.py              # THE BRAIN.
│   │                         # - Defines the LLM (Gemini-Flash)
│   │                         # - Defines the Tools (request_refund, check_stock)
│   │                         # - Contains the Business Rules (if price > $50)
│   │
│   ├── models.py             # THE CONTRACT.
│   │                         # - Defines Database Tables (User, Order)
│   │                         # - Defines Validation Rules (Email must be valid)
│   │
│   └── utils/
│       └── db.py             # THE VAULT KEY.
│                             # - Creates the Engine
│                             # - Ensures we point to the correct database.db file
│
├── static/
│   └── index.html            # THE FACE.
│                             # - Single-page dashboard for Chat & Admin
│
├── notebooks/
│   └── seed_data.ipynb       # THE GOD MODE.
│                             # - Creates the universe (Products, Users, History)
│                             # - Used only during setup/dev
│
├── scripts/
│   ├── manual_chat.py        # THE PLAYGROUND.
│   │                         # - A safe place to test the Brain without the Web
│   └── embed_products.py     # DOMAIN KNOWLEDGE.
│                             # - Embeds products into the Vector DB
│
├── .env                      # THE SECRETS (API Keys)
└── database.db               # THE STORAGE (SQLite File)
```

## 🛠️ Setup & Installation

1.  **Clone the repository**
2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment**
    Create a `.env` file in the root directory and add your Google API Key:
    ```ini
    GOOGLE_API_KEY=your_api_key_here
    ```

## 🏃 Usage

### 1. Seed the Database
Before running the agent, populate the database with dummy data using the provided notebook:
- Open `notebooks/seed_data.ipynb` in VS Code or Jupyter.
- Run all cells to reset and seed `database.db`.

### 2. Setup Vector Database (Semantic Search)
To enable the "search_products" tool, you must generate the vector embeddings:
```bash
python scripts/embed_products.py
```
This requires `GOOGLE_API_KEY` to be set in your `.env`.

### 3. Manual Testing (CLI)
Test the agent logic directly in the terminal without starting the server:
```bash
python scripts/manual_chat.py
```

### 4. Run the Web Server
Start the FastAPI backend:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
**Open your browser to `http://127.0.0.1:8000` to access the Dashboard.**

### 5. API Endpoints
- **Chat**: `POST /chat`
  - Headers: `User-ID: <customer_id>`
  - Body: `{"message": "Can I return order 123?"}`
- **Admin List**: `GET /admin/tickets`
- **Admin Review**: `POST /admin/refunds/{ticket_id}/decision`
  - Body: `{"decision": "approve"}` or `{"decision": "reject"}`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
