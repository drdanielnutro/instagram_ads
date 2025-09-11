# 🤖 FACILITADOR - Flutter Code Generation Agent System

## 🎯 Project Overview

**FACILITADOR** is an advanced multi-agent AI system built on Google ADK v1.4.2 that automates Flutter application feature development through intelligent code generation pipelines.

**Core Technology**: Python 3.10+ | FastAPI | Google ADK | Gemini 2.5 | GCP

**Mission**: Transform feature descriptions into production-ready Flutter code with automated quality assurance.

## 📚 PRIMARY KNOWLEDGE SOURCE - GEMINI.md

### ⚡ CRITICAL INSTRUCTION - READ FIRST

**THE GEMINI.md FILE IS YOUR ULTIMATE SOURCE OF TRUTH FOR ALL ADK-RELATED QUESTIONS**

Before making ANY assumptions about Google ADK functionality, architecture, or best practices:

```bash
# ALWAYS consult GEMINI.md first
cat GEMINI.md | grep -A 20 "your_topic"  # Quick search
less GEMINI.md                            # Full browse
```

### 📖 GEMINI.md Quick Reference Guide

The `GEMINI.md` file (1531 lines) contains the complete ADK Python Cheatsheet. Use these section mappings:

```yaml
ADK_KNOWLEDGE_MAP:
  Core_Concepts:
    location: "Section 1: Core Concepts & Project Structure"
    use_when: "Understanding ADK principles, project layout"
    
  Agent_Development:
    LlmAgent: "Section 2: Agent Definitions"
    Orchestration: "Section 3: Orchestration with Workflow Agents"
    Custom_Agents: "Section 5: Building Custom Agents (BaseAgent)"
    Multi_Agent: "Section 4: Multi-Agent Systems & Communication"
    
  Model_Configuration:
    Gemini: "Section 6.1: Google Gemini Models"
    Vertex_AI: "Section 6.1: AI Studio & Vertex AI"
    LiteLLM: "Section 6.2-6.3: Other Models via LiteLLM"
    
  Tools_and_Functions:
    Definition: "Section 7.1: Defining Function Tools"
    ToolContext: "Section 7.2: The ToolContext Object"
    All_Types: "Section 7.3: All Tool Types & Usage"
    
  State_Management:
    Session: "Section 8.1: The Session Object"
    State: "Section 8.2: State - Conversational Scratchpad"
    Memory: "Section 8.3: Memory - Long-Term Knowledge"
    Artifacts: "Section 8.4: Artifacts - Binary Data"
    
  Runtime_and_Events:
    Runner: "Section 9.1: The Runner"
    Event_Loop: "Section 9.2: The Event Loop"
    Events: "Section 9.3: Event Object"
    Async: "Section 9.4: Asynchronous Programming"
    
  Advanced_Topics:
    Callbacks: "Section 10: Control Flow with Callbacks"
    Authentication: "Section 11: Authentication for Tools"
    Deployment: "Section 12: Deployment Strategies"
    Evaluation: "Section 13: Evaluation and Safety"
    Debugging: "Section 14: Debugging, Logging & Observability"
    Performance: "Section 16: Performance Optimization"
    Best_Practices: "Section 17: General Best Practices"
```

### 🔍 When to Consult GEMINI.md

**MUST CONSULT** for these scenarios:
1. **Creating new agents** → Section 2-5
2. **Modifying pipelines** → Section 3 (Orchestration)
3. **Adding tools/functions** → Section 7
4. **State management changes** → Section 8
5. **Callback implementation** → Section 10
6. **Model configuration** → Section 6
7. **Deployment questions** → Section 12
8. **ANY uncertainty about ADK** → Search entire document

**Example Workflow**:
```python
# Before implementing any ADK feature:
# 1. Search GEMINI.md for the topic
# 2. Read the relevant section completely
# 3. Copy the example code pattern
# 4. Adapt to project needs
# 5. Test thoroughly
```

## 🚀 Quick Start Commands

