"""
AI Assistant API - CNF Generator and Problem Analysis
Uses local Ollama or configurable AI providers to:
1. Analyze if a problem can be formulated as SAT
2. Convert constraint problems to CNF format
3. Provide explanations about SAT/UNSAT results
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from pathlib import Path
from datetime import datetime
import subprocess
import httpx
import json
import re
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CONFIGURATION ====================

# Get Ollama host from environment variable (for Docker), default to localhost
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

AI_CONFIG = {
    "ollama": {
        "base_url": OLLAMA_HOST,
        "default_model": "llama3.2",
        "timeout": 120.0,
        "available_models": ["llama3.2", "llama3", "mistral", "codellama", "gemma2"]
    }
}

# CNF output directory
CNF_OUTPUT_DIR = Path("/app/data/generated_cnf")
CNF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================== SCHEMAS ====================

class ProblemAnalysisRequest(BaseModel):
    """Request to analyze if a problem is SAT-compatible"""
    problem_description: str = Field(..., description="Natural language description of the problem")
    problem_type: Optional[str] = Field(None, description="Type hint: scheduling, graph, logic, etc.")
    model: Optional[str] = Field(None, description="AI model to use")


class CNFGenerationRequest(BaseModel):
    """Request to generate CNF from a constraint problem"""
    problem_description: str = Field(..., description="Description of the constraint problem")
    constraints: Optional[List[str]] = Field(None, description="List of explicit constraints")
    variables: Optional[Dict[str, str]] = Field(None, description="Variable definitions")
    num_variables: Optional[int] = Field(None, description="Hint for number of variables")
    model: Optional[str] = Field(None, description="AI model to use")
    save_to_file: bool = Field(True, description="Save generated CNF to file")
    filename: Optional[str] = Field(None, description="Custom filename for CNF file")


class ExplanationRequest(BaseModel):
    """Request to explain a SAT result"""
    cnf_content: Optional[str] = Field(None, description="CNF content")
    cnf_file_path: Optional[str] = Field(None, description="Path to CNF file")
    result: Literal["SAT", "UNSAT", "UNKNOWN"] = Field(..., description="Solver result")
    assignment: Optional[List[int]] = Field(None, description="Variable assignment if SAT")
    solver_output: Optional[str] = Field(None, description="Raw solver output")
    model: Optional[str] = Field(None, description="AI model to use")


class ChatMessage(BaseModel):
    """Chat message for conversational AI"""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Conversational chat request"""
    messages: List[ChatMessage]
    model: Optional[str] = None
    context: Optional[str] = Field(None, description="Additional context (current CNF, results, etc.)")


# ==================== HELPER FUNCTIONS ====================

