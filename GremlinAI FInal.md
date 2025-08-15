# **Project Title: gremlinsAI**

## **Primary Objective**

To build a sophisticated, headless, **multi-modal** AI system named **"gremlinsAI."** The system will serve as an extensible, API-first platform for diverse tasks, featuring specialized agents that can reason across text, audio, and video, use tools, and collaborate to solve complex problems. The entire system will be accessible through a robust and well-documented API, empowering developers to build powerful applications on top of its advanced analytical capabilities.

## **Core Philosophy**

**CRITICAL REQUIREMENT:** Our philosophy is **headless, powerful, and extensible.** We will build a single, self-contained backend application that manages all processes. This application will expose its full functionality through a clean, modern API. This approach empowers developers and other AI systems to build custom interfaces and integrations, prioritizing flexibility and power over a built-in UI.

### **Application Entry Point (app/main.py)**

This file is the central glue for the entire FastAPI application. It initializes the app and includes all the API routers from the different modules.

\# app/main.py  
from fastapi import FastAPI, Request, status  
from fastapi.responses import JSONResponse  
from fastapi.exceptions import RequestValidationError  
from app.api.v1.endpoints import agent, chat\_history, orchestrator

\# Create the main FastAPI application instance  
app \= FastAPI(  
    title="gremlinsAI",  
    description="API for the gremlinsAI multi-modal agentic system.",  
    version="1.0.0"  
)

\# Global Error Handling  
@app.exception\_handler(RequestValidationError)  
async def validation\_exception\_handler(request: Request, exc: RequestValidationError):  
    return JSONResponse(  
        status\_code=status.HTTP\_422\_UNPROCESSABLE\_ENTITY,  
        content={"code": "VALIDATION\_ERROR", "message": "Input validation failed", "details": exc.errors()},  
    )

\# Include the API routers from different modules  
app.include\_router(agent.router, prefix="/api/v1/agent", tags=\["Agent"\])  
app.include\_router(chat\_history.router, prefix="/api/v1/history", tags=\["Chat History"\])  
app.include\_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=\["Orchestrator"\])

@app.get("/", tags=\["Root"\])  
async def read\_root():  
    """  
    A simple root endpoint to confirm the API is running.  
    """  
    return {"message": "Welcome to the gremlinsAI API\!"}

### **Running the Application (start.sh)**

This shell script provides the single command to start the entire backend server. It ensures the uvicorn server is run with the correct parameters for development.

\#\!/bin/bash  
\# start.sh: A simple script to run the gremlinsAI FastAPI server.  
HOST="127.0.0.1"  
PORT="8000"  
APP\_MODULE="app.main:app"  
GREEN='\\033\[0;32m'  
NC='\\033\[0m' \# No Color  
echo \-e "${GREEN}Starting gremlinsAI server...${NC}"  
echo \-e "Access the API documentation at http://${HOST}:${PORT}/docs"  
uvicorn ${APP\_MODULE} \--host ${HOST} \--port ${PORT} \--reload

### **Environment Configuration (.env.example)**

This file serves as a template for all required environment variables. Developers should copy this to a .env file and fill in the values.

\# .env.example  
\# This file contains all the environment variables needed for the application.  
\# Copy this file to .env and fill in the appropriate values.

\# \-- Core Application Settings \--  
LOG\_LEVEL="INFO"  
DATABASE\_URL="sqlite:///./data/gremlinsai.db"

\# \-- Ollama Configuration (for local LLMs) \--  
\# Required if using a local model via Ollama  
OLLAMA\_BASE\_URL="http://localhost:11434"

\# \-- External API Keys (add as needed) \--  
\# Example for OpenAI  
\# OPENAI\_API\_KEY="your-openai-api-key"

\# \-- Phase 4+ Technology Configurations \--  
QDRANT\_HOST="localhost"  
QDRANT\_PORT="6333"  
MINIO\_ENDPOINT="localhost:9000"  
MINIO\_ACCESS\_KEY="minioadmin"  
MINIO\_SECRET\_KEY="minioadmin"  
KAFKA\_BROKER\_URLS="localhost:9092"  
REDIS\_URL="redis://localhost:6379"

