import json
import os
import re
import sys
import logging
from dataclasses import dataclass
from datetime import date
from http.client import HTTPSConnection
from base64 import b64encode
from typing import Optional, Set, List, Tuple

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class JiraVersion:
    id: str
    number: str


@dataclass(frozen=True)
class JiraIssue:
    status: str
    key: str


@dataclass(frozen=True)
class JiraConfig:
    url: str
    project_id: str
    project_key: str
    user_email: str
    user_token: str
    rfr_status_name: str
    done_transition_id: str


class JiraPluginException(Exception):
    pass


class JiraService:
    def __init__(self, jira_config: JiraConfig) -> None:
        self.jira_config = jira_config
        self.c = HTTPSConnection(jira_config.url)
        user_and_pass = b64encode(f"{jira_config.user_email}:{jira_config.user_token}".encode()).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {user_and_pass}",
            "Content-type": "application/json"
        }

    def execute(self, version: str, ticket_numbers: Set[str]):
        version = self.get_or_create_version(version)
        for ticket_number in ticket_numbers:
            jira_issue = self.get_jira_issue(ticket_number)
            if not jira_issue:
                logger.warning(f"Cannot process ticket [{ticket_number}] because it was not found in JIRA")
                continue
            self.assign_version_to_issue(version, jira_issue)
            self.transition_issue_to_done(jira_issue)

    def get_jira_issue(self, ticket_number: str) -> Optional[JiraIssue]:
        logger.info(f"Going to get issue with key [{ticket_number}]")
        get_issue_url = f"/rest/api/3/issue/{ticket_number}"

        code, resp_dict = self._send_get_request(get_issue_url)

        if code != 200:
            return None

        return JiraIssue(status=resp_dict["fields"]["status"]["name"], key=resp_dict["key"])

    def assign_version_to_issue(self, version: JiraVersion, issue: JiraIssue):
        logger.info(f"Going to assign ticket [{issue.key}] version [{version.number}]")
        assign_version_body = {
            "update": {
                "fixVersions": [
                    {"add": {"id": version.id}}
                ],
            }
        }
        assign_version_url = f"/rest/api/3/issue/{issue.key}"

        self._send_put_request(assign_version_url, assign_version_body)

    def transition_issue_to_done(self, issue: JiraIssue) -> bool:
        if issue.status.lower() != self.jira_config.rfr_status_name.lower():
            logger.warning(f"Cannot transition ticket [{issue.key}] with status [{issue.status}] to Done, it needs to be in 'Ready for Release' status")
            return False

        transition_issue_url = f"/rest/api/3/issue/{issue.key}/transitions"
        transition_issue_body = {
            "transition": {
                "id": self.jira_config.done_transition_id
            }
        }

        self._send_post_request(transition_issue_url, transition_issue_body)

    def get_or_create_version(self, version_number: str) -> JiraVersion:
        get_version_url = f"/rest/api/3/project/{self.jira_config.project_key}/version?query={version_number}"

        resp = self._send_get_request(get_version_url)
        for version in resp[1]["values"]:
            if version["name"] == version_number:
                logger.info(f"Found JIRA version with name [{version_number}]")
                return JiraVersion(id=version["id"], number=version["name"])

        logger.info(f"Going to create new JIRA version with name [{version_number}]")

        create_version_url = f"/rest/api/3/version"
        create_version_body = {
            "releaseDate": date.today().isoformat(),
            "released": True,
            "name": version_number,
            "projectId": self.jira_config.project_id
        }

        resp = self._send_post_request(create_version_url, body=create_version_body)[1]

        return JiraVersion(id=resp["id"], number=resp["name"])

    def _send_get_request(self, url) -> Tuple[int, dict]:
        logger.info(f"Going to send GET JIRA request to the url [{url}]")
        self.c.request("GET", url, headers=self.headers)
        return self._execute_request_and_return_dict()

    def _send_put_request(self, url, body: dict) -> Tuple[int, dict]:
        str_body = json.dumps(body)
        logger.info(f"Going to send PUT JIRA request to the url [{url}] with body [{str_body}]")
        self.c.request("PUT", url, headers=self.headers, body=str_body)
        return self._execute_request_and_return_dict()

    def _send_post_request(self, url, body: dict) -> Tuple[int, dict]:
        str_body = json.dumps(body)
        logger.info(f"Going to send POST JIRA request to the url [{url}] with body [{str_body}]")
        self.c.request("POST", url, headers=self.headers, body=str_body)
        return self._execute_request_and_return_dict()

    def _execute_request_and_return_dict(self) -> Tuple[int, dict]:
        response = self.c.getresponse()
        content = response.read()

        # log not 2xx responses
        if not 200 <= response.getcode() < 300:
            logger.warning(f"Non 2xx response [{response.getcode()}] with response body [{content}]")

        if not content:
            return response.getcode(), {}
        return response.getcode(), json.loads(content)


