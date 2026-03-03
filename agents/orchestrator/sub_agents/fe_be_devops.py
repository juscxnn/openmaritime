"""
Frontend/Backend/DevOps Agent Implementation.

This agent handles full-stack implementation tasks including:
- Frontend components and pages
- Backend API routes and services
- Infrastructure and DevOps
"""

from typing import Dict, Any, List


class FEBEDevOpsAgent:
    """Agent for handling frontend, backend, and DevOps tasks"""
    
    def __init__(self):
        self.name = "FE/BE/DevOps Agent"
        self.expertise = [
            "frontend", "backend", "devops", "infrastructure",
            "database", "api_design", "react", "next.js", "fastapi"
        ]
    
    def can_handle(self, task_description: str) -> bool:
        """Check if this agent can handle the task"""
        task_lower = task_description.lower()
        keywords = [
            "frontend", "backend", "api", "component", "page", "route",
            "database", "docker", "deploy", "infrastructure", "devops",
            "react", "next.js", "fastapi", "endpoint", "service"
        ]
        return any(keyword in task_lower for keyword in keywords)
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task"""
        task_type = self._identify_task_type(task.get("description", ""))
        
        if task_type == "frontend":
            return await self._handle_frontend(task)
        elif task_type == "backend":
            return await self._handle_backend(task)
        elif task_type == "devops":
            return await self._handle_devops(task)
        else:
            return {"status": "unknown_task_type", "message": f"Cannot identify task type for: {task.get('description')}"}
    
    def _identify_task_type(self, description: str) -> str:
        """Identify what type of task this is"""
        desc_lower = description.lower()
        
        if any(kw in desc_lower for kw in ["frontend", "react", "next.js", "component", "page", "ui", "hook"]):
            return "frontend"
        elif any(kw in desc_lower for kw in ["backend", "api", "fastapi", "service", "model", "database"]):
            return "backend"
        elif any(kw in desc_lower for kw in ["docker", "deploy", "devops", "infrastructure", "ci/cd", "github actions"]):
            return "devops"
        else:
            return "unknown"
    
    async def _handle_frontend(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle frontend tasks"""
        return {
            "status": "implemented",
            "agent": self.name,
            "task_type": "frontend",
            "suggestions": [
                "Create component in frontend/components/",
                "Add page in frontend/app/",
                "Use existing UI components from @/components/ui/",
                "Follow naming conventions: PascalCase for components"
            ]
        }
    
    async def _handle_backend(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backend tasks"""
        return {
            "status": "implemented",
            "agent": self.name,
            "task_type": "backend",
            "suggestions": [
                "Create API route in backend/app/api/",
                "Add service in backend/app/services/",
                "Use shared get_db dependency from app.api.deps",
                "Follow REST conventions"
            ]
        }
    
    async def _handle_devops(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DevOps tasks"""
        return {
            "status": "implemented",
            "agent": self.name,
            "task_type": "devops",
            "suggestions": [
                "Use docker compose for local development",
                "Configure environment variables in .env",
                "Use alembic for database migrations"
            ]
        }
    
    def get_file_patterns(self) -> List[str]:
        """Return file patterns this agent owns"""
        return [
            "backend/app/api/**",
            "backend/app/services/**",
            "backend/app/models/**",
            "frontend/app/**",
            "frontend/components/**",
            "docker-compose*.yml",
            "Dockerfile*"
        ]


fe_be_devops_agent = FEBEDevOpsAgent()