### **Dependency Management (requirements.txt)**

This file lists the exact Python dependencies required to run the project, ensuring a reproducible environment.

\# FastAPI and Server  
fastapi==0.111.0  
uvicorn\[standard\]==0.29.0

\# LangChain and LangGraph  
langchain==0.1.20  
langgraph==0.0.48  
langchain-community==0.0.38  
langchain-core==0.1.52  
langchain-openai \# For later phases

\# CrewAI  
crewai==0.28.8  
crewai\_tools==0.1.6

\# Tools  
duckduckgo-search==5.3.1b1  
ffmpeg-python==0.2.0  
openai-whisper==20231117

\# LLM Integration  
ollama==0.2.0

\# Database  
sqlalchemy==2.0.23  
alembic==1.13.1  
qdrant-client==1.7.3

\# Object Storage  
minio==7.2.0

\# Asynchronous Tasks & Messaging  
celery==5.3.6  
redis==5.0.1  
kafka-python==2.0.2

\# API & Communication  
strawberry-graphql\[fastapi\]==0.215.0  
grpcio==1.60.0  
grpcio-tools==1.60.0

\# Utilities  
python-dotenv==1.0.1  
pydantic\<3,\>2

## **System-Wide Conventions**

### **Error Handling Strategy**

* **Global Exception Handling:** A global exception handler is defined in app/main.py to catch FastAPI's RequestValidationError. This ensures that all validation errors return a standardized 422 Unprocessable Entity response.  
* **Standardized Error Format:** All API errors should conform to the structure: {"code": "ERROR\_CODE", "message": "A human-readable error message."}. For validation errors, a details field will be included.  
* **Agent-Specific Errors:** Within agent and tool logic, errors (e.g., a tool failing to execute) will be caught in try...except blocks. The error information will be logged and incorporated into the agent's state to allow it to reason about the failure and potentially retry or choose a different tool.

### **Logging and Monitoring Strategy**

* **Structured Logging:** All services will use Python's built-in logging module. The long-term goal is to use structured logging (e.g., JSON format) to make logs easily parsable by monitoring systems.  
* **Logging Levels:** The LOG\_LEVEL will be configurable via an environment variable (INFO, DEBUG, WARNING, ERROR).  
* **Future Monitoring:** In later phases, the application will be instrumented to expose metrics (e.g., API latency, error rates) for collection by a Prometheus/Grafana stack.

## **The Development Roadmap: An Expanded Phased Approach**

### **Phase 1: The Core Agent Engine ⚙️**

**Goal:** Create a foundational, tool-using AI agent.

* **Tasks:** Environment Setup, Build Agent Graph, Integrate First Tool, Initial Test Runner.

### **Phase 1 Elaboration: Agent & Tool Implementation Details**

#### **A. Tool Specifications (app/core/tools.py)**

\# app/core/tools.py  
from langchain\_community.tools import DuckDuckGoSearchRun  
from pydantic import BaseModel, Field

\# Initialize the tool. This can be reused across the application.  
search\_tool \= DuckDuckGoSearchRun()

class SearchInput(BaseModel):  
    query: str \= Field(description="The search query to execute.")

def duckduckgo\_search(query: str) \-\> str:  
    """  
    A wrapper for the DuckDuckGo Search tool to be used by agents.  
    It takes a query string and returns the search results.  
    """  
    print(f"--- Executing search for: {query} \---")  
    return search\_tool.invoke(query)

\# In later phases, more tools will be added here.  
\# Example:  
\# def transcribe\_video\_audio(video\_path: str) \-\> str: ...

#### **B. Core Agent Logic (app/core/agent.py)**

