import pandas as pd
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

df = pd.read_csv("worldbank_final_dataset.csv")

documents = []
for _, row in df.iterrows():
    text = (
        f"{row['country']} has a life expectancy of {row['life_expectancy']:.1f} years. "
        f"Its GDP per capita is {row['gdp_per_capita']:.2f} USD. "
        f"Health expenditure per capita is {row['health_expenditure_per_capita']:.2f} USD. "
        f"{row['internet_users_pct']:.1f}% of the population uses the internet. "
        f"The population growth rate is {row['population_growth']:.2f}% per year."
    )
    documents.append(Document(page_content=text, metadata={"country": row["country"]}))

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(documents, embeddings, persist_directory="./chroma_worldbank_db")

print("Vector store built with", vectorstore._collection.count(), "documents")