```bash
# Development Environment
source .venv/bin/activate           # Activate virtual environment
uv sync                             # Sync dependencies with uv
python run_agent.py                 # Run agent locally

# Testing
pytest tests/ -v                    # Run all tests
pytest tests/test_agent.py -k "test_pipeline"  # Specific test

# Server Operations  
uvicorn app.server:app --reload --port 8000    # Dev server
make run-local                      # Run with Makefile

# Google Cloud Operations
gcloud auth login                   # Authenticate GCP
gcloud config set project [PROJECT_ID]  # Set project
export GOOGLE_CLOUD_PROJECT=[PROJECT_ID]  # Set env var

# AI Studio Mode (Alternative to Vertex AI)
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export GOOGLE_API_KEY=[YOUR_KEY]

# ADK Reference Commands
grep -n "SequentialAgent" GEMINI.md  # Find orchestration patterns
grep -n "LlmAgent" GEMINI.md        # Find agent patterns
grep -n "tools" GEMINI.md           # Find tool patterns
```

## 📋 CRITICAL RULES (YOU MUST FOLLOW)

### 🔴 ABSOLUTE IMPERATIVES
- **NEVER** modify files in `.venv/`, `uv.lock`, or `__pycache__/`
- **NEVER** edit Google ADK internal files or Gemini SDK code
- **NEVER** commit API keys or credentials (check `.env` files)
- **NEVER** change the agent pipeline structure without architectural review
- **NEVER** make ADK assumptions without checking GEMINI.md first
- **ALWAYS** use `uv` for dependency management, NOT pip directly
- **ALWAYS** run tests before modifying agent.py core logic
- **ALWAYS** preserve the 5-stage pipeline architecture
- **ALWAYS** consult GEMINI.md for ADK patterns before implementing

### ⚠️ Agent Development Rules
- **BEFORE** creating new agents: Read GEMINI.md Section 2 AND existing agent.py patterns
- **WHEN** modifying pipelines: Check GEMINI.md Section 3 for orchestration patterns
- **IF** changing models: Consult GEMINI.md Section 6, then update config.py
- **ASK** before modifying: LoopAgent/SequentialAgent configurations (check GEMINI.md Section 3)

### 📖 Documentation Consultation Protocol
```python
# MANDATORY WORKFLOW for ANY ADK-related task:
def before_any_adk_work(task_description: str):
    """Protocol for ADK development tasks."""
    
    # Step 1: Identify ADK component
    component = identify_component(task_description)
    
    # Step 2: Find in GEMINI.md
    section = ADK_KNOWLEDGE_MAP[component]
    
    # Step 3: Read complete section
    knowledge = read_gemini_section(section)
    
    # Step 4: Extract pattern
    pattern = extract_code_pattern(knowledge)
    
    # Step 5: Validate with existing code
    validate_against_current_implementation(pattern)
    
    # Step 6: Implement with confidence
    return implement_with_pattern(pattern)
```

## 🏗️ Architecture & File Structure

```
facilitador/
├── GEMINI.md                    # 📚 [SOURCE OF TRUTH] Complete ADK reference
├── app/                          # [CORE - Handle with care]
│   ├── agent.py                 # ⚡ CRITICAL: Main pipeline (1040+ lines)
│   ├── server.py                # FastAPI server configuration
│   ├── config.py                # Agent configuration & models
│   └── utils/                   # Utilities
│       ├── gcs.py              # GCS bucket operations
│       ├── tracing.py          # OpenTelemetry setup
│       └── typing.py           # Pydantic models
├── frontend/                    # [CAN MODIFY] Streamlit UI
├── deployment/                  # [CAN MODIFY] Deploy scripts
├── tests/                       # [CAN MODIFY] Test suite
├── notebooks/                   # [CAN MODIFY] Experiments
├── .env                        # [NEVER COMMIT] Credentials
└── pyproject.toml              # [CAREFUL] Dependencies
```

