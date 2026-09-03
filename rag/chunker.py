from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text, source_path, chunk_size=500, chunk_overlap=50):
    # 末尾的 "" 是必须的兜底：当文本里找不到上面任何分隔符时（如无空格/标点的长串、
    # 压缩代码、长 URL、base64），LangChain 会放弃切分、把整段当成一个块，
    # 导致块体积失控、塞进 prompt 后撑爆 LLM 请求（实测触发 DeepSeek 413）。
    # 加上 "" 后，最差情况会退化成按字符切分，保证块长不超过 chunk_size。
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""]
    )
    return splitter.create_documents(
        texts=[text],
        metadatas=[{"source": source_path}]
    )
