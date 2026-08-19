from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text, source_path):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "，", " "]
    )
    return splitter.create_documents(
        texts=[text],
        metadatas=[{"source": source_path}]
    )