### File Modification Boundaries with ADK Context
```yaml
CAN_MODIFY:
  - frontend/**/*          # UI improvements
  - tests/**/*            # Test additions
  - notebooks/**/*        # Experimentation
  - deployment/scripts/*  # Deploy automation
  - docs/**/*            # Documentation

MODIFY_WITH_CAUTION:
  - app/agent.py         # Check GEMINI.md Section 2-4 first
  - app/server.py        # Check GEMINI.md Section 12 for deployment
  - app/config.py        # Check GEMINI.md Section 6 for models
  - pyproject.toml       # Use 'uv add', not manual edits

NEVER_TOUCH:
  - .venv/**/*           # Virtual environment
  - uv.lock              # Lock file (auto-generated)
  - .git/**/*            # Git internals
  - __pycache__/**/*     # Python cache
  - *.pyc                # Compiled Python
  
READ_ONLY_REFERENCE:
  - GEMINI.md            # ADK knowledge base (never edit, only read)
```

## 🎨 Code Style & Standards

### Python Code Conventions (ADK-Aligned)

```python
# ✅ GOOD: Following GEMINI.md patterns (Section 2.1)
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ImplementationTask(BaseModel):
    """Model for a single implementation task (per GEMINI.md Section 7.1)."""
    id: str = Field(description="Unique identifier")
    category: Literal["MODEL", "PROVIDER", "WIDGET"]
    
    def execute(self, context: ToolContext) -> Dict[str, Any]:
        """Execute with ToolContext as per GEMINI.md Section 7.2."""
        try:
            # Access runtime info via context
            session = context.session
            state = session.state
            
            result = self._process(state)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Task {self.id} failed: {e}")
            raise

# ❌ BAD: Not following ADK patterns
class task:
    def do_something(self, data):
        # Missing ToolContext, no types, poor structure
        try:
            return data
        except:
            print("error")
```

### Agent Pipeline Patterns (From GEMINI.md Section 3)

```python
# ✅ GOOD: Structured pipeline following GEMINI.md orchestration
from google.adk.agents import SequentialAgent, LoopAgent

# Based on GEMINI.md Section 3.1: Sequential Execution
sequential_agent = SequentialAgent(
    name="flutter_pipeline",
    jobs=[
        analyze_context_agent,    # Step 1
        create_plan_agent,        # Step 2
        LoopAgent(               # Step 3: Iterative (Section 3.3)
            name="implementation_loop",
            loop_job=code_generation_agent,
            max_iterations=config.max_task_iterations,
            post_job_callback=collect_code_snippets_callback  # Section 10
        ),
        assembly_agent           # Step 4
    ],
    enable_logging=config.enable_detailed_logging
)

# ❌ BAD: Not using ADK orchestration patterns
agent = Agent()
agent.run(data)  # No structure, no patterns from GEMINI.md
```

## 🧪 Testing Strategy

### Test-Driven Development for ADK Agents

```bash
# Following GEMINI.md Section 13: Evaluation patterns

# 1. Create evaluation dataset (per GEMINI.md)
cat > tests/integration/facilitador.evalset.json << 'EOF'
{
  "eval_name": "Flutter Generation Test",
  "agents": ["facilitador"],
  "examples": [
    {
      "input": "Create login state with Riverpod",
      "expected_output": "StateNotifier implementation"
    }
  ]
}
EOF

# 2. Run ADK evaluation (GEMINI.md Section 13.1)
adk eval tests/integration/facilitador.evalset.json

# 3. For unit tests, follow patterns from GEMINI.md
pytest tests/ --cov=app
```

### Integration Testing with Gemini (Per GEMINI.md Section 6)

```python
# Pattern from GEMINI.md for mocking Gemini calls
from unittest.mock import patch
from google.genai import types as genai_types

@patch('google.genai.models.GenerativeModel')
def test_pipeline_with_mock_llm(mock_model):
    """Test following GEMINI.md mocking patterns."""
    # Configure mock per GEMINI.md Section 6.1
    mock_response = genai_types.GenerateContentResponse(...)
    mock_model.return_value.generate_content.return_value = mock_response
    
    # Test your pipeline
    result = sequential_agent.run_async(...)
    assert result.success
```

