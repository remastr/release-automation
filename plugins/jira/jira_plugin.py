import enum
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
    released_to_staging_transition_id: str

    def validate(self, jira_operation: JiraOperation) -> None:
        """
        Raises exception if some required parameter is missing for the specified operation
        :param jira_operation:
        :return:
        """
        required_parameters = ["url", "project_id", "project_key", "user_email", "user_token"]
        if jira_operation == JiraOperation.VERIFY:
            required_parameters.extend(["rfr_status_name", "done_transition_id"])
        elif jira_operation == JiraOperation.RELEASE:
            required_parameters.extend(["released_to_staging_transition_id"])

        for param in required_parameters:
            if not getattr(self, param):
                raise JiraPluginException(f"Missing required parameter [{name}]")


class JiraPluginException(Exception):
    pass


class JiraOperation(enum.Enum):
    RELEASE = "release"
    VERIFY = "verify"


class JiraService:
    def __init__(self, jira_config: JiraConfig) -> None:
        self.jira_config = jira_config
        self.c = HTTPSConnection(jira_config.url)
        user_and_pass = b64encode(f"{jira_config.user_email}:{jira_config.user_token}".encode()).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {user_and_pass}",
            "Content-type": "application/json"
        }

    def verify(self, ticket_numbers: Set[str]):
        self.jira_config.validate(JiraOperation.VERIFY)
        for ticket_number in ticket_numbers:
            jira_issue = self.get_jira_issue(ticket_number)
            if not jira_issue:
                logger.warning(f"Cannot process ticket [{ticket_number}] because it was not found in JIRA")
                continue
            self.transition_issue_to_staging(jira_issue)

    def release(self, version: str, ticket_numbers: Set[str]):
        self.jira_config.validate(JiraOperation.RELEASE)
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
        # If you are using release-verification plugin than it is not necessary to check for current status of issue
        if not self.jira_config.released_to_staging_transition_id and issue.status.lower() != self.jira_config.rfr_status_name.lower():
                logger.warning(f"Cannot transition ticket [{issue.key}] with status [{issue.status}] to Done, it needs to be in 'Ready for Release' status")
                return False

        transition_issue_url = f"/rest/api/3/issue/{issue.key}/transitions"
        transition_issue_body = {
            "transition": {
                "id": self.jira_config.done_transition_id
            }
        }

        self._send_post_request(transition_issue_url, transition_issue_body)
        return True

    def transition_issue_to_staging(self, issue: JiraIssue) -> bool:
        transition_issue_url = f"/rest/api/3/issue/{issue.key}/transitions"
        transition_issue_body = {
            "transition": {
                "id": self.jira_config.released_to_staging_transition_id
            }
        }

        self._send_post_request(transition_issue_url, transition_issue_body)
        return True

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


if __name__ == '__main__':
    logger.info("Running Jira plugin of release-automation\n\n")

    logger.info("#################################################")
    logger.info("Starting extraction of environment variables\n")

    # Jira URL without www or https, e.g. abodeinauto.atlassian.net
    jira_url = os.environ.get("JIRA_URL", None)

    # Email of the user which will be used to manipulate Jira data
    jira_user_email = os.environ.get("JIRA_USER_EMAIL", None)

    # Jira personal user token (https://id.atlassian.com/manage-profile/security/api-tokens)
    jira_user_token = os.environ.get("JIRA_USER_TOKEN", None)

    # Jira project key, usually 3 letters present in Jira issue key, like ADA-122
    jira_project_key = os.environ.get("JIRA_PROJECT_KEY", None)

    # Jira project ID, retrieved via API (/rest/api/3/project/<project_key>)
    jira_project_id = os.environ.get("JIRA_PROJECT_ID", None)

    # Jira Ready for Release status name, the one prior to Done
    jira_ready_for_release_status_name = os.environ.get("JIRA_READY_FOR_RELEASE_STATUS_NAME", None)

    # Jira 'Done' transition id, retrieved via API (/rest/api/3/issue/<any_project_issue_key>/transitions)
    # Look for the transition with correct name and pass the ID in this variable
    jira_done_transition_id = os.environ.get("JIRA_DONE_TRANSITION_ID", None)

    # Jira 'Released on staging' transition id
    # retrieved via API (/rest/api/3/issue/<any_project_issue_key>/transitions)
    # Look for the transition with correct name and pass the ID in this variable
    jira_released_on_staging_transition_id = os.environ.get("JIRA_RELEASED_ON_STAGING_TRANSITION_ID", None)

    jira_config = JiraConfig(jira_url, jira_project_id, jira_project_key, jira_user_email, jira_user_token, jira_ready_for_release_status_name, jira_done_transition_id, jira_released_on_staging_transition_id)

    logger.info("Extraction of environment variables finished successfully")
    logger.info("#################################################\n\n")

    logger.info("#################################################")
    logger.info("Starting parsing of arguments passed into script\n")

    logger.info(f"Arguments passed to script: {sys.argv}")

    ver = sys.argv[2]
    tn = parse_changelog_into_ticket_numbers(sys.argv[3])

    logger.info(f"Version is [{ver}]")
    logger.info(f"Parsed ticket numbers are: {list(tn)}")

    logger.info("Parsing of arguments passed into script finished successfully")
    logger.info("#################################################\n\n")

    logger.info("#################################################")
    logger.info("Running the Jira Service\n")

    jira_service = JiraService(jira_config)
    operation = JiraOperation(sys.argv[1])
    if operation == JiraOperation.RELEASE:
        jira_service.release(ver, tn)
    elif operation == JiraOperation.VERIFY:
        jira_service.verify(tn)

    logger.info("Jira Service ran successfully")
    logger.info("#################################################\n\n")

    logger.info("Jira plugin of release-automation finished successfully")
