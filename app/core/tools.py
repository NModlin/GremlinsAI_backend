# app/core/tools.py
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel, Field

# Initialize the tool. This can be reused across the application.
search_tool = DuckDuckGoSearchRun()

class SearchInput(BaseModel):
    query: str = Field(description="The search query to execute.")

def duckduckgo_search(query: str) -> str:
    """
    A wrapper for the DuckDuckGo Search tool to be used by agents.
    It takes a query string and returns the search results.
    """
    print(f"--- Executing search for: {query} ---")
    return search_tool.invoke(query)

# In later phases, more tools will be added here.
# Example:
# def transcribe_video_audio(video_path: str) -> str: ...
