# Jira Plugin

Jira plugin is plugin of release-automation which allows you
to automatically create Jira versions, assign released tickets to them and move them to `Done` status. 
With Jira automation you can also post Slack messages with released changes to communication channels to directly notify stakeholders.


## Overview of setting up the release-automation script

1. enable Jira plugin
2. choose Jira user to use with Jira plugin
3. get required variables for Jira plugin
4. configure Jira plugin


## 1. Enabling Jira plugin

To enable Jira plugin, you need to set `RA_JIRA_PLUGIN` CI environment variable to `1`.


## 2. Choosing Jira user to use with Jira plugin

In order to manage data in Jira, you need to have Jira user.
You can either use account of one of the people working on project.
However, suggested way is to create a new user specifically for this automation script.
After choosing user, you need to create a token for him on this page: 
https://id.atlassian.com/manage-profile/security/api-tokens


## 3. Getting required variables for Jira plugin

Some of the variables required for Jira plugin are easy to get.
However, for some of them you need to use the API.
In this section, you will learn how to get required variables from API.

In commands, you will need a few variables:

- `<your_jira_url>` - something like `remaster.atlassian.net`
- `<your_jira_project_key>` - string contained in ticket numbers, like `TES-111` (in this case the project key is `TES`)
- `<your_jira_ticket>` - any of the currently existing Jira tickets in your project, in format `TES-111`
- `<authorization>` - base64 encode of following string `<your_jira_user_email>:<your_jira_user_token>`


### Project ID

In response, find `id`.:

```
curl --location --request GET 'https://<your_jira_url>/rest/api/3/project/<your_jira_project_key>' \
--header 'Authorization: Basic <authorization>' \
```

### `Done` transition ID

In response, go to `transitions` and find the one with `name` attribute corresponding to your `Done` Jira status. From there, copy the `id` (the one directly in transition, not under the `to` parameter inside this transition).

```
curl --location --request GET 'https://<your_jira_url>/rest/api/3/issue/<your_jira_ticket>/transitions' \
--header 'Authorization: Basic <authorization>' \
```


## 4. Configuring Jira plugin

Following variables are required for Jira plugin to run successfully and need to be specified in your CI project environment variables.

- `JIRA_URL` without the `https` or `www`, something like `remaster.atlassian.net`
- `JIRA_USER_EMAIL` - email of user selected to perform operations
- `JIRA_USER_TOKEN` - API token of user selected to perform operations
- `JIRA_PROJECT_KEY` - string contained in ticket numbers, like `TES-111` (in this case the project key is `TES`)
- `JIRA_PROJECT_ID` - ID of project aquired from API, see previous section
- `JIRA_DONE_TRANSITION_ID` - ID of `Done` status transition aquired from API, see previous section
- `JIRA_READY_FOR_RELEASE_STATUS_NAME` - name of status prior to `Done` status, like 'Ready for Relase', casing does not matter (only tickets in this status will be moved to `Done`, other will stay in their columns - to not move tickets e.g. from testing column to `Done` status accidentaly)