\# app/core/agent.py  
from langchain\_core.agents import AgentAction, AgentFinish  
from langchain\_core.messages import BaseMessage  
from langgraph.graph import StateGraph, END  
from langgraph.prebuilt import ToolNode  
from typing import TypedDict, Annotated, List, Union  
import operator  
from app.core.tools import duckduckgo\_search  
from langchain\_openai import ChatOpenAI \# Will be used with a proper model  
from langchain\_core.prompts import ChatPromptTemplate  
from langchain.agents import create\_tool\_calling\_agent

\# This would be configured with a real model  
\# llm \= ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)  
\# For now, we'll simulate the agent's logic

\# 1\. Define the state  
class AgentState(TypedDict):  
    input: str  
    chat\_history: list\[BaseMessage\]  
    agent\_outcome: Union\[AgentAction, AgentFinish, None\]  
    intermediate\_steps: Annotated\[list\[tuple\[AgentAction, str\]\], operator.add\]

\# 2\. Define the tools and the ToolNode  
tools \= \[duckduckgo\_search\]  
tool\_node \= ToolNode(tools)

\# 3\. Define the agent logic (simulated for now)  
def run\_agent(data: AgentState) \-\> dict:  
    """Simulates an LLM call to decide the next action."""  
    input\_text \= data\['input'\]  
    print(f"--- Agent running on Input: {input\_text} \---")  
    \# This is where a real agent would use an LLM with ReAct prompting.  
    \# For now, we hardcode the decision to use the search tool.  
    action \= AgentAction(tool="duckduckgo\_search", tool\_input=input\_text, log="")  
    return {"agent\_outcome": action}

\# 4\. Define the conditional edge logic  
def should\_continue(data: AgentState) \-\> str:  
    """Determines whether to continue the loop or end."""  
    if isinstance(data\['agent\_outcome'\], AgentFinish):  
        return "end"  
    else:  
        return "continue"

\# 5\. Define the graph  
workflow \= StateGraph(AgentState)  
workflow.add\_node("agent", run\_agent)  
workflow.add\_node("action", tool\_node)  
workflow.set\_entry\_point("agent")  
workflow.add\_conditional\_edges(  
    "agent",  
    should\_continue,  
    {"continue": "action", "end": END}  
)  
workflow.add\_edge("action", "agent") \# Loop back to the agent to reason about the tool output  
agent\_graph\_app \= workflow.compile()

#### **C. Agent API Endpoint (app/api/v1/endpoints/agent.py)**

\# app/api/v1/endpoints/agent.py  
from fastapi import APIRouter  
from pydantic import BaseModel  
from app.core.agent import agent\_graph\_app

router \= APIRouter()

class AgentRequest(BaseModel):  
    input: str

class AgentResponse(BaseModel):  
    output: dict

@router.post("/invoke", response\_model=AgentResponse)  
async def invoke\_agent(request: AgentRequest):  
    """Invokes the core agent with a given input."""  
    inputs \= {"input": request.input, "chat\_history": \[\]}  
    final\_state \= {}  
    for s in agent\_graph\_app.stream(inputs):  
        final\_state \= s  
    return {"output": final\_state}

### **Phase 2: The Robust API Layer 🔌**

**Goal:** Implement and expose chat history functionality.

* **Tasks:** Implement chat\_history.py service and endpoints, define schemas, and provide API examples.

### **Phase 2 Elaboration: Chat History Implementation Details**

*This phase is fully specified with the code provided in the prompt.*

### **Phase 3: Advanced Agent Architecture 🧠**

**Goal:** Evolve the single agent into a sophisticated, multi-agent system capable of complex reasoning.

### **Phase 3 Elaboration: Implementation Details**