## 🔒 Security & API Management

### Environment Configuration (GEMINI.md Section 6.1)

```bash
# For Vertex AI (Production) - per GEMINI.md
export GOOGLE_GENAI_USE_VERTEXAI=True
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1

# For AI Studio (Development) - per GEMINI.md
export GOOGLE_GENAI_USE_VERTEXAI=False
export GOOGLE_API_KEY=your-api-key  # NEVER commit
```

## 🔄 Git Workflow

### Branch Strategy with ADK Context

```bash
# Feature development
git checkout -b feature/agent-improvement

# Before committing agent changes, verify against GEMINI.md
grep -n "your_pattern" GEMINI.md  # Verify you followed patterns

git add app/agent.py tests/
git commit -m "feat(agent): add retry logic per GEMINI.md Section 10"

# Reference GEMINI.md sections in commits when applicable
git commit -m "fix(pipeline): fix LoopAgent per GEMINI.md 3.3"
```

## 🎯 Development Workflows

### Workflow 1: Adding New Agent Capability (ADK-Guided)

```bash
# 1. RESEARCH: Check GEMINI.md for patterns
grep -n "LlmAgent\|output_schema" GEMINI.md
# Read Section 2.2 for advanced configuration

# 2. EXPLORE: Understand current implementation
grep -n "SequentialAgent\|LoopAgent" app/agent.py

# 3. PLAN: Design based on GEMINI.md patterns
echo "Plan: Add structured output per GEMINI.md Section 2.2"
echo "1. Define Pydantic model (Section 7.1)"
echo "2. Add output_schema to agent (Section 2.2)"
echo "3. Update callbacks (Section 10)"

# 4. IMPLEMENT: Follow GEMINI.md examples exactly
# Copy pattern from GEMINI.md, adapt to your needs

# 5. VALIDATE: Use ADK eval (Section 13)
adk eval tests/integration/new_capability.evalset.json
```

### Workflow 2: Debugging Pipeline Issues (With GEMINI.md)

```python
# Based on GEMINI.md Section 14: Debugging & Observability

# Enable detailed logging per GEMINI.md
config.enable_detailed_logging = True

# Add debug callback (GEMINI.md Section 10.2)
from google.adk.agents.callback_context import CallbackContext

def debug_callback(callback_context: CallbackContext) -> None:
    """Debug callback per GEMINI.md Section 10 patterns."""
    session = callback_context._invocation_context.session
    print(f"Stage: {callback_context.agent_name}")
    print(f"State keys: {callback_context.state.keys()}")
    print(f"Events count: {len(session.events)}")
    
# Attach per GEMINI.md callback patterns
problem_agent.post_job_callback = debug_callback
```

### Workflow 3: Implementing Custom Tools (GEMINI.md Section 7)

```python
# STEP 1: Read GEMINI.md Section 7 completely
# STEP 2: Follow the FunctionTool pattern

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def my_custom_tool(
    param1: str,
    param2: int,
    context: ToolContext  # GEMINI.md Section 7.2 requirement
) -> dict:
    """Custom tool following GEMINI.md patterns."""
    # Access session via context
    session = context.session
    current_state = session.state
    
    # Tool implementation
    result = process_data(param1, param2)
    
    # Update state if needed
    session.state["tool_result"] = result
    
    return {"status": "success", "result": result}

# Register as per GEMINI.md
custom_tool = FunctionTool(my_custom_tool)
```

### Workflow 4: Multi-Agent Communication (GEMINI.md Section 4)

```python
# Before implementing, read GEMINI.md Section 4 entirely

# Pattern from GEMINI.md Section 4.2: Inter-Agent Communication
from google.adk.agents import LlmAgent

# Producer agent (GEMINI.md pattern)
producer = LlmAgent(
    name="producer",
    model="gemini-2.5-flash",
    output_key="produced_data",  # Saves to state
    instruction="Generate data and save to state"
)

# Consumer agent (GEMINI.md pattern)  
consumer = LlmAgent(
    name="consumer",
    model="gemini-2.5-flash",
    instruction="Process the data from {produced_data}",  # Reads from state
    output_key="final_result"
)

# Orchestrate per GEMINI.md Section 3.1
pipeline = SequentialAgent(
    name="producer_consumer_pipeline",
    jobs=[producer, consumer]
)
```

