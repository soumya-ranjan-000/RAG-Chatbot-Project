import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import chromadb
    from sentence_transformers import SentenceTransformer
    import os
    from langchain_anthropic import ChatAnthropic
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage
    from dotenv import load_dotenv

    load_dotenv()

    # 1. SETUP & STATE
    # This state holds the context retrieved for the MOST RECENT message
    get_sources, set_sources = mo.state([])

    @mo.cache
    def load_resources():
        embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        db_client = chromadb.PersistentClient(path=r"D:\RAG Chatbot Project\proof-of-concepts\rag\policy_vector_db")
        collection = db_client.get_collection(name="company_policies")

        return embed_model, collection

    embed_model, collection = load_resources()
    return (
        AIMessage,
        ChatAnthropic,
        ChatPromptTemplate,
        HumanMessage,
        MessagesPlaceholder,
        collection,
        embed_model,
        get_sources,
        mo,
        set_sources,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Select The LLM Provider & Model
    """)
    return


@app.cell
def _(ChatAnthropic):
    # Initialize the Anthropic model via LangChain
    llm = ChatAnthropic(model="claude-opus-4-7", streaming=True)
    return (llm,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### The RAG Engine
    """)
    return


@app.cell
def _(
    AIMessage,
    ChatPromptTemplate,
    HumanMessage,
    MessagesPlaceholder,
    collection,
    embed_model,
    llm,
    set_sources,
):
    def rag_chat_engine(messages, config):
        user_query = messages[-1].content

        # A. Retrieval
        query_emb = embed_model.encode(user_query).tolist()
        results = collection.query(query_embeddings=[query_emb], n_results=3)

        # B. Update the Source Inspector state
        retrieved_data = [
            {"Source": m.get("source"), "Snippet": d} 
            for m, d in zip(results['metadatas'][0], results['documents'][0])
        ]
        set_sources(retrieved_data)

        # C. LangChain Prompting
        context_str = "\n\n".join([f"Source: {r['Source']}\n{r['Snippet']}" for r in retrieved_data])

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a helpful policy assistant. Use the following context to answer.\n\nCONTEXT:\n{context_str}"),
            MessagesPlaceholder(variable_name="history"),
        ])

        # D. Convert marimo messages to LangChain format
        lc_messages = []
        for m in messages:
            if m.role == "user":
                lc_messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))

        # E. Stream the response
        chain = prompt | llm

        for chunk in chain.stream({"history": lc_messages}):
            if chunk.content:
                yield chunk.content

    return (rag_chat_engine,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The UI Layout
    """)
    return


@app.cell
def _(get_sources, mo, set_sources):
    # --- CELL A: UI Definitions ---
    current_sources = get_sources()

    # 1. Define the table
    inspector = mo.ui.table(
        current_sources,
        label="Context Inspector (Evidence used for last response)",
        selection="single"
    )

    # 2. Define the reset logic - simplify this
    def reset_all(_):
        set_sources([]) 

    clear_button = mo.ui.button(
        label="Clear Chat & Sources",
        on_click=reset_all,
        kind="neutral"
    )
    return clear_button, inspector


@app.cell
def _(clear_button, inspector, mo, rag_chat_engine):
    # --- CELL B: Final Layout ---

    # 1. Safe to read inspector.value now
    selected_snippet = (
        mo.callout(f"{inspector.value[0]['Snippet']}", kind="info") 
        if len(inspector.value) > 0 
        else mo.md("*Select a row in the inspector to see full text*")
    )

    # 2. Render the full UI
    mo.vstack([
        mo.hstack([
            mo.md("# 🤖 Policy AI"),
            clear_button 
        ], justify="space-between"),
    
        mo.hstack([
            # Left Column: Chat
            mo.vstack([
                mo.md("### Chat"),
                mo.vstack([
                    # Removed the 'key' argument that caused the error
                    mo.ui.chat(
                        rag_chat_engine, 
                        show_configuration_controls=True
                    )
                ]).style({
                    "max-height": "600px", 
                    "overflow-y": "auto",
                    "border": "1px solid #e1e4e8",
                    "padding": "10px",
                    "border-radius": "8px"
                })
            ]),
            # Right Column: Inspector
            mo.vstack([
                mo.md("### 🔍 Source Inspector"),
                inspector,
                selected_snippet 
            ])
        ], widths=[1, 1], align="start")
    ])
    return


if __name__ == "__main__":
    app.run()
