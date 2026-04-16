from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Jira.js MCP Server")

API_TOKEN = os.environ.get("API_TOKEN", "")
HOST = os.environ.get("HOST", "")
EMAIL = os.environ.get("EMAIL", "")


def get_base_url() -> str:
    host = HOST.rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    return host


def get_auth():
    return (EMAIL, API_TOKEN)


def get_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


@mcp.tool()
async def get_myself() -> dict:
    """Get the details of the currently authenticated user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/myself",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def search_issues(
    jql: str,
    start_at: int = 0,
    max_results: int = 50,
    fields: Optional[str] = None,
) -> dict:
    """Search for Jira issues using JQL (Jira Query Language).
    
    Args:
        jql: JQL query string (e.g. 'project = MY_PROJECT AND status = Open')
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return (default 50)
        fields: Comma-separated list of fields to include (e.g. 'summary,status,assignee')
    """
    params: dict[str, Any] = {
        "jql": jql,
        "startAt": start_at,
        "maxResults": max_results,
    }
    if fields:
        params["fields"] = fields

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/search",
            auth=get_auth(),
            headers=get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue(issue_key: str, fields: Optional[str] = None) -> dict:
    """Get details of a specific Jira issue by its key (e.g. 'PROJECT-123').
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        fields: Comma-separated list of fields to include
    """
    params: dict[str, Any] = {}
    if fields:
        params["fields"] = fields

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            auth=get_auth(),
            headers=get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: Optional[str] = None,
    assignee_account_id: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> dict:
    """Create a new Jira issue.
    
    Args:
        project_key: The project key (e.g. 'MYPROJECT')
        summary: Issue summary/title
        issue_type: Issue type name (e.g. 'Task', 'Bug', 'Story', 'Epic')
        description: Issue description text
        assignee_account_id: Account ID of the user to assign the issue to
        priority: Priority name (e.g. 'High', 'Medium', 'Low')
        labels: List of labels to add to the issue
    """
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }

    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        }

    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}

    if priority:
        fields["priority"] = {"name": priority}

    if labels:
        fields["labels"] = labels

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue",
            auth=get_auth(),
            headers=get_headers(),
            json={"fields": fields},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def update_issue(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_account_id: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> dict:
    """Update an existing Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        summary: New summary/title
        description: New description text
        assignee_account_id: Account ID of the new assignee (set to empty string to unassign)
        priority: New priority name (e.g. 'High', 'Medium', 'Low')
        labels: New list of labels
    """
    fields: dict[str, Any] = {}

    if summary is not None:
        fields["summary"] = summary

    if description is not None:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        }

    if assignee_account_id is not None:
        fields["assignee"] = {"accountId": assignee_account_id} if assignee_account_id else None

    if priority is not None:
        fields["priority"] = {"name": priority}

    if labels is not None:
        fields["labels"] = labels

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            auth=get_auth(),
            headers=get_headers(),
            json={"fields": fields},
        )
        response.raise_for_status()
        return {"success": True, "issue_key": issue_key}


@mcp.tool()
async def delete_issue(issue_key: str) -> dict:
    """Delete a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return {"success": True, "issue_key": issue_key}