## 🚨 Troubleshooting Guide (Enhanced with GEMINI.md)

### Problem: "Pipeline hangs at code generation"

```bash
# Solution 1: Check GEMINI.md Section 3.3 for LoopAgent limits
grep -n "max_iterations" GEMINI.md
# Apply the pattern found

# Solution 2: Check GEMINI.md Section 9 for timeout patterns
grep -n "timeout\|async" GEMINI.md

# Solution 3: Enable debug per GEMINI.md Section 14
export ADK_DEBUG=true
```

### Problem: "Agent not using tools correctly"

```bash
# Consult GEMINI.md Section 7 immediately
less +/Tools GEMINI.md

# Verify tool definition matches GEMINI.md patterns
# Check ToolContext usage (Section 7.2)
# Ensure function signatures match examples
```

### Problem: "State not persisting between agents"

```bash
# Read GEMINI.md Section 8 completely
grep -n "Session\|State\|Memory" GEMINI.md

# Common solution from GEMINI.md:
# Use output_key and proper state management
```

### Problem: "Deployment failing"

```bash
# GEMINI.md Section 12 has complete deployment guide
grep -n "Deployment\|Cloud Run\|Vertex" GEMINI.md

# Follow the exact deployment pattern for your target
```

## 📊 Performance Monitoring (Per GEMINI.md Section 16)

### Implementing ADK Metrics

```python
# Based on GEMINI.md Section 16: Performance Optimization
import time
from dataclasses import dataclass
from google.adk.agents.invocation_context import InvocationContext

@dataclass
class PipelineMetrics:
    """Metrics following GEMINI.md patterns."""
    total_time: float
    tasks_completed: int
    review_iterations: int
    tokens_used: int
    success_rate: float
    events_generated: int  # Per GEMINI.md Section 9.3
    
def track_metrics(context: InvocationContext) -> PipelineMetrics:
    """Track metrics per GEMINI.md Section 14 & 16."""
    session = context.session
    events = session.events
    
    return PipelineMetrics(
        total_time=time.time() - context.start_time,
        tasks_completed=len(context.state.get("completed_tasks", [])),
        review_iterations=context.state.get("review_count", 0),
        tokens_used=calculate_token_usage(events),
        success_rate=calculate_success_rate(events),
        events_generated=len(events)
    )
```

## 🔧 Advanced Configuration (GEMINI.md-Aligned)

### Model Configuration (GEMINI.md Section 6)

```python
# Following GEMINI.md Section 6.1 for Gemini configuration
from google.genai import types as genai_types

# Per GEMINI.md Section 2.2: Advanced LlmAgent Configuration
gen_config = genai_types.GenerateContentConfig(
    temperature=0.2,          # GEMINI.md recommended for deterministic
    top_p=0.9,               # Per GEMINI.md Section 6
    top_k=40,                # Standard per GEMINI.md
    max_output_tokens=1024,  # Adjust per use case
    stop_sequences=["## END"] # Custom stop per GEMINI.md
)

# Task-specific models per GEMINI.md patterns
TASK_MODEL_MAPPING = {
    "MODEL": "gemini-2.5-flash",      # Fast per GEMINI.md
    "WIDGET": "gemini-2.5-pro",       # Quality per GEMINI.md
    "SERVICE": "gemini-2.5-pro",      # Critical per GEMINI.md
    "PROVIDER": "gemini-2.5-flash",   # Balance per GEMINI.md
}
```

### Callback Configuration (GEMINI.md Section 10)

