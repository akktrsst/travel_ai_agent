import streamlit as st
import os
from crewai import Agent
from langchain_openai import ChatOpenAI
from TravelTools import SearchTool
import re
from dotenv import load_dotenv
from crewai_tools import tool
load_dotenv()
api_key=os.environ.get('OPENAI_API_KEY')
# print(api_key)
# AGENTS
class TravelAgents():
    
    # LLM Setting
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.environ.get('OPENAI_API_KEY'))
    
    # Agent city expert
    def location_expert(self):
        return Agent(
            role="Travel Trip Expert",
            goal="Adapt to the user destination city language (Gather helpful information about to the city and city during travel.",
            backstory="""A seasoned traveler who has explored various destinations and knows the ins and outs of travel logistics.""",
            tools=[SearchTool.search_web_tool],
            verbose=True,
            max_iter=5,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.environ.get('OPENAI_API_KEY')),
            allow_delegation=False,
            # step_callback=streamlit_callback,
            )
    
    # Agent Resercher
    def guide_expert(self):
        return Agent( 
            role="City Local Guide Expert",
            goal="Provides information on things to do in the city based on the user's interests.",
            backstory="""A local expert with a passion for sharing the best experiences and hidden gems of their city.""",
            tools=[SearchTool.search_web_tool],
            verbose=True,
            max_iter=5,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=os.environ.get('OPENAI_API_KEY')),
            allow_delegation=False,
            # step_callback=streamlit_callback,
            )
    
    # Agent Resercher
    def planner_expert(self):
        return Agent(
            role="Travel Planning Expert",
            goal="Compiles all gathered information to provide a comprehensive travel plan.",
            backstory="""
            You are a professional guide with a passion for travel.
            An organizational wizard who can turn a list of possibilities into a seamless itinerary.
            """,
            tools=[SearchTool.search_web_tool],
            verbose=True,
            max_iter=5,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.environ.get('OPENAI_API_KEY')),
            allow_delegation=False,
            # step_callback=streamlit_callback,
            )

    # Agent for budget-friendly planning
    def budget_expert(self):
        return Agent(
            role="Budget Travel Expert",
            goal="Optimize the travel plan for cost-effectiveness, best deals, and group savings based on the user's budget and number of people.",
            backstory="""
            A savvy traveler and deal hunter who specializes in finding the best value for money, discounts, and group offers for travel, accommodation, and activities.
            """,
            tools=[SearchTool.search_web_tool],
            verbose=True,
            max_iter=5,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.environ.get('OPENAI_API_KEY')),
            allow_delegation=False,
        )

class StreamToExpander:
    # Print agent process to Streamlit app container 
    # This portion of the code is adapted from @AbubakrChan; thank you!  
    
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.colors = ['red', 'green', 'blue', 'orange']  # Define a list of colors
        self.color_index = 0  # Initialize color index

    def write(self, data):
        # Filter out ANSI escape codes using a regular expression
        cleaned_data = re.sub(r'\x1B\[[0-9;]*[mK]', '', data)

        # Check if the data contains 'task' information
        task_match_object = re.search(r'\"task\"\s*:\s*\"(.*?)\"', cleaned_data, re.IGNORECASE)
        task_match_input = re.search(r'task\s*:\s*([^\n]*)', cleaned_data, re.IGNORECASE)
        task_value = None
        if task_match_object:
            task_value = task_match_object.group(1)
        elif task_match_input:
            task_value = task_match_input.group(1).strip()

        if task_value:
            st.toast(":robot_face: " + task_value)

        # Check if the text contains the specified phrase and apply color
        if "Entering new CrewAgentExecutor chain" in cleaned_data:
            # Apply different color and switch color index
            self.color_index = (self.color_index + 1) % len(self.colors)  # Increment color index and wrap around if necessary

            cleaned_data = cleaned_data.replace("Entering new CrewAgentExecutor chain", f":{self.colors[self.color_index]}[Entering new CrewAgentExecutor chain]")

        if "City Selection Expert" in cleaned_data:
            # Apply different color 
            cleaned_data = cleaned_data.replace("City Selection Expert", f":{self.colors[self.color_index]}[City Selection Expert]")
        if "Local Expert at this city" in cleaned_data:
            cleaned_data = cleaned_data.replace("Local Expert at this city", f":{self.colors[self.color_index]}[Local Expert at this city]")
        if "Amazing Travel Concierge" in cleaned_data:
            cleaned_data = cleaned_data.replace("Amazing Travel Concierge", f":{self.colors[self.color_index]}[Amazing Travel Concierge]")
        if "Finished chain." in cleaned_data:
            cleaned_data = cleaned_data.replace("Finished chain.", f":{self.colors[self.color_index]}[Finished chain.]")

        self.buffer.append(cleaned_data)
        if "\n" in data:
            self.expander.markdown(''.join(self.buffer), unsafe_allow_html=True)
            self.buffer = []
