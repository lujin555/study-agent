from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text, source_path, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " "]
    )
    return splitter.create_documents(
        texts=[text],
        metadatas=[{"source": source_path}]
    )