* **CrewAI Manager (app/core/crew\_manager.py):**  
  \# app/core/crew\_manager.py  
  from crewai import Agent, Task, Crew  
  from langchain\_openai import ChatOpenAI

  \# llm \= ChatOpenAI(model="gpt-4-turbo-preview") \# Or use Ollama

  class ResearchCrew:  
      def \_\_init\_\_(self, topic: str):  
          self.topic \= topic

      def run(self):  
          \# Define Agents  
          researcher \= Agent(  
              role='Senior Research Analyst',  
              goal=f'Uncover cutting-edge developments in {self.topic}',  
              backstory="You are a world-class research analyst...",  
              verbose=True,  
              \# llm=llm  
          )  
          writer \= Agent(  
              role='Professional Content Strategist',  
              goal=f'Craft a compelling and informative report on {self.topic}',  
              backstory="You are a renowned content strategist...",  
              verbose=True,  
              \# llm=llm  
          )  
          \# Define Tasks  
          research\_task \= Task(description=f"Identify the top 3 most significant trends in {self.topic} from the last year.", agent=researcher)  
          write\_task \= Task(description=f"Based on the research, write a 500-word report on the trends in {self.topic}.", agent=writer)

          \# Form the Crew  
          crew \= Crew(agents=\[researcher, writer\], tasks=\[research\_task, write\_task\], verbose=2)  
          result \= crew.kickoff()  
          return result

### **Phase 4: Data Infrastructure Overhaul 📊**

**Goal:** Implement a scalable, high-performance data infrastructure.

### **Phase 4 Elaboration: Implementation Details**

* **Vector Store Service (app/services/vector\_store.py):**  
  \# app/services/vector\_store.py  
  import os  
  from qdrant\_client import QdrantClient, models

  class VectorStoreService:  
      def \_\_init\_\_(self):  
          self.client \= QdrantClient(host=os.getenv("QDRANT\_HOST"), port=int(os.getenv("QDRANT\_PORT")))

      def create\_collection(self, collection\_name: str):  
          self.client.recreate\_collection(  
              collection\_name=collection\_name,  
              vectors\_config=models.VectorParams(size=1536, distance=models.Distance.COSINE), \# Example size for OpenAI  
          )

      def add\_documents(self, collection\_name: str, docs: list, embeddings: list, payloads: list):  
          self.client.upsert(  
              collection\_name=collection\_name,  
              points=models.Batch(  
                  ids=\[doc.id for doc in docs\],  
                  vectors=embeddings,  
                  payloads=payloads  
              )  
          )

      def search(self, collection\_name: str, query\_vector: list, limit: int \= 5):  
          return self.client.search(  
              collection\_name=collection\_name,  
              query\_vector=query\_vector,  
              limit=limit  
          )

### **Phase 5: Agent Orchestration & Scalability 🚀**

**Goal:** Implement a central orchestrator and asynchronous task execution.

### **Phase 5 Elaboration: Implementation Details**

* **Asynchronous Tasks (app/tasks.py):**  
  \# app/tasks.py  
  import os  
  from celery import Celery  
  from app.core.crew\_manager import ResearchCrew

  celery\_app \= Celery('tasks', broker=os.getenv("REDIS\_URL"), backend=os.getenv("REDIS\_URL"))  
  celery\_app.conf.update(task\_track\_started=True)

  @celery\_app.task(name="run\_research\_crew")  
  def run\_research\_crew\_task(topic: str) \-\> str:  
      crew \= ResearchCrew(topic)  
      result \= crew.run()  
      return result

* **Updated Orchestrator (app/core/orchestrator.py):**  
  \# Snippet showing update to app/core/orchestrator.py  
  from app.tasks import run\_research\_crew\_task

  \# ... inside Orchestrator.delegate\_task method ...  
  def delegate\_task(self, task\_type, payload):  
      \# ...  
      if task\_type \== "research\_topic":  
          task\_result \= run\_research\_crew\_task.delay(payload\["topic"\])  
          confirmation\["task\_id"\] \= task\_result.id  
          confirmation\["status"\] \= "Task has been dispatched for asynchronous execution."  
      \# ...  
      return confirmation

### **Phase 6: API Modernization & Real-time Communication 🌐**

**Goal:** Modernize the API architecture for maximum flexibility and performance.