def parse_changelog_into_ticket_numbers(changelog: str) -> Set[str]:
    lines = changelog.split("\n")
    tic_numbers = list(map(parse_changelog_line_to_ticket_number, lines))
    return flatten_list_of_lists(tic_numbers)


def parse_changelog_line_to_ticket_number(changelog_line: str) -> List[str]:
    regex = re.compile(fr"{jira_project_key}-\d*")
    return regex.findall(changelog_line)


def flatten_list_of_lists(l: List[List[str]]) -> Set[str]:
    return {item for sublist in l for item in sublist}


def get_env_variable_or_raise(variable_name: str) -> str:
    value = os.environ.get(variable_name)
    if not value:
        raise JiraPluginException(f"Missing env variable [{variable_name}]")
    return value


if __name__ == '__main__':
    logger.info("Running Jira plugin of release-automation\n\n")

    logger.info("#################################################")
    logger.info("Starting extraction of environment variables\n")

    # Jira URL without www or https, e.g. abodeinauto.atlassian.net
    jira_url = get_env_variable_or_raise("JIRA_URL")

    # Email of the user which will be used to manipulate Jira data
    jira_user_email = get_env_variable_or_raise("JIRA_USER_EMAIL")

    # Jira personal user token (https://id.atlassian.com/manage-profile/security/api-tokens)
    jira_user_token = get_env_variable_or_raise("JIRA_USER_TOKEN")

    # Jira project key, usually 3 letters present in Jira issue key, like ADA-122
    jira_project_key = get_env_variable_or_raise("JIRA_PROJECT_KEY")

    # Jira project ID, retrieved via API (/rest/api/3/project/<project_key>)
    jira_project_id = get_env_variable_or_raise("JIRA_PROJECT_ID")

    # Jira Ready for Release status name, the one prior to Done
    jira_ready_for_release_status_name = get_env_variable_or_raise("JIRA_READY_FOR_RELEASE_STATUS_NAME")

    # Jira Done transition id, retrieved via API (/rest/api/3/issue/<any_project_issue_key>/transitions)
    # Look for the transition with correct name and pass the ID in this variable
    jira_done_transition_id = get_env_variable_or_raise("JIRA_DONE_TRANSITION_ID")

    jira_config = JiraConfig(jira_url, jira_project_id, jira_project_key, jira_user_email, jira_user_token, jira_ready_for_release_status_name, jira_done_transition_id)

    logger.info("Extraction of environment variables finished successfully")
    logger.info("#################################################\n\n")

    logger.info("#################################################")
    logger.info("Starting parsing of arguments passed into script\n")

    logger.info(f"Arguments passed to script: {sys.argv}")

    ver = sys.argv[1]
    tn = parse_changelog_into_ticket_numbers(sys.argv[2])

    logger.info(f"Version is [{ver}]")
    logger.info(f"Parsed ticket numbers are: {list(tn)}")

    logger.info("Parsing of arguments passed into script finished successfully")
    logger.info("#################################################\n\n")

    logger.info("#################################################")
    logger.info("Running the Jira Service\n")

    jira_service = JiraService(jira_config)
    operation = sys.argv[1]
    if operation == "release":
        jira_service.execute(ver, tn)
    elif operation == "verify":
        # TODO run verification of release

    logger.info("Jira Service ran successfully")
    logger.info("#################################################\n\n")

    logger.info("Jira plugin of release-automation finished successfully")