async def check_ollama_status() -> Dict:
    """Check if Ollama is running and get available models"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is running
            response = await client.get(f"{AI_CONFIG['ollama']['base_url']}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "online",
                    "models": models,
                    "default_model": AI_CONFIG['ollama']['default_model']
                }
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")
    
    return {
        "status": "offline",
        "models": [],
        "default_model": None,
        "error": "Ollama is not running. Start it with: ollama serve"
    }


async def query_ollama(prompt: str, model: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
    """Query Ollama API"""
    model = model or AI_CONFIG['ollama']['default_model']
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        async with httpx.AsyncClient(timeout=AI_CONFIG['ollama']['timeout']) as client:
            response = await client.post(
                f"{AI_CONFIG['ollama']['base_url']}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama error: {response.text}"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


def parse_cnf_from_response(response: str) -> Optional[Dict]:
    """Parse CNF format from AI response"""
    # Look for CNF content in code blocks
    cnf_pattern = r'```(?:cnf|dimacs)?\s*(p cnf.*?)```'
    match = re.search(cnf_pattern, response, re.DOTALL | re.IGNORECASE)
    
    if match:
        cnf_content = match.group(1).strip()
    else:
        # Try to find CNF-like content directly
        lines = response.split('\n')
        cnf_lines = []
        in_cnf = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('p cnf'):
                in_cnf = True
            if in_cnf:
                # Check if line looks like CNF (starts with c, p, or numbers)
                if line.startswith('c ') or line.startswith('p cnf') or re.match(r'^-?\d+', line):
                    cnf_lines.append(line)
                elif line and not re.match(r'^-?\d+', line) and not line.startswith('c'):
                    # Stop if we hit non-CNF content
                    if cnf_lines:
                        break
        
        if cnf_lines:
            cnf_content = '\n'.join(cnf_lines)
        else:
            return None
    
    # Parse CNF header
    header_match = re.search(r'p cnf (\d+) (\d+)', cnf_content)
    if not header_match:
        return None
    
    num_vars = int(header_match.group(1))
    num_clauses = int(header_match.group(2))
    
    # Extract clauses
    clauses = []
    for line in cnf_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('c') and not line.startswith('p'):
            # Parse clause
            literals = line.split()
            if literals and literals[-1] == '0':
                clause = [int(lit) for lit in literals[:-1]]
                clauses.append(clause)
    
    return {
        "num_variables": num_vars,
        "num_clauses": num_clauses,
        "clauses": clauses,
        "raw_cnf": cnf_content
    }


# ==================== ENDPOINTS ====================

@router.get("/status")
async def get_ai_status() -> Dict:
    """Get AI service status and available models"""
    ollama_status = await check_ollama_status()
    
    return {
        "ollama": ollama_status,
        "supported_providers": ["ollama"],
        "recommended_models": {
            "fast": "llama3.2",
            "quality": "llama3",
            "code": "codellama"
        }
    }


@router.post("/analyze-problem")
async def analyze_problem(request: ProblemAnalysisRequest) -> Dict:
    """Analyze if a problem can be formulated as SAT"""
    
    system_prompt = """You are an expert in computational complexity and SAT (Boolean Satisfiability) problems.
Your task is to analyze problems and determine if they can be formulated as SAT problems.

For each problem, provide:
1. Whether it can be formulated as SAT (yes/no/partially)
2. The problem class (NP-complete, P, etc.)
3. How to model the variables
4. How to model the constraints as clauses
5. Estimated complexity

Be precise and technical. If the problem is not directly SAT-compatible, explain why and suggest alternatives."""

    prompt = f"""Analyze the following problem for SAT compatibility:

PROBLEM DESCRIPTION:
{request.problem_description}

{f"PROBLEM TYPE HINT: {request.problem_type}" if request.problem_type else ""}

Please provide a detailed analysis including:
1. Can this be formulated as a SAT problem? (YES/NO/PARTIALLY)
2. Problem classification (complexity class)
3. Suggested variable encoding
4. Suggested clause structure
5. Estimated number of variables and clauses
6. Any potential issues or limitations"""

    response = await query_ollama(prompt, request.model, system_prompt)
    
    # Simple parsing to extract key information
    is_sat_compatible = "YES" if "yes" in response.lower()[:200] else "NO" if "no" in response.lower()[:200] else "PARTIAL"
    
    return {
        "problem_description": request.problem_description,
        "is_sat_compatible": is_sat_compatible,
        "analysis": response,
        "timestamp": datetime.now().isoformat(),
        "model_used": request.model or AI_CONFIG['ollama']['default_model']
    }


@router.post("/generate-cnf")
async def generate_cnf(request: CNFGenerationRequest) -> Dict:
    """Generate CNF from a constraint problem description"""
    
    system_prompt = """You are an expert in SAT encoding and CNF (Conjunctive Normal Form) generation.
Your task is to convert constraint problems into valid DIMACS CNF format.

IMPORTANT RULES:
1. Output must be valid DIMACS CNF format
2. First line should be: p cnf <num_vars> <num_clauses>
3. Each clause ends with 0
4. Use comments (c ...) to explain variable meanings
5. Be precise with the encoding

Always provide the CNF inside a code block like:
```cnf
c Comment explaining the encoding
p cnf N M
1 2 0
-1 3 0
...
```"""

    constraints_text = ""
    if request.constraints:
        constraints_text = "\n".join(f"- {c}" for c in request.constraints)
    
    variables_text = ""
    if request.variables:
        variables_text = "\n".join(f"- {k}: {v}" for k, v in request.variables.items())

    prompt = f"""Convert the following constraint problem to CNF (DIMACS format):

PROBLEM:
{request.problem_description}

