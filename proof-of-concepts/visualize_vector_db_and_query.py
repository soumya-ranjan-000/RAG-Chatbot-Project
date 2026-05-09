import marimo

__generated_with = "0.23.4"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    CHROMA_PATH = os.path.join(os.getcwd(), "rag", "policy_vector_db")
    print(f"ChromaDB Path: {CHROMA_PATH}")
    return (CHROMA_PATH,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Imports and Data Loading
    """)
    return


@app.cell
def _(CHROMA_PATH):
    import marimo as mo
    import umap
    import chromadb
    import numpy as np
    import textwrap
    import plotly.graph_objects as go
    from sentence_transformers import SentenceTransformer

    # 1. CONFIGURATION
    COLLECTION_NAME = "company_policies"
    MODEL_NAME = 'all-MiniLM-L6-v2'

    @mo.cache
    def load_and_project_data():
        model = SentenceTransformer(MODEL_NAME)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)

        # Fetch all vectors
        all_data = collection.get(include=["embeddings", "metadatas", "documents"])
        embeddings = np.array(all_data['embeddings'])

        # Compute 2D Projections (UMAP)
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
        projections = reducer.fit_transform(embeddings)

        return model, collection, projections, all_data

    # Initialize
    model, collection, projections, data = load_and_project_data()

    # 2. DEFINE UI ELEMENTS
    search_input = mo.ui.text(placeholder="Search policies...", label="Query:", full_width=True)
    search_button = mo.ui.run_button(label="🔍 Search & Highlight", kind="neutral")

    # Display Header and Search Bar
    mo.vstack([
        mo.md("# 🗂️ Vector Database Explorer"),
        mo.hstack([search_input, search_button], justify="start")
    ])
    return (
        collection,
        data,
        go,
        mo,
        model,
        projections,
        search_button,
        search_input,
        textwrap,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Visualization Logic
    """)
    return


@app.cell
def _(
    collection,
    data,
    go,
    mo,
    model,
    projections,
    search_button,
    search_input,
    textwrap,
):
    def get_explorer_view():
        highlight_ids = []
        search_results_data = []

        # 1. Run Search Logic
        if search_button.value and search_input.value:
            query_emb = model.encode(search_input.value).tolist()
            results = collection.query(query_embeddings=[query_emb], n_results=5)
            highlight_ids = results['ids'][0]

            # Prepare data for the table
            for i in range(len(results['ids'][0])):
                search_results_data.append({
                    "ID": results['ids'][0][i],
                    "Distance": round(results['distances'][0][i], 4),
                    "Source": results['metadatas'][0][i].get('source', 'N/A'),
                    "Content": textwrap.shorten(results['documents'][0][i], width=200)
                })

        # 2. Build the Plot
        colors = ['#ff4b4b' if tid in highlight_ids else 'rgba(100, 150, 250, 0.3)' for tid in data['ids']]
        sizes = [15 if tid in highlight_ids else 7 for tid in data['ids']]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=projections[:, 0], 
            y=projections[:, 1], 
            mode='markers',
            marker=dict(
                color=colors, 
                size=sizes, 
                line=dict(width=1, color='white')
            ),
            text=[f"<b>Source: {m.get('source')}</b><br>{textwrap.shorten(d, 60)}" 
                  for m, d in zip(data['metadatas'], data['documents'])],
            hoverinfo='text'
        ))

        fig.update_layout(
            title="Embedding Space (UMAP)",
            template="plotly_dark",
            height=500,
            margin=dict(l=0, r=0, b=0, t=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        # 3. Create the Layout
        # Use mo.ui.table for a professional look at the bottom
        results_table = mo.ui.table(search_results_data, label="Top 5 Relevant Documents") if search_results_data else mo.md("*Enter a query to see matched documents*")

        return mo.vstack([
            mo.as_html(fig),
            mo.md("### 📄 Matching Context"),
            results_table
        ])

    get_explorer_view()
    return


if __name__ == "__main__":
    app.run()
