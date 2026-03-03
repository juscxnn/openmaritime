"""Multi-Agent Orchestrator for OpenMaritime Development

This orchestrator manages task delegation to specialized sub-agents:
- Systems Architect: Architecture decisions, system design, tech stack
- FE/BE/DevOps: Frontend, backend, infrastructure implementation
- ML Architect: AI/ML integration, Wake AI ranking, local Llama
- Optimization Specialist: Performance, caching, scalability
- Senior Expert UIUX: User experience, design systems, accessibility
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime


class AgentRole(Enum):
    SYSTEMS_ARCHITECT = "systems_architect"
    FE_BE_DEVOPS = "fe_be_devops"
    ML_ARCHITECT = "ml_architect"
    OPTIMIZATION_SPECIALIST = "optimization_specialist"
    SENIOR_EXPERT_UIUX = "senior_expert_uiux"
    ORCHESTRATOR = "orchestrator"


@dataclass
class Task:
    """Represents a task to be delegated to an agent"""
    id: str
    title: str
    description: str
    priority: int = 1  # 1-5, 1 is highest
    status: str = "pending"  # pending, in_progress, completed, failed
    assigned_agent: Optional[AgentRole] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    role: AgentRole
    name: str
    description: str
    expertise: List[str]
    file_patterns: List[str]  # File patterns this agent owns
    can_delegate_to: List[AgentRole] = field(default_factory=list)


AGENT_CAPABILITIES: Dict[AgentRole, AgentCapability] = {
    AgentRole.SYSTEMS_ARCHITECT: AgentCapability(
        role=AgentRole.SYSTEMS_ARCHITECT,
        name="Systems Architect",
        description="Architectural decisions, system design, tech stack selection, scalability patterns",
        expertise=["system_design", "architecture_patterns", "tech_stack", "scalability", "security"],
        file_patterns=["*.md", "architecture/**", "docs/**", "*.yaml", "*.yml"],
        can_delegate_to=[AgentRole.FE_BE_DEVOPS, AgentRole.ML_ARCHITECT]
    ),
    AgentRole.FE_BE_DEVOPS: AgentCapability(
        role=AgentRole.FE_BE_DEVOPS,
        name="FE/BE/DevOps",
        description="Full-stack implementation, frontend/backend code, infrastructure, CI/CD",
        expertise=["frontend", "backend", "devops", "infrastructure", "database", "api_design"],
        file_patterns=["backend/**", "frontend/**", "docker/**", "*.dockerfile", "*.tf"],
        can_delegate_to=[]
    ),
    AgentRole.ML_ARCHITECT: AgentCapability(
        role=AgentRole.ML_ARCHITECT,
        name="ML Architect",
        description="AI/ML integration, Wake AI ranking engine, local Llama, data pipelines",
        expertise=["machine_learning", "llm", "llama", "ranking_algorithms", "data_processing", "nlp"],
        file_patterns=["**/ml/**", "**/wake_ai/**", "**/ai/**", "**/models/**"],
        can_delegate_to=[]
    ),
    AgentRole.OPTIMIZATION_SPECIALIST: AgentCapability(
        role=AgentRole.OPTIMIZATION_SPECIALIST,
        name="Optimization Specialist",
        description="Performance optimization, caching, database tuning, scalability",
        expertise=["performance", "caching", "optimization", "database", "load_balancing", "profiling"],
        file_patterns=["**/cache/**", "**/optimization/**", "**/performance/**"],
        can_delegate_to=[]
    ),
    AgentRole.SENIOR_EXPERT_UIUX: AgentCapability(
        role=AgentRole.SENIOR_EXPERT_UIUX,
        name="Senior Expert UI/UX",
        description="User experience, design systems, accessibility, UI components",
        expertise=["ui_design", "ux_design", "accessibility", "design_systems", "components", "animations"],
        file_patterns=["frontend/components/**", "frontend/app/**", "**/*.css", "**/*.scss"],
        can_delegate_to=[]
    ),
}


class Orchestrator:
    """Main orchestrator for delegating tasks to specialized agents"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0
        self.execution_log: List[Dict] = []
    
    def create_task(
        self,
        title: str,
        description: str,
        priority: int = 3,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """Create a new task and assign to appropriate agent"""
        self.task_counter += 1
        task = Task(
            id=f"task_{self.task_counter}",
            title=title,
            description=description,
            priority=priority,
            dependencies=dependencies or []
        )
        self.tasks[task.id] = task
        return task
    
    def assign_task(self, task_id: str, agent_role: AgentRole) -> bool:
        """Manually assign a task to a specific agent"""
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].assigned_agent = agent_role
        return True
    
    def auto_assign_task(self, task_id: str) -> AgentRole:
        """Automatically assign task to best-fit agent based on content analysis"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        desc_lower = task.description.lower()
        
        # Score each agent based on task content
        scores: Dict[AgentRole, float] = {
            AgentRole.SYSTEMS_ARCHITECT: 0,
            AgentRole.FE_BE_DEVOPS: 0,
            AgentRole.ML_ARCHITECT: 0,
            AgentRole.OPTIMIZATION_SPECIALIST: 0,
            AgentRole.SENIOR_EXPERT_UIUX: 0,
        }
        
        # Keywords mapping to agents
        keyword_agents = {
            "architecture": AgentRole.SYSTEMS_ARCHITECT,
            "system design": AgentRole.SYSTEMS_ARCHITECT,
            "tech stack": AgentRole.SYSTEMS_ARCHITECT,
            "scalability": AgentRole.SYSTEMS_ARCHITECT,
            "frontend": AgentRole.FE_BE_DEVOPS,
            "backend": AgentRole.FE_BE_DEVOPS,
            "devops": AgentRole.FE_BE_DEVOPS,
            "infrastructure": AgentRole.FE_BE_DEVOPS,
            "api": AgentRole.FE_BE_DEVOPS,
            "database": AgentRole.FE_BE_DEVOPS,
            "ml": AgentRole.ML_ARCHITECT,
            "ai": AgentRole.ML_ARCHITECT,
            "llama": AgentRole.ML_ARCHITECT,
            "wake ai": AgentRole.ML_ARCHITECT,
            "ranking": AgentRole.ML_ARCHITECT,
            "optimization": AgentRole.OPTIMIZATION_SPECIALIST,
            "performance": AgentRole.OPTIMIZATION_SPECIALIST,
            "caching": AgentRole.OPTIMIZATION_SPECIALIST,
            "ui": AgentRole.SENIOR_EXPERT_UIUX,
            "ux": AgentRole.SENIOR_EXPERT_UIUX,
            "design": AgentRole.SENIOR_EXPERT_UIUX,
            "accessibility": AgentRole.SENIOR_EXPERT_UIUX,
            "component": AgentRole.SENIOR_EXPERT_UIUX,
        }
        
        for keyword, agent in keyword_agents.items():
            if keyword in desc_lower:
                scores[agent] += 1
        
        # Also consider file patterns if mentioned
        for role, capability in AGENT_CAPABILITIES.items():
            for pattern in capability.file_patterns:
                if pattern.replace("**/", "").replace("*", "") in desc_lower:
                    scores[role] += 0.5
        
        # Select agent with highest score
        best_agent = max(scores.items(), key=lambda x: x[1])[0]
        if scores[best_agent] == 0:
            best_agent = AgentRole.FE_BE_DEVOPS  # Default to FE/BE/DevOps
        
        task.assigned_agent = best_agent
        return best_agent
    
    def get_task_chain(self, task_id: str) -> List[Task]:
        """Get ordered list of tasks including dependencies"""
        if task_id not in self.tasks:
            return []
        
        chain = []
        visited = set()
        
        def add_task(tid: str):
            if tid in visited:
                return
            visited.add(tid)
            task = self.tasks[tid]
            for dep_id in task.dependencies:
                add_task(dep_id)
            chain.append(task)
        
        add_task(task_id)
        return chain
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task - returns agent configuration for Task tool"""
        if task_id not in self.tasks:
            return {"error": f"Task {task_id} not found"}
        
        task = self.tasks[task_id]
        if task.assigned_agent is None:
            self.auto_assign_task(task_id)
        
        assigned = task.assigned_agent
        if assigned is None:
            return {"error": "Failed to assign agent to task"}
        
        agent_cap = AGENT_CAPABILITIES[assigned]
        
        return {
            "task_id": task.id,
            "task_title": task.title,
            "task_description": task.description,
            "assigned_agent": agent_cap.name,
            "agent_role": assigned.value,
            "agent_expertise": agent_cap.expertise,
            "priority": task.priority,
            "execution_prompt": self._build_execution_prompt(task, agent_cap)
        }
    
    def _build_execution_prompt(self, task: Task, capability: AgentCapability) -> str:
        """Build detailed prompt for agent execution"""
        return f"""You are the {capability.name} agent for OpenMaritime project.

Your role: {capability.description}
Your expertise: {', '.join(capability.expertise)}

TASK: {task.title}
DESCRIPTION: {task.description}

Execute this task using the available tools. Focus on your area of expertise.
When delegating, use the orchestrator for sub-tasks.
"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall orchestration status"""
        status = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
        agent_counts = {role.value: 0 for role in AgentRole if role != AgentRole.ORCHESTRATOR}
        
        for task in self.tasks.values():
            status[task.status] = status.get(task.status, 0) + 1
            if task.assigned_agent:
                agent_counts[task.assigned_agent.value] += 1
        
        return {
            "total_tasks": len(self.tasks),
            "status": status,
            "agent_assignments": agent_counts,
            "capabilities": {
                role.value: {
                    "name": cap.name,
                    "expertise": cap.expertise
                }
                for role, cap in AGENT_CAPABILITIES.items()
            }
        }


