"""
Pipeline de busca RAG — NovaTech
Recebe uma pergunta, gera embedding e retorna os 5 chunks mais similares
da collection 'novatech' no ChromaDB.
"""

import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "novatech"
TOP_K = 5


def recuperar(pergunta: str) -> list[dict]:
    """
    Gera o embedding da pergunta, consulta o ChromaDB e retorna os TOP_K
    chunks mais similares como lista de dicts com as chaves:
      texto, source, section, score
    """
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode(pergunta).tolist()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    resultados = collection.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for texto, meta, distancia in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        chunks.append(
            {
                "texto": texto,
                "source": meta.get("source", "—"),
                "section": meta.get("section", "—"),
                "score": 1 / (1 + distancia),  # distância L2 → score [0, 1]
            }
        )
    return chunks


def buscar(pergunta: str) -> None:
    chunks = recuperar(pergunta)

    print(f"\nPergunta: {pergunta}")
    print(f"{'─' * 72}\n")

    for i, chunk in enumerate(chunks, start=1):
        print(f"[{i}] Score de similaridade: {chunk['score']:.4f}")
        print(f"    Arquivo : {chunk['source']}")
        print(f"    Seção   : {chunk['section']}")
        print(f"    Texto   :\n{chunk['texto']}\n")
        print(f"{'─' * 72}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pergunta = " ".join(sys.argv[1:])
    else:
        pergunta = input("Digite sua pergunta: ").strip()

    if not pergunta:
        print("Nenhuma pergunta fornecida.")
        sys.exit(1)

    buscar(pergunta)