{f"EXPLICIT CONSTRAINTS:{chr(10)}{constraints_text}" if constraints_text else ""}

{f"VARIABLES:{chr(10)}{variables_text}" if variables_text else ""}

{f"HINT: Approximately {request.num_variables} variables expected" if request.num_variables else ""}

Please provide:
1. A clear explanation of the variable encoding
2. The complete CNF in DIMACS format (inside ```cnf``` code block)
3. Verification that the encoding is correct"""

    response = await query_ollama(prompt, request.model, system_prompt)
    
    # Parse CNF from response
    cnf_data = parse_cnf_from_response(response)
    
    result = {
        "problem_description": request.problem_description,
        "ai_response": response,
        "timestamp": datetime.now().isoformat(),
        "model_used": request.model or AI_CONFIG['ollama']['default_model']
    }
    
    if cnf_data:
        result["cnf_parsed"] = True
        result["num_variables"] = cnf_data["num_variables"]
        result["num_clauses"] = cnf_data["num_clauses"]
        result["cnf_content"] = cnf_data["raw_cnf"]
        
        # Save to file if requested
        if request.save_to_file:
            filename = request.filename or f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cnf"
            if not filename.endswith('.cnf'):
                filename += '.cnf'
            
            file_path = CNF_OUTPUT_DIR / filename
            with open(file_path, 'w') as f:
                f.write(cnf_data["raw_cnf"])
            
            result["saved_to"] = str(file_path)
    else:
        result["cnf_parsed"] = False
        result["parse_error"] = "Could not extract valid CNF from AI response. Please check the response manually."
    
    return result


@router.post("/explain-result")
async def explain_result(request: ExplanationRequest) -> Dict:
    """Get an explanation of a SAT/UNSAT result"""
    
    # Get CNF content
    cnf_content = request.cnf_content
    if not cnf_content and request.cnf_file_path:
        try:
            with open(request.cnf_file_path, 'r') as f:
                cnf_content = f.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read CNF file: {e}")
    
    system_prompt = """You are an expert in SAT solving and formal verification.
Your task is to explain SAT solver results in a clear and educational way.

When explaining results:
1. Explain what the result (SAT/UNSAT) means for the original problem
2. If SAT, explain what the satisfying assignment represents
3. If UNSAT, explain why no solution exists
4. Provide insights about the problem structure
5. Suggest improvements or variations if applicable"""

    assignment_text = ""
    if request.assignment:
        assignment_text = f"\nSATISFYING ASSIGNMENT: {request.assignment}"
    
    prompt = f"""Explain the following SAT solving result:

RESULT: {request.result}
{assignment_text}

CNF FORMULA (first 50 lines):
{chr(10).join(cnf_content.split(chr(10))[:50]) if cnf_content else "Not provided"}

{f"SOLVER OUTPUT:{chr(10)}{request.solver_output}" if request.solver_output else ""}

Please provide:
1. What does this result mean?
2. Interpretation in terms of the original problem
3. Key insights about why this result was obtained
4. Any interesting observations about the formula structure"""

    response = await query_ollama(prompt, request.model, system_prompt)
    
    return {
        "result": request.result,
        "explanation": response,
        "timestamp": datetime.now().isoformat(),
        "model_used": request.model or AI_CONFIG['ollama']['default_model']
    }


@router.post("/chat")
async def chat(request: ChatRequest) -> Dict:
    """Conversational AI for SAT-related questions"""
    
    system_prompt = """You are an AI assistant specialized in SAT solving, CNF encoding, and computational complexity.
You help users:
1. Understand SAT problems and their applications
2. Create CNF encodings for various problems
3. Interpret solver results
4. Learn about SAT solving algorithms (CDCL, DPLL, etc.)
5. Understand complexity theory related to SAT