# Global orchestrator instance
orchestrator = Orchestrator()


# Helper functions for creating common tasks
def create_infrastructure_task(title: str, description: str, priority: int = 3) -> Task:
    """Create a task for Systems Architect"""
    task = orchestrator.create_task(title, description, priority)
    orchestrator.assign_task(task.id, AgentRole.SYSTEMS_ARCHITECT)
    return task


def create_implementation_task(title: str, description: str, priority: int = 3) -> Task:
    """Create a task for FE/BE/DevOps"""
    task = orchestrator.create_task(title, description, priority)
    orchestrator.assign_task(task.id, AgentRole.FE_BE_DEVOPS)
    return task


def create_ml_task(title: str, description: str, priority: int = 3) -> Task:
    """Create a task for ML Architect"""
    task = orchestrator.create_task(title, description, priority)
    orchestrator.assign_task(task.id, AgentRole.ML_ARCHITECT)
    return task


def create_optimization_task(title: str, description: str, priority: int = 3) -> Task:
    """Create a task for Optimization Specialist"""
    task = orchestrator.create_task(title, description, priority)
    orchestrator.assign_task(task.id, AgentRole.OPTIMIZATION_SPECIALIST)
    return task


def create_uiux_task(title: str, description: str, priority: int = 3) -> Task:
    """Create a task for Senior Expert UI/UX"""
    task = orchestrator.create_task(title, description, priority)
    orchestrator.assign_task(task.id, AgentRole.SENIOR_EXPERT_UIUX)
    return task