### **Phase 6 Elaboration: Implementation Details**

* **GraphQL with Strawberry (app/api/v1/graphql/schema.py):**  
  \# app/api/v1/graphql/schema.py  
  import strawberry  
  import typing  
  from app.api.v1 import schemas as rest\_schemas

  @strawberry.type  
  class Message:  
      role: str  
      content: str

  @strawberry.type  
  class Conversation:  
      id: strawberry.ID  
      messages: typing.List\[Message\]

  @strawberry.type  
  class Query:  
      @strawberry.field  
      def conversation(self, id: strawberry.ID) \-\> Conversation:  
          \# Logic to fetch conversation from DB and map to GraphQL type  
          \# db\_convo \= get\_conversation(db, id)  
          \# return Conversation(...)  
          return Conversation(id=id, messages=\[Message(role="user", content="Hello\!")\])

  graphql\_schema \= strawberry.Schema(query=Query)

  *This would be added to main.py with app.add\_route("/graphql", GraphQL(graphql\_schema))*

### **Phase 7: The Multi-Modal Revolution 🎬🎙️**

**Goal:** Integrate specialized models and tools for audio and video analysis.

### **Phase 7 Elaboration: Implementation Details**

* **Multi-modal Tool (app/core/tools.py):**  
  \# Addition to app/core/tools.py  
  import ffmpeg  
  import whisper  
  import os

  def transcribe\_video\_audio(video\_path: str) \-\> str:  
      """  
      Extracts audio from a video file and transcribes it using Whisper.  
      This is a long-running task and should be run in a Celery worker.  
      """  
      if not os.path.exists(video\_path):  
          return "Error: Video file not found."

      audio\_output \= "temp\_audio.aac"  
      try:  
          \# Use ffmpeg-python to extract audio  
          (  
              ffmpeg  
              .input(video\_path)  
              .output(audio\_output, acodec='copy', loglevel='quiet')  
              .run(overwrite\_output=True)  
          )

          \# Use Whisper model to transcribe  
          model \= whisper.load\_model("base")  
          result \= model.transcribe(audio\_output)

          return result\["text"\]  
      except ffmpeg.Error as e:  
          return f"FFmpeg error: {e.stderr.decode()}"  
      finally:  
          \# Cleanup temp file  
          if os.path.exists(audio\_output):  
              os.remove(audio\_output)

### **Phase 8: Developer Enablement & Documentation 📖**

**Goal:** Create comprehensive documentation and resources for developers.

### **Phase 8 Elaboration: Implementation Details**

* **"Getting Started" Guide (docs/getting\_started.md):**  
  \# Getting Started with the gremlinsAI API

  Welcome\! This guide will walk you through making your first API call to our agent.

  \#\# 1\. Get Your API Key

  First, you'll need an API key. Please contact support to be issued a key.

  \#\# 2\. Set Up Your Environment

  Make sure you have \`requests\` installed:  
  \`pip install requests\`

  \#\# 3\. Make Your First Request

  Use the following Python script to invoke our agent. Replace \`YOUR\_API\_KEY\` with the key you received.

  \`\`\`python  
  import requests

  API\_URL \= "http://localhost:8000/api/v1/agent/invoke"  
  API\_KEY \= "YOUR\_API\_KEY" \# Note: Auth not yet implemented, but this is best practice

  headers \= {  
      \# "Authorization": f"Bearer {API\_KEY}"  
  }

  payload \= {  
      "input": "What are the latest advancements in AI?"  
  }

  response \= requests.post(API\_URL, headers=headers, json=payload)

  if response.status\_code \== 200:  
      print("Success:")  
      print(response.json())  
  else:  
      print(f"Error {response.status\_code}:")  
      print(response.text)

## **IMMEDIATE ACTION REQUIRED**

This document now provides a complete, end-to-end blueprint. The immediate focus is to create the file structure and code for **all phases** as detailed in their respective "Elaboration" sections. The plan is fully specified and ready for implementation.