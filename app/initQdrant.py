import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader

import dotenv

dotenv.load_dotenv()

#https://medium.com/@himansrivastava/retrieval-augmented-generation-rag-using-qdrant-with-a-pdf-file-45a9c757bf68

def add_unique_id(chunks):
     for chunk in chunks:
         chunk.metadata["chunk_id"] = (
             f"{chunk.metadata['source']}_{chunk.metadata['start_index']}"
         )
     return chunks

def load_pdf_document(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    langchain_documents = []
    for doc in documents:
        langchain_documents.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "source": doc.metadata["source"],
                    "page": doc.metadata["page"],
                    "project": "project_1",
                },
            )
        )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    docs = text_splitter.split_documents(langchain_documents)
    return docs


#https://medium.com/@anixlynch/build-rag-with-qdrant-w-dynamic-prompt-via-langchain-hub-c5ab43758b93
def load_txt_document(doc_path):
    loader = TextLoader(doc_path)  # Load the text file
    document = loader.load()  # Load the document content

    langchain_documents = []
    for doc in document:
         langchain_documents.append(
             Document(
                 page_content=doc.page_content,
                 metadata={
                     "source": doc_path,
#                    "page": doc.metadata["page"],
                     "project": "project_1",
                 },
             )
         )

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100, add_start_index=True)  # Split text into chunks
    docs = text_splitter.split_documents(langchain_documents)  # Process and create document chunks

    return docs


def __add_txt_documents(documents, collection):
    if len(documents) > 0:
        docs_dict = {k: [doc.dict()[k] for doc in documents] for k in documents[0].dict()}
        print("RAG URL", os.environ.get("RAG_URL"), flush=True)
        try:
            client = QdrantClient(os.environ.get("RAG_URL"))  # Adjust the URL to your Qdrant instance
            client.add(
                collection_name=collection,
                documents=docs_dict["page_content"],
                metadata=docs_dict["metadata"],
                ids=[i for i in range(0, len(documents))]
            )
        except Exception as e:
            print(e)


def __load_documents(documentsPath, collection="default"):
    if os.environ.get("RAG_RE_UPLOAD"):
        documents=[]
        for path, subdirs, files in os.walk(documentsPath):
            print("walk", path, subdirs, files)
            for name in files:
                if not name.startswith("."):
                    print("file name", os.path.join(path, name))
                    if name.endswith(".pdf"):
                        doc = load_pdf_document(os.path.join(path, name))
                    elif name.endswith(".txt"):
                        doc = load_txt_document(os.path.join(path, name))
                    else:
                        print("unsuported file type")
                    documents = documents + doc

        documents = add_unique_id(documents)

        __add_txt_documents(documents, collection)

def __load_expert_documents(documentsPath):
    documents = []
    experts=[]
    for path, subdirs, files in os.walk(documentsPath):
        collection = "_".join(path.split("/")[2:])
        experts.append(collection)
        if os.environ.get("RAG_RE_UPLOAD"):
            for name in files:
                if not name.startswith("."):
                    print("file name", os.path.join(path, name))
                    if name.endswith(".pdf"):
                        doc = load_pdf_document(os.path.join(path, name))
                    elif name.endswith(".txt"):
                        doc = load_txt_document(os.path.join(path, name))
                    else:
                        print("unsuported file type")
                    documents = documents + doc
            documents = add_unique_id(documents)
            __add_txt_documents(documents, collection)
    return experts

def initQdrant():

    documentsPath = os.environ["RAG_DOCUMENTS_PATH"]
    print("documentsPath", documentsPath, flush=True)
    __load_documents(documentsPath, "default")

    documentsPath = os.environ["RAG_EXPERT_DOCUMENTS_PATH"]
    print("documentsExpertPath", documentsPath, flush=True)
    experts = __load_expert_documents(documentsPath)

    return experts

def get_doc(request, collection="default"):
    # Initialize Qdrant client
    client = QdrantClient(os.environ["RAG_URL"])
    # Test the db
    search_result = client.query(
        collection_name=collection,
        query_text=request
    )
    return search_result

