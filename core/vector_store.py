import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


EMBEDDING_MODEL="all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device":'cpu'}
    )
def build_vector_store(transcript:str)->Chroma:
    print("building vector store")
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks=splitter.split_text(transcript)
    docs=[
        Document(page_content=chunk,metadata={'chunk_index':i})
        for i,chunk in enumerate(chunks)
    ]
    embeddings=get_embeddings()
    vector_store=Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
    )
    return vector_store



def get_retriever(vector_store:Chroma,k:int=4):
    return vector_store.as_retriever(
        search_type='similarity',
        search_kwargs={"k":k}
    )


    