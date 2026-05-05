import os
import sys
import yaml
import requests

API_BASE = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-11-28",
}


def load_definition(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def get_auth_headers(token):
    headers = HEADERS.copy()
    headers["Authorization"] = f"token {token}"
    return headers


def github_request(method, url, token, **kwargs):
    response = requests.request(method, url, headers=get_auth_headers(token), **kwargs)
    if not response.ok:
        raise SystemExit(
            f"GitHub request failed ({response.status_code}): {response.text}"
        )
    return response.json()


def get_repo_projects(owner, repo, token):
    url = f"{API_BASE}/repos/{owner}/{repo}/projects"
    try:
        return github_request("GET", url, token, params={"per_page": 100})
    except SystemExit as error:
        message = str(error)
        if "404" in message:
            print("Warning: GitHub Projects API returned 404. Repository project boards may not be available with this token or API version.")
            return None
        raise


def create_repo_project(owner, repo, token, name, body=""):
    url = f"{API_BASE}/repos/{owner}/{repo}/projects"
    payload = {"name": name, "body": body}
    return github_request("POST", url, token, json=payload)


def get_repo_issues(owner, repo, token):
    url = f"{API_BASE}/repos/{owner}/{repo}/issues"
    issues = []
    page = 1
    while True:
        page_items = github_request(
            "GET",
            url,
            token,
            params={"state": "all", "per_page": 100, "page": page},
        )
        if not page_items:
            break
        issues.extend(page_items)
        if len(page_items) < 100:
            break
        page += 1
    return issues


def create_repo_issue(owner, repo, token, title, body="", labels=None):
    url = f"{API_BASE}/repos/{owner}/{repo}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    return github_request("POST", url, token, json=payload)


def get_project_columns(project_id, token):
    url = f"{API_BASE}/projects/{project_id}/columns"
    return github_request("GET", url, token, params={"per_page": 100})


def create_project_column(project_id, token, name):
    url = f"{API_BASE}/projects/{project_id}/columns"
    payload = {"name": name}
    return github_request("POST", url, token, json=payload)


def get_column_cards(column_id, token):
    url = f"{API_BASE}/projects/columns/{column_id}/cards"
    return github_request("GET", url, token, params={"per_page": 100})


def create_card(column_id, token, note=None, issue_id=None):
    url = f"{API_BASE}/projects/columns/{column_id}/cards"
    payload = {}
    if issue_id:
        payload["content_id"] = issue_id
        payload["content_type"] = "Issue"
    elif note:
        payload["note"] = note
    else:
        raise ValueError("Card must contain either note or issue_id.")
    return github_request("POST", url, token, json=payload)


def card_references_issue(card, owner, repo, issue_number):
    content_url = card.get("content_url")
    return content_url == f"{API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python create_github_project_board.py <definition-path>")

    definition_path = sys.argv[1]
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")

    if not token:
        raise SystemExit("GITHUB_TOKEN environment variable is required")
    if not repository:
        raise SystemExit("GITHUB_REPOSITORY environment variable is required")

    owner, repo = repository.split("/")
    definition = load_definition(definition_path)
    project = definition.get("project")

    if not project:
        raise SystemExit("Invalid project definition: missing 'project' section")

    project_name = project.get("name")
    if not project_name:
        raise SystemExit("Project definition must include a name")

    project_body = project.get("body", "")
    print(f"Searching for existing project '{project_name}' in {owner}/{repo}...")
    projects = get_repo_projects(owner, repo, token)

    project_id = None
    columns_by_name = {}
    if projects is not None:
        match = next((p for p in projects if p.get("name") == project_name), None)
        if match:
            project_id = match["id"]
            print(f"Found existing project with ID {project_id}. Reusing it.")
        else:
            print(f"Creating project '{project_name}'...")
            created = create_repo_project(owner, repo, token, project_name, project_body)
            project_id = created["id"]
            print(f"Created project with ID {project_id}.")

        print("Loading columns...")
        existing_columns = get_project_columns(project_id, token)
        columns_by_name = {c["name"]: c for c in existing_columns}
    else:
        print("Project board API unavailable; will create issues only.")

    existing_issues = get_repo_issues(owner, repo, token)
    issues_by_title = {issue["title"]: issue for issue in existing_issues}

    for issue_def in project.get("issues", []):
        title = issue_def.get("title")
        body = issue_def.get("body", "")
        labels = issue_def.get("labels", [])
        column_name = issue_def.get("column")

        if not title:
            print("Skipping issue definition with missing title.")
            continue

        issue = issues_by_title.get(title)
        if issue:
            print(f"Found existing issue: {title}")
        else:
            print(f"Creating issue: {title}")
            issue = create_repo_issue(owner, repo, token, title, body, labels)
            issues_by_title[title] = issue

        if project_id is not None and column_name:
            column = columns_by_name.get(column_name)
            if not column:
                raise SystemExit(f"Column '{column_name}' is not defined in project columns.")

            column_id = column["id"]
            existing_cards = get_column_cards(column_id, token)
            if any(
                card_references_issue(c, owner, repo, issue["number"])
                for c in existing_cards
                if c.get("content_url")
            ):
                print(f"Issue card already exists in '{column_name}': {title}")
            else:
                print(f"Adding issue card to '{column_name}': {title}")
                create_card(column_id, token, issue_id=issue["id"])

    if project_id is None:
        print("Completed issue creation; project board actions were skipped because the Projects API is unavailable.")
        return

    if "cards" not in project:
        print("No cards defined in project definition. Project issues created.")
        return

    for card in project["cards"]:
        column_name = card.get("column")
        note = card.get("note")
        if not column_name or not note:
            print("Skipping invalid card definition missing column or note.")
            continue

        column = columns_by_name.get(column_name)
        if not column:
            raise SystemExit(f"Column '{column_name}' is not defined in project columns.")

        column_id = column["id"]
        existing_cards = get_column_cards(column_id, token)
        if any(c.get("note") == note for c in existing_cards if c.get("note") is not None):
            print(f"Card already exists in '{column_name}': {note}")
            continue

        print(f"Creating card in '{column_name}': {note}")
        create_card(column_id, token, note)

    print("Project board setup complete.")


if __name__ == "__main__":
    main()
