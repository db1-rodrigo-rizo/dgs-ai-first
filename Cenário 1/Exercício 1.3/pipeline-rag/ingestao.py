"""
Pipeline de ingestão RAG — NovaTech
Estratégia de chunking conforme seção 5 da Análise Técnica de Viabilidade v2:
  - Tabelas markdown  → row-as-chunk com cabeçalho injetado (§5.1)
  - Texto narrativo   → chunking hierárquico por seção H2/H3, overlap 15% (§5.3/5.4)
"""

import hashlib
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent / "documentos"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "novatech"
OVERLAP_RATIO = 0.15   # 15% de overlap para chunks narrativos (§5.4)
OVERLAP_MIN_WORDS = 50  # floor de 50 tokens conforme §5.2/5.3


# ---------------------------------------------------------------------------
# Helpers de chunking
# ---------------------------------------------------------------------------

def get_tail(text: str) -> str:
    """Retorna os últimos OVERLAP_RATIO% das palavras do texto (para overlap)."""
    words = text.split()
    n = max(OVERLAP_MIN_WORDS, int(len(words) * OVERLAP_RATIO))
    return " ".join(words[-n:]) if len(words) > n else text


def table_to_row_chunks(table_text: str, section_header: str) -> list[str]:
    """
    Converte uma tabela markdown em um chunk por linha de dados.
    Cada chunk tem os cabeçalhos de coluna injetados como prefixo (§5.1).
    """
    lines = [ln for ln in table_text.strip().splitlines() if ln.strip()]
    # Necessário: linha de cabeçalho + separador + ao menos 1 linha de dados
    if len(lines) < 3:
        return [f"[Seção: {section_header}]\n{table_text}"]

    col_headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    # lines[1] é o separador (---|---)
    data_rows = lines[2:]

    chunks = []
    for row in data_rows:
        cells = [c.strip() for c in row.split("|") if c.strip()]
        if not cells:
            continue
        pairs = " | ".join(
            f"{col}: {val}" for col, val in zip(col_headers, cells)
        )
        chunks.append(f"[Seção: {section_header}]\n{pairs}")

    return chunks if chunks else [f"[Seção: {section_header}]\n{table_text}"]


def split_body_into_blocks(body: str) -> list[tuple[str, str]]:
    """
    Divide o corpo de uma seção em blocos ('table' | 'narrative').
    Blocos de tabela são linhas contíguas que começam com '|'.
    """
    blocks: list[tuple[str, str]] = []
    lines = body.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            blocks.append(("table", "\n".join(table_lines)))
        else:
            narrative_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("|"):
                narrative_lines.append(lines[i])
                i += 1
            text = "\n".join(narrative_lines).strip()
            if text:
                blocks.append(("narrative", text))

    return blocks


# ---------------------------------------------------------------------------
# Chunking de documento
# ---------------------------------------------------------------------------

def chunk_document(filepath: Path) -> list[dict]:
    """
    Lê um arquivo .md e retorna lista de chunks com metadados.
    Cada item: {"text": str, "source": str, "section": str}
    """
    content = filepath.read_text(encoding="utf-8")

    # Extrai seções por cabeçalhos H1/H2/H3
    header_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(header_re.finditer(content))

    sections: list[tuple[str, str]] = []

    # Preâmbulo antes do primeiro cabeçalho (ex.: metadados do documento)
    if matches and matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append(("(cabeçalho do documento)", preamble))
    elif not matches:
        sections.append(("(documento)", content.strip()))

    for i, m in enumerate(matches):
        header_text = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body:
            sections.append((header_text, body))

    result: list[dict] = []
    prev_tail = ""  # tail da última seção narrativa para overlap

    for section_header, body in sections:
        blocks = split_body_into_blocks(body)
        section_has_narrative = False

        for block_type, block_text in blocks:
            if block_type == "table":
                # §5.1 — row-as-chunk; sem overlap entre linhas
                for row_chunk in table_to_row_chunks(block_text, section_header):
                    result.append(
                        {
                            "text": row_chunk,
                            "source": filepath.name,
                            "section": section_header,
                        }
                    )
            else:
                # §5.3/5.4 — texto narrativo com overlap de 15%
                text_with_overlap = (
                    (prev_tail + "\n" + block_text).strip() if prev_tail else block_text
                )
                chunk_text = f"[Seção: {section_header}]\n{text_with_overlap}"
                result.append(
                    {
                        "text": chunk_text,
                        "source": filepath.name,
                        "section": section_header,
                    }
                )
                prev_tail = get_tail(block_text)
                section_has_narrative = True

        if not section_has_narrative:
            prev_tail = ""  # seções de pura tabela não propagam overlap narrativo

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Carregando modelo de embeddings (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    all_chunks: list[dict] = []
    md_files = sorted(DOCS_DIR.glob("*.md"))

    if not md_files:
        print(f"Nenhum arquivo .md encontrado em {DOCS_DIR}")
        return

    print(f"\nProcessando {len(md_files)} documento(s)...")
    for md_file in md_files:
        chunks = chunk_document(md_file)
        all_chunks.extend(chunks)
        print(f"  {md_file.name}: {len(chunks)} chunks")

    print(f"\nGerando embeddings para {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # IDs baseados em hash MD5 do texto para idempotência (re-ingestão não duplica)
    ids = [hashlib.md5(t.encode("utf-8")).hexdigest() for t in texts]
    metadatas = [{"source": c["source"], "section": c["section"]} for c in all_chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"\nTotal de chunks armazenados na collection '{COLLECTION_NAME}': {collection.count()}")


if __name__ == "__main__":
    main()
