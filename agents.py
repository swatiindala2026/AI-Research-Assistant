
import os
from dotenv import load_dotenv
from crewai import Agent
from crewai.llms.providers.openai.completion import OpenAICompletion

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file")

llm = OpenAICompletion(
    model=model_name,
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    custom_openai=True,
    temperature=0.2
)

# 1. Discovery Agent
discovery_agent = Agent(
    role="Research Paper Discovery Expert",
    goal="Organize and verify supplied research paper metadata",
    backstory="You are an academic research expert.",
    llm=llm,
    verbose=True
)

# 2. Summarization Agent
summarization_agent = Agent(
    role="Research Paper Summarizer",
    goal="Summarize available research abstracts accurately",
    backstory="You are an expert in research paper analysis.",
    llm=llm,
    verbose=True
)

# 3. Literature Review Agent
literature_agent = Agent(
    role="Literature Review Expert",
    goal="Compare research methods and findings",
    backstory="You are an academic literature reviewer.",
    llm=llm,
    verbose=True
)

# 4. Research Gap Agent
gap_agent = Agent(
    role="Research Gap Analyst",
    goal="Identify evidence-based research gaps",
    backstory="You analyze limitations and future research opportunities.",
    llm=llm,
    verbose=True
)

# 5. Report Agent
report_agent = Agent(
    role="Research Report Writer",
    goal="Prepare a complete academic research report",
    backstory="You are an academic report writing expert.",
    llm=llm,
    verbose=True
)

print("All 5 AI Agents configured successfully!")
