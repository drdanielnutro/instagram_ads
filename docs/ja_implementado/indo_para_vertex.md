Gemini Fullstack Agent Development Kit (ADK) Quickstart
The Gemini Fullstack Agent Development Kit (ADK) Quickstart is a production-ready blueprint for building a sophisticated, fullstack research agent with Gemini. It's built to demonstrate how the ADK helps structure complex agentic workflows, build modular agents, and incorporate critical Human-in-the-Loop (HITL) steps.

Key Features
🏗️	Fullstack & Production-Ready: A complete React frontend and ADK-powered FastAPI backend, with deployment options for Google Cloud Run and Vertex AI Agent Engine.
🧠	Advanced Agentic Workflow: The agent uses Gemini to strategize a multi-step plan, reflect on findings to identify gaps, and synthesize a final, comprehensive report.
🔄	Iterative & Human-in-the-Loop Research: Involves the user for plan approval, then autonomously loops through searching (via Gemini function calling) and refining its results until it has gathered sufficient information.
Here is the agent in action:

Gemini Fullstack ADK Preview


This project adapts concepts from the Gemini FullStack LangGraph Quickstart for the frontend app.

🚀 Getting Started: From Zero to Running Agent in 1 Minute
Prerequisites: Python 3.10+, Node.js, uv

You have two options to get started. Choose the one that best fits your setup:

A. Google AI Studio: Choose this path if you want to use a Google AI Studio API key. This method involves cloning the sample repository.
B. Google Cloud Vertex AI: Choose this path if you want to use an existing Google Cloud project for authentication. This method generates a new, prod-ready project using the agent-starter-pack including all the deployment scripts required.
A. Google AI Studio
You'll need a Google AI Studio API Key.

Step 1: Clone Repository
Clone the repository and cd into the project directory.

git clone https://github.com/google/adk-samples.git
cd adk-samples/python/agents/gemini-fullstack
Step 2: Set Environment Variables
Create a .env file in the app folder by running the following command (replace YOUR_AI_STUDIO_API_KEY with your actual API key):

echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_API_KEY" >> app/.env
Step 3: Install & Run
From the gemini-fullstack directory, install dependencies and start the servers.

make install && make dev
Your agent is now running at http://localhost:5173.

B. Google Cloud Vertex AI
You'll also need: Google Cloud SDK and a Google Cloud Project with the Vertex AI API enabled.

Step 1: Create Project from Template
This command uses the Agent Starter Pack to create a new directory (my-fullstack-agent) with all the necessary code.

# Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate # On Windows: .venv\Scripts\activate

# Install the starter pack and create your project
pip install --upgrade agent-starter-pack
agent-starter-pack create my-fullstack-agent -a adk@gemini-fullstack
⚡️ Alternative: Using uv
You'll be prompted to select a deployment option (Agent Engine or Cloud Run) and verify your Google Cloud credentials.

Step 2: Install & Run
Navigate into your newly created project folder, then install dependencies and start the servers.

cd my-fullstack-agent && make install && make dev
Your agent is now running at http://localhost:5173.

☁️ Cloud Deployment
Note: The cloud deployment instructions below apply only if you chose the Google Cloud Vertex AI option.

You can quickly deploy your agent to a development environment on Google Cloud. You can deploy your latest code at any time with:

# Replace YOUR_DEV_PROJECT_ID with your actual Google Cloud Project ID
gcloud config set project YOUR_DEV_PROJECT_ID
make backend
For robust, production-ready deployments with automated CI/CD, please follow the detailed instructions in the Agent Starter Pack Development Guide.

Agent Details
Attribute	Description
Interaction Type	Workflow
Complexity	Advanced
Agent Type	Multi Agent
Components	Multi-agent, Function calling, Web search, React frontend, Human-in-the-Loop
Vertical	Horizontal
How the Agent Thinks: A Two-Phase Workflow
The backend agent, defined in app/agent.py, follows a sophisticated workflow to move from a simple topic to a fully-researched report.

The following diagram illustrates the agent's architecture and workflow:

ADK Gemini Fullstack Architecture

This process is broken into two main phases:

Phase 1: Plan & Refine (Human-in-the-Loop)
This is the collaborative brainstorming phase.