@mcp.tool()
async def transition_issue(issue_key: str, transition_id: str) -> dict:
    """Transition a Jira issue to a new status using a transition ID.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        transition_id: The ID of the transition to perform
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/transitions",
            auth=get_auth(),
            headers=get_headers(),
            json={"transition": {"id": transition_id}},
        )
        response.raise_for_status()
        return {"success": True, "issue_key": issue_key, "transition_id": transition_id}


@mcp.tool()
async def get_issue_transitions(issue_key: str) -> dict:
    """Get available transitions for a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/transitions",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def add_comment(issue_key: str, comment_text: str) -> dict:
    """Add a comment to a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        comment_text: The text of the comment to add
    """
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment_text}],
                }
            ],
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/comment",
            auth=get_auth(),
            headers=get_headers(),
            json=body,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue_comments(issue_key: str, start_at: int = 0, max_results: int = 50) -> dict:
    """Get comments for a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/comment",
            auth=get_auth(),
            headers=get_headers(),
            params={"startAt": start_at, "maxResults": max_results},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_projects(start_at: int = 0, max_results: int = 50) -> dict:
    """Get all accessible Jira projects.
    
    Args:
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/search",
            auth=get_auth(),
            headers=get_headers(),
            params={"startAt": start_at, "maxResults": max_results},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project(project_key: str) -> dict:
    """Get details of a specific Jira project.
    
    Args:
        project_key: The project key (e.g. 'MYPROJECT')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project_issues(
    project_key: str,
    start_at: int = 0,
    max_results: int = 50,
    status: Optional[str] = None,
    issue_type: Optional[str] = None,
) -> dict:
    """Get issues for a specific Jira project.
    
    Args:
        project_key: The project key (e.g. 'MYPROJECT')
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
        status: Filter by status name (e.g. 'Open', 'In Progress', 'Done')
        issue_type: Filter by issue type (e.g. 'Bug', 'Task', 'Story')
    """
    jql_parts = [f"project = {project_key}"]
    if status:
        jql_parts.append(f'status = "{status}"')
    if issue_type:
        jql_parts.append(f'issuetype = "{issue_type}"')
    jql = " AND ".join(jql_parts)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/search",
            auth=get_auth(),
            headers=get_headers(),
            params={"jql": jql, "startAt": start_at, "maxResults": max_results},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_boards(project_key: Optional[str] = None, start_at: int = 0, max_results: int = 50) -> dict:
    """Get all Agile boards, optionally filtered by project.
    
    Args:
        project_key: Filter boards by project key
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    params: dict[str, Any] = {"startAt": start_at, "maxResults": max_results}
    if project_key:
        params["projectKeyOrId"] = project_key

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/board",
            auth=get_auth(),
            headers=get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_board_sprints(
    board_id: int,
    state: Optional[str] = None,
    start_at: int = 0,
    max_results: int = 50,
) -> dict:
    """Get sprints for a specific Agile board.
    
    Args:
        board_id: The ID of the board
        state: Filter by sprint state ('active', 'closed', 'future')
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    params: dict[str, Any] = {"startAt": start_at, "maxResults": max_results}
    if state:
        params["state"] = state

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/board/{board_id}/sprint",
            auth=get_auth(),
            headers=get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_sprint_issues(
    sprint_id: int,
    start_at: int = 0,
    max_results: int = 50,
) -> dict:
    """Get issues in a specific sprint.
    
    Args:
        sprint_id: The ID of the sprint
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/sprint/{sprint_id}/issue",
            auth=get_auth(),
            headers=get_headers(),
            params={"startAt": start_at, "maxResults": max_results},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_users(query: Optional[str] = None, start_at: int = 0, max_results: int = 50) -> dict:
    """Search for Jira users.
    
    Args:
        query: Search query string (searches username, name, email)
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    params: dict[str, Any] = {"startAt": start_at, "maxResults": max_results}
    if query:
        params["query"] = query

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/users/search",
            auth=get_auth(),
            headers=get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue_types(project_key: Optional[str] = None) -> dict:
    """Get all available issue types, optionally filtered by project.
    
    Args:
        project_key: Filter issue types by project key
    """
    async with httpx.AsyncClient() as client:
        if project_key:
            response = await client.get(
                f"{get_base_url()}/rest/api/3/issuetype/project",
                auth=get_auth(),
                headers=get_headers(),
                params={"projectId": project_key},
            )
        else:
            response = await client.get(
                f"{get_base_url()}/rest/api/3/issuetype",
                auth=get_auth(),
                headers=get_headers(),
            )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def add_worklog(
    issue_key: str,
    time_spent: str,
    comment: Optional[str] = None,
    started: Optional[str] = None,
) -> dict:
    """Add a worklog entry to a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        time_spent: Time spent in Jira time format (e.g. '2h 30m', '1d', '30m')
        comment: Optional comment for the worklog
        started: When the work started in ISO 8601 format (e.g. '2024-01-15T09:00:00.000+0000')
    """
    body: dict[str, Any] = {"timeSpent": time_spent}

    if comment:
        body["comment"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment}],
                }
            ],
        }

    if started:
        body["started"] = started

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/worklog",
            auth=get_auth(),
            headers=get_headers(),
            json=body,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_worklogs(issue_key: str, start_at: int = 0, max_results: int = 50) -> dict:
    """Get worklogs for a Jira issue.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        start_at: Index of the first result to return (0-based)
        max_results: Maximum number of results to return
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/worklog",
            auth=get_auth(),
            headers=get_headers(),
            params={"startAt": start_at, "maxResults": max_results},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project_versions(project_key: str) -> dict:
    """Get all versions for a Jira project.
    
    Args:
        project_key: The project key (e.g. 'MYPROJECT')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}/versions",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project_components(project_key: str) -> dict:
    """Get all components for a Jira project.
    
    Args:
        project_key: The project key (e.g. 'MYPROJECT')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}/components",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def assign_issue(issue_key: str, account_id: Optional[str] = None) -> dict:
    """Assign a Jira issue to a user or unassign it.
    
    Args:
        issue_key: The Jira issue key (e.g. 'PROJECT-123')
        account_id: Account ID of the user to assign to. Pass null/empty to unassign.
    """
    body: dict[str, Any] = {"accountId": account_id if account_id else None}

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/assignee",
            auth=get_auth(),
            headers=get_headers(),
            json=body,
        )
        response.raise_for_status()
        return {"success": True, "issue_key": issue_key, "assignee": account_id}


@mcp.tool()
async def get_issue_link_types() -> dict:
    """Get all available issue link types in Jira."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issueLinkType",
            auth=get_auth(),
            headers=get_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def link_issues(
    link_type: str,
    inward_issue_key: str,
    outward_issue_key: str,
    comment: Optional[str] = None,
) -> dict:
    """Create a link between two Jira issues.
    
    Args:
        link_type: The name of the link type (e.g. 'Blocks', 'Clones', 'Duplicate')
        inward_issue_key: The key of the inward issue (e.g. 'PROJECT-123')
        outward_issue_key: The key of the outward issue (e.g. 'PROJECT-456')
        comment: Optional comment to add with the link
    """
    body: dict[str, Any] = {
        "type": {"name": link_type},
        "inwardIssue": {"key": inward_issue_key},
        "outwardIssue": {"key": outward_issue_key},
    }

    if comment:
        body["comment"] = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issueLink",
            auth=get_auth(),
            headers=get_headers(),
            json=body,
        )
        response.raise_for_status()
        return {"success": True, "inward_issue": inward_issue_key, "outward_issue": outward_issue_key}




_SERVER_SLUG = "mrrefactoring-jira-js"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