Be educational, precise, and helpful. Use examples when appropriate.
If the user asks you to generate CNF, provide it in valid DIMACS format."""

    if request.context:
        system_prompt += f"\n\nCURRENT CONTEXT:\n{request.context}"
    
    # Build conversation
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    try:
        async with httpx.AsyncClient(timeout=AI_CONFIG['ollama']['timeout']) as client:
            response = await client.post(
                f"{AI_CONFIG['ollama']['base_url']}/api/chat",
                json={
                    "model": request.model or AI_CONFIG['ollama']['default_model'],
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data.get("message", {}).get("content", "")
                
                return {
                    "response": assistant_message,
                    "model_used": request.model or AI_CONFIG['ollama']['default_model'],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI request timed out")


@router.get("/generated-files")
async def list_generated_files() -> List[Dict]:
    """List all generated CNF files"""
    files = []
    if CNF_OUTPUT_DIR.exists():
        for f in CNF_OUTPUT_DIR.glob("*.cnf"):
            stat = f.stat()
            # Parse header to get variables and clauses
            try:
                with open(f, 'r') as cnf_file:
                    for line in cnf_file:
                        if line.startswith('p cnf'):
                            parts = line.split()
                            num_vars = int(parts[2])
                            num_clauses = int(parts[3])
                            break
                    else:
                        num_vars = None
                        num_clauses = None
            except:
                num_vars = None
                num_clauses = None
            
            files.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "num_variables": num_vars,
                "num_clauses": num_clauses
            })
    
    return sorted(files, key=lambda x: x["created"], reverse=True)


@router.delete("/generated-files/{filename}")
async def delete_generated_file(filename: str) -> Dict:
    """Delete a generated CNF file"""
    file_path = CNF_OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path.unlink()
    return {"message": f"File {filename} deleted successfully"}


@router.get("/examples")
async def get_example_problems() -> List[Dict]:
    """Get example problems that can be converted to CNF"""
    return [
        {
            "name": "Graph Coloring (3 colors)",
            "description": "Color a graph with 3 colors such that no adjacent vertices have the same color",
            "type": "graph",
            "sample_input": {
                "problem_description": "Color a triangle graph (3 vertices: A, B, C, all connected to each other) with 3 colors (Red, Green, Blue) such that no two adjacent vertices have the same color.",
                "constraints": [
                    "Each vertex must have exactly one color",
                    "Adjacent vertices cannot have the same color"
                ],
                "variables": {
                    "A_R": "Vertex A is Red",
                    "A_G": "Vertex A is Green",
                    "A_B": "Vertex A is Blue",
                    "B_R": "Vertex B is Red",
                    "...": "etc."
                }
            }
        },
        {
            "name": "N-Queens Problem",
            "description": "Place N queens on an NxN chessboard so no two queens attack each other",
            "type": "constraint",
            "sample_input": {
                "problem_description": "Place 4 queens on a 4x4 chessboard such that no two queens attack each other (no two queens in same row, column, or diagonal).",
                "num_variables": 16
            }
        },
        {
            "name": "Sudoku",
            "description": "Fill a 9x9 grid with digits 1-9 following Sudoku rules",
            "type": "constraint",
            "sample_input": {
                "problem_description": "Solve a Sudoku puzzle where each row, column, and 3x3 box must contain all digits 1-9 exactly once.",
                "constraints": [
                    "Each cell has exactly one digit (1-9)",
                    "Each row contains each digit exactly once",
                    "Each column contains each digit exactly once",
                    "Each 3x3 box contains each digit exactly once"
                ]
            }
        },
        {
            "name": "Boolean Formula",
            "description": "Check satisfiability of a boolean formula",
            "type": "logic",
            "sample_input": {
                "problem_description": "Check if the following formula is satisfiable: (A OR B) AND (NOT A OR C) AND (NOT B OR NOT C) AND (A OR C)",
                "variables": {
                    "A": "Boolean variable A",
                    "B": "Boolean variable B",
                    "C": "Boolean variable C"
                }
            }
        },
        {
            "name": "Job Scheduling",
            "description": "Schedule jobs on machines with constraints",
            "type": "scheduling",
            "sample_input": {
                "problem_description": "Schedule 3 jobs (J1, J2, J3) on 2 machines (M1, M2) in 3 time slots, where: J1 must run before J2, J3 cannot run on M1, and no machine can run two jobs at the same time.",
                "constraints": [
                    "Each job runs exactly once",
                    "J1 finishes before J2 starts",
                    "J3 only on M2",
                    "At most one job per machine per time slot"
                ]
            }
        }
    ]