You provide a research topic.
The agent generates a high-level research plan with several key goals (e.g., "Analyze the market impact," "Identify key competitors").
The plan is presented to you. You can approve it, or chat with the agent to add, remove, or change goals until you're satisfied. Nothing happens without your explicit approval.
The plan will contains following tags as a signal to downstream agents,

Research Plan Tags

[RESEARCH]: Guides info gathering via search.
[DELIVERABLE]: Guides creation of final outputs (e.g., tables, reports).
Plan Refinement Tags

[MODIFIED]: Goal was updated.
[NEW]: New goal added per user.
[IMPLIED]: Deliverable proactively added by AI.
Phase 2: Execute Autonomous Research
Once you approve the plan, the agent's research_pipeline takes over and works autonomously.

Outlining: It first converts the approved plan into a structured report outline (like a table of contents).
Iterative Research & Critique Loop: For each section of the outline, it repeats a cycle:
Search: It performs web searches to gather information.
Critique: A "critic" model evaluates the findings for gaps or weaknesses.
Refine: If the critique finds weaknesses, the agent generates more specific follow-up questions and searches again. This loop continues until the research meets a high-quality bar.
Compose Final Report: After the research loop is complete, a final agent takes all the verified findings and writes a polished report, automatically adding inline citations that link back to the original sources.
You can edit key parameters (Gemini models, research loop iterations) in the ResearchConfiguration dataclass within app/config.py.

Customization
You can modify and extend this agent's behavior by editing the backend code.

Modifying Agent Logic: The core logic for all sub-agents (planner, researcher, critic, composer) is defined in app/agent.py. You can change the prompts, tools, or reasoning steps by modifying the agent definitions here.

Adjusting Research Parameters: Key parameters, such as the Gemini models used or the number of research loop iterations, can be adjusted in the ResearchConfiguration dataclass within app/config.py.

Syncing with Frontend: The frontend UI integrates with the backend through specific agent names that process outputs differently (e.g., research findings vs. final report), update the activity timeline with appropriate titles/icons, and track research metrics like website counts. Important agent names include:

section_researcher & enhanced_search_executor - track websites consulted
report_composer_with_citations - processes final report
interactive_planner_agent - updates AI messages during planning
plan_generator and section_planner - used for timeline labels
If you rename agents in app/agent.py, you must update their names in the frontend code (/ui) to maintain functionality.

Example Interaction
User: A report on the last Google I/O

Agent: Here's a research plan for a report on the last Google I/O:

Analyze the key announcements and product updates made at Google I/O 2025.
Identify the central themes and strategic directions emphasized by Google during the event, particularly concerning AI, Android, and other emerging technologies like Android XR.
Investigate the reception and industry impact of the major product unveilings and feature enhancements.
Examine any significant shifts or continuities in Google's developer strategy as presented at the conference.
Assess the implications of the announced technologies and initiatives for developers, consumers, and the broader tech landscape.
Does this plan look good, or would you like to refine it further? Once approved, I can initiate the research.

User: Looks good! (The agent proceeds to autonomously execute the research, showing its progress on the timeline.)

Agent:

Google I/O 2025: Key Announcements and Highlights ....

Troubleshooting
If you encounter issues while setting up or running this agent, here are some resources to help you troubleshoot:

ADK Documentation: Comprehensive documentation for the Agent Development Kit
Vertex AI Authentication Guide: Detailed instructions for setting up authentication
Agent Starter Pack Troubleshooting: Common issues
🛠️ Technologies Used
Backend
Agent Development Kit (ADK): The core framework for building the stateful, multi-turn agent.
FastAPI: High-performance web framework for the backend API.
Google Gemini: Used for planning, reasoning, search query generation, and final synthesis.
Frontend
React (with Vite): For building the interactive user interface.
Tailwind CSS: For utility-first styling.
Shadcn UI: A set of beautifully designed, accessible components.
Disclaimer
This agent sample is provided for illustrative purposes only. It serves as a basic example of an agent and a foundational starting point for individuals or teams to develop their own agents.

Users are solely responsible for any further development, testing, security hardening, and deployment of agents based on this sample. We recommend thorough review, testing, and the implementation of appropriate safeguards before using any derived agent in a live or critical system.