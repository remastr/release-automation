TODO make it work also without staging environment
TODO add optional flag to not run JIRA plugin on verification, but run on release

# Release-verification Plugin

Release-verification is plugin of release-automation which allows you
to verify that release can be proceeded (e.g. version is not yet existing as git tag).
If you use JIRA plugin at the same time, it moves tickets in Jira which are currently being released to another column (for easier testing). The tickets that were not in `Ready for Release` column before moving them to `Released on Staging` are flagged for easier identification of potentially untested tickets being deployed to production.


## Overview of setting up the release-automation script

1. include script execution in your CI/CD tool pipeline
2. configure JIRA plugin - only if you are using JIRA plugin


## 1. Including script execution in CI/CD tool pipeline


### GitLab CI

Add another `stage` called `release-verification` (before `post-deploy`) into your config:

```
stages:
  ... any other stages
  - release-verification
  - post-deploy
```

Add following step into your `.gitlab-ci.yml` file:

```
release-verification:
  stage: release-verification
  image: cimg/python:3.8-node
  rules:
    - if: '$CI_COMMIT_BRANCH =~ "/^release\/.+$/" || $CI_COMMIT_BRANCH =~ "/^hotfix\/.+$/"'
  script:
    - VERSION=$(poetry version --short)
    - bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/$RA_VERSION/plugins/release-verification/release_verification.sh) $VERSION
```

## 2. Configuring JIRA version plugin

If you are using JIRA plugin, you need to configure some additional settings to make it work.

There is a way to get the `Done` transition ID described in section 3 of JIRA plugin readme file. Follow this section but instead of `Done` tranisition ID you will need to find the `Released on Staging` transition ID. 

For flagging functionality, you need to get the "Flagged" custom field ID. "Flagged" is not standard field accessible by its name, but it is custom one and needs to be accessed via ID. For getting this ID follow JIRA plugin README file, 3rd section and following URL: 

```
curl --location --request GET 'https://<your_jira_url>/rest/api/3/issue/<your_jira_ticket>?expand=names' \
--header 'Authorization: Basic <authorization>'
```

And in response, find `names` and custom field with value "Flagged". In this case, it is `customfield_10021`:

```
...
"names": {
  "customfield_10021": "Flagged",
  ...
}
...
```

Then set these two as variables in your CI/CD tool:
```
JIRA_RELEASED_ON_STAGING_TRANSITION_ID - Transition ID aquired from API
JIRA_FLAG_CUSTOM_FIELD_ID - custom field ID aquired from API
JIRA_RELEASED_ON_STAGING_STATUS_NAME - name of status prior to `Done` status
```