```python
# Following GEMINI.md Section 10: Control Flow with Callbacks

from google.adk.agents.callback_context import CallbackContext

# Pre-job callback (GEMINI.md Section 10.2)
def pre_job_callback(context: CallbackContext) -> None:
    """Pre-execution per GEMINI.md patterns."""
    logger.info(f"Starting {context.agent_name}")
    context.state["start_time"] = time.time()

# Post-job callback (GEMINI.md Section 10.2)
def post_job_callback(context: CallbackContext) -> None:
    """Post-execution per GEMINI.md patterns."""
    duration = time.time() - context.state["start_time"]
    logger.info(f"Completed {context.agent_name} in {duration}s")
    
# Error callback (GEMINI.md pattern)
def error_callback(context: CallbackContext, error: Exception) -> None:
    """Error handling per GEMINI.md."""
    logger.error(f"Error in {context.agent_name}: {error}")
    # Implement retry logic per GEMINI.md Section 17
```

## 📝 Project-Specific Guidelines

### Flutter Code Generation Standards
- Always use Riverpod for state management
- Include Freezed annotations for models
- Generate comprehensive error handling
- Add widget tests for UI components
- Follow Material Design guidelines

### ADK Agent Best Practices (From GEMINI.md Section 17)
- Keep agents focused (single responsibility)
- Use callbacks for state management (Section 10)
- Implement proper error boundaries
- Log all critical decisions (Section 14)
- Version your prompts
- **ALWAYS verify patterns against GEMINI.md**

### GCP Integration Requirements
- Use regional buckets (southamerica-east1)
- Enable Cloud Logging for all agents
- Implement trace correlation IDs
- Monitor API quotas daily
- Set up alerts for failures

## 🎓 Learning Resources & References

### Primary References (In Order of Priority)
1. **GEMINI.md** - Complete ADK reference (ALWAYS check first)
2. **app/agent.py** - Current implementation patterns
3. **tests/** - Working examples and test patterns
4. **AGENTS.md** - Additional agent patterns
5. **notebooks/** - Experimental implementations

### Quick Reference Protocol
```bash
# When stuck, follow this sequence:
1. grep "your_problem" GEMINI.md
2. Read the entire relevant section
3. Check app/agent.py for current usage
4. Implement following both patterns
5. Test thoroughly

# Common searches
grep -n "LlmAgent\|BaseAgent" GEMINI.md     # Agent types
grep -n "SequentialAgent\|Loop" GEMINI.md    # Orchestration
grep -n "Tool\|Function" GEMINI.md           # Tools
grep -n "State\|Session" GEMINI.md           # State management
grep -n "Callback" GEMINI.md                 # Callbacks
grep -n "Deploy\|Cloud" GEMINI.md            # Deployment
```

### Emergency Commands
```bash
# If agent breaks, check against GEMINI.md
diff <(grep -A 10 "pattern" app/agent.py) <(grep -A 10 "pattern" GEMINI.md)

# Validate structure against GEMINI.md
python -c "from app.agent import root_agent; print(root_agent.name)"

# Test with ADK eval (GEMINI.md Section 13)
adk eval tests/integration/facilitador.evalset.json --debug
```

---

## 🏆 GOLDEN RULE

**BEFORE ANY ADK-RELATED TASK:**
1. **STOP** - Don't assume anything
2. **SEARCH** - Find the topic in GEMINI.md
3. **STUDY** - Read the complete section
4. **SAMPLE** - Copy the example pattern
5. **SYNTHESIZE** - Adapt to project needs
6. **SCRUTINIZE** - Test thoroughly

**REMEMBER**: 
- GEMINI.md is your ADK bible - it contains 1531 lines of validated patterns and examples
- Every ADK question has an answer in GEMINI.md
- When in doubt, the answer is in GEMINI.md
- Failed? Check if you followed GEMINI.md patterns exactly

**SUCCESS CRITERIA**: 
- Code generated follows GEMINI.md patterns exactly
- All ADK features implemented per documentation
- Zero assumptions made without GEMINI.md verification
- Pipeline maintains integrity per GEMINI.md Section 3
- Flutter code passes both agent and human review

**THE FACILITATOR PROJECT DEPENDS ON YOUR ADHERENCE TO ADK BEST PRACTICES AS DOCUMENTED IN GEMINI.md**