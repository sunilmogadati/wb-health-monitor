import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.agents import create_agent

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory="./chroma_worldbank_db", embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})


def rag_answer(question):
    retrieved_docs = retriever.invoke(question)
    context = "\n".join([doc.page_content for doc in retrieved_docs])

    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=[],
        system_prompt="Answer the user's question using only the country data provided below. If the data doesn't contain enough information to answer, say so.\n\nCountry data:\n" + context
    )

    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content


while True:
    user_input = input("Ask something (or type 'exit'): ")
    if user_input.lower() == "exit":
        break
    print(rag_answer(user_input))