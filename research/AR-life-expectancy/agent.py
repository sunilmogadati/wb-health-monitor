import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from predict_tool import lookup_country, predict_life_expectancy

load_dotenv()

tools = [lookup_country, predict_life_expectancy]

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=tools,
    system_prompt="You are a helpful assistant answering questions about life expectancy using World Bank data. If the user asks about a real country by name, use lookup_country. If the user gives you hypothetical numbers instead of a country name, use predict_life_expectancy. If required information is missing, ask the user for it before calling a tool."
)


while True:
    user_input = input("Ask something : ")
    if user_input.lower() == "exit":
        break
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    print(result["messages"][-1].content)