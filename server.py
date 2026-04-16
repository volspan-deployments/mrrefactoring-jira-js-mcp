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
JIRA_HOST = os.environ.get("HOST", "")
JIRA_EMAIL = os.environ.get("EMAIL", "")


def get_base_url() -> str:
    host = JIRA_HOST.rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    return host


def get_auth_headers() -> dict:
    import base64
    credentials = base64.b64encode(f"{JIRA_EMAIL}:{API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@mcp.tool()
async def get_issue(issue_key: str) -> dict:
    """Get details of a Jira issue by its key (e.g. PROJECT-123)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def search_issues(jql: str, max_results: int = 50, start_at: int = 0) -> dict:
    """Search Jira issues using JQL (Jira Query Language)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/search",
            headers=get_auth_headers(),
            json={"jql": jql, "maxResults": max_results, "startAt": start_at},
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
    labels: Optional[list] = None,
) -> dict:
    """Create a new Jira issue."""
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
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
            headers=get_auth_headers(),
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
    labels: Optional[list] = None,
) -> dict:
    """Update fields of an existing Jira issue."""
    fields: dict[str, Any] = {}
    if summary:
        fields["summary"] = summary
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if priority:
        fields["priority"] = {"name": priority}
    if labels is not None:
        fields["labels"] = labels
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            headers=get_auth_headers(),
            json={"fields": fields},
        )
        if response.status_code == 204:
            return {"success": True, "message": f"Issue {issue_key} updated successfully."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def delete_issue(issue_key: str) -> dict:
    """Delete a Jira issue by its key."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}",
            headers=get_auth_headers(),
        )
        if response.status_code == 204:
            return {"success": True, "message": f"Issue {issue_key} deleted successfully."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def transition_issue(issue_key: str, transition_id: str) -> dict:
    """Transition a Jira issue to a new status using a transition ID."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/transitions",
            headers=get_auth_headers(),
            json={"transition": {"id": transition_id}},
        )
        if response.status_code == 204:
            return {"success": True, "message": f"Issue {issue_key} transitioned successfully."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue_transitions(issue_key: str) -> dict:
    """Get available transitions for a Jira issue."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/transitions",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def add_comment(issue_key: str, comment_body: str) -> dict:
    """Add a comment to a Jira issue."""
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_body}]}],
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/comment",
            headers=get_auth_headers(),
            json=body,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_comments(issue_key: str, max_results: int = 50, start_at: int = 0) -> dict:
    """Get comments for a Jira issue."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/comment",
            headers=get_auth_headers(),
            params={"maxResults": max_results, "startAt": start_at},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_projects(max_results: int = 50, start_at: int = 0) -> dict:
    """Get all Jira projects accessible to the authenticated user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/search",
            headers=get_auth_headers(),
            params={"maxResults": max_results, "startAt": start_at},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project(project_key: str) -> dict:
    """Get details of a specific Jira project by its key."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_myself() -> dict:
    """Get details of the currently authenticated Jira user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/myself",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_user(account_id: str) -> dict:
    """Get details of a Jira user by their account ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/user",
            headers=get_auth_headers(),
            params={"accountId": account_id},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def find_users(query: str, max_results: int = 50) -> dict:
    """Search for Jira users by display name or email."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/user/search",
            headers=get_auth_headers(),
            params={"query": query, "maxResults": max_results},
        )
        response.raise_for_status()
        return {"users": response.json()}


@mcp.tool()
async def get_boards(project_key_or_id: Optional[str] = None, board_type: Optional[str] = None, max_results: int = 50, start_at: int = 0) -> dict:
    """Get all Agile boards, optionally filtered by project key or board type (scrum, kanban)."""
    params: dict[str, Any] = {"maxResults": max_results, "startAt": start_at}
    if project_key_or_id:
        params["projectKeyOrId"] = project_key_or_id
    if board_type:
        params["type"] = board_type
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/board",
            headers=get_auth_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_board_sprints(board_id: int, state: Optional[str] = None, max_results: int = 50, start_at: int = 0) -> dict:
    """Get sprints for an Agile board. State can be 'active', 'future', or 'closed'."""
    params: dict[str, Any] = {"maxResults": max_results, "startAt": start_at}
    if state:
        params["state"] = state
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/board/{board_id}/sprint",
            headers=get_auth_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_sprint(sprint_id: int) -> dict:
    """Get details of a specific Agile sprint by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/sprint/{sprint_id}",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_sprint_issues(sprint_id: int, max_results: int = 50, start_at: int = 0) -> dict:
    """Get all issues in a specific Agile sprint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/sprint/{sprint_id}/issue",
            headers=get_auth_headers(),
            params={"maxResults": max_results, "startAt": start_at},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_board_backlog(board_id: int, jql: Optional[str] = None, max_results: int = 50, start_at: int = 0) -> dict:
    """Get the backlog issues for an Agile board."""
    params: dict[str, Any] = {"maxResults": max_results, "startAt": start_at}
    if jql:
        params["jql"] = jql
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/agile/1.0/board/{board_id}/backlog",
            headers=get_auth_headers(),
            params=params,
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
    """Add a worklog entry to a Jira issue. time_spent should be in Jira duration format (e.g. '1h 30m'). started is ISO8601 datetime string."""
    body: dict[str, Any] = {"timeSpent": time_spent}
    if comment:
        body["comment"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}],
        }
    if started:
        body["started"] = started
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/worklog",
            headers=get_auth_headers(),
            json=body,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_worklogs(issue_key: str) -> dict:
    """Get all worklogs for a Jira issue."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/worklog",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue_link_types() -> dict:
    """Get all available issue link types in Jira."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issueLinkType",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def link_issues(
    inward_issue_key: str,
    outward_issue_key: str,
    link_type_name: str,
    comment: Optional[str] = None,
) -> dict:
    """Create a link between two Jira issues."""
    body: dict[str, Any] = {
        "type": {"name": link_type_name},
        "inwardIssue": {"key": inward_issue_key},
        "outwardIssue": {"key": outward_issue_key},
    }
    if comment:
        body["comment"] = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}],
            }
        }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_base_url()}/rest/api/3/issueLink",
            headers=get_auth_headers(),
            json=body,
        )
        if response.status_code == 201:
            return {"success": True, "message": "Issue link created successfully."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_project_versions(project_key: str) -> dict:
    """Get all versions (releases) for a Jira project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}/versions",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return {"versions": response.json()}


@mcp.tool()
async def get_project_components(project_key: str) -> dict:
    """Get all components for a Jira project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/project/{project_key}/components",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return {"components": response.json()}


@mcp.tool()
async def get_issue_types() -> dict:
    """Get all issue types available in the Jira instance."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issuetype",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return {"issueTypes": response.json()}


@mcp.tool()
async def get_priorities() -> dict:
    """Get all available issue priorities in Jira."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/priority",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return {"priorities": response.json()}


@mcp.tool()
async def get_statuses() -> dict:
    """Get all available issue statuses in Jira."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/status",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return {"statuses": response.json()}


@mcp.tool()
async def assign_issue(issue_key: str, account_id: Optional[str] = None) -> dict:
    """Assign a Jira issue to a user. Pass null account_id to unassign."""
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/assignee",
            headers=get_auth_headers(),
            json={"accountId": account_id},
        )
        if response.status_code == 204:
            return {"success": True, "message": f"Issue {issue_key} assigned successfully."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_issue_watchers(issue_key: str) -> dict:
    """Get all watchers of a Jira issue."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/issue/{issue_key}/watchers",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_server_info() -> dict:
    """Get information about the Jira server/instance."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{get_base_url()}/rest/api/3/serverInfo",
            headers=get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()




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
