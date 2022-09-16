# release-automation

release_script.sh is script used to perform following tasks automatically after each merge to main branch:

- creating a git tag based on parameter sent to the script
- generate changelog based on commit messages since last commit and pushing it into main branch
- merge main branch into develop branch after release


## Supported combinations of VCS and CI/CD tool

- [x] GitLab + GitLab CI
- [x] GitLab + Circle CI
- [x] BitBucket + Circle CI
- [ ] [Planned] GitHub + Circle CI


## Overview of setting up the release-automation script

1. specify version of release-automation you will use
2. specify git username and email for commits from CI
3. specify names of development and main git branches
4. generate the SSH key to push to repository from CI
5. add SSH key into CI/CD tool projects settings
6. include script execution in your CI/CD tool pipeline


## Specifying version of release-automation

To specify version of release-automation you will use, just add env variable `RA_VERSION` with valid git reference, like branch name, tag name, revision number etc.


## Specifying git username and email

Script is automatically creating some commits, such as changelog commit and merge of `main` branch to `development` branch. You need to set two environment variables inside your CI/CD project configuration to make commiting possible:

```
GIT_EMAIL=email-used-for-new-commits-in-ci
GIT_USERNAME=username-used-for-new-commits-in-ci
```

This is recommended configuration:

```
GIT_EMAIL=ci@<projectemaildomain>
GIT_USERNAME=<project_name> CI

# In case of Google:
GIT_EMAIL=ci@google.com
GIT_USERNAME=Google CI
```


## Specifying names of development and main git branches

Script needs to know which branches are main and develop, which you can specify by simply adding these two environment variables inside your CI/CD project configuration:

```
GIT_DEV_BRANCH=dev-branch-of-project
GIT_BRANCH=main-branch-of-project
```


## Generating the SSH key to push to repository from CI

By default, if you set up any VCS project inside any CI/CD tool, most of them use read-only access key to check out the code. Therefore push is prohibited and that's something needed to be allowed before running the script. In following subsections are instructions how to generate a key with deploy rights, you will use that key later.


### GitLab + GitLab CI

In GitLab project to `Settings` -> `Access Tokens` and create new access token with `read_repository` and `write_repository` permissions and assign it role `Maintainer`. Copy the key ID, you will use it later.


### GitLab + Circle CI


Generate new SSH key using guide in Help section. Open the project on GitLab and copy the content of `id_rsa.pub` into `Settings` -> `Repository` -> `Deploy Keys`. Make sure the option `Grant write permissions to this key` is checked and save the key


### BitBucket + CircleCI

You will need to create BitBucket user specifically for this project. Then, generate new SSH key using guide in Help section. Go to the newly created user `Personal Settings` -> `SSH Keys` -> `Add key` and copy the content of `id_rsa.pub` there.


## Adding SSH key into CI/CD tool projects settings

### GitLab + Circle CI

Open Circle CI project, go to `Project settings` -> `SSH Keys` -> `Additional SSH Keys` and add previously created key there. Leave hostname empty.


### GitLab + GitLab CI

Add environment variable `GIT_TOKEN` inside your CI/CD project settings, where you will pass the copied Key ID from previous step.


### BitBucket + Circle CI

https://support.circleci.com/hc/en-us/articles/360003174053-How-Do-I-Add-a-Bitbucket-User-Key-

After adding this key, you need to delete `Deploy Key` that was previously added there.

## Including script execution in CI/CD tool pipeline


### GitLab + GitLab CI

Add another `stage` called `post-release` into your config:

```
stages:
  ... any other stages
  - post-deploy
```

Add following step into your `.gitlab-ci.yml` file:

```
release:
  stage: post-deploy
  image: cimg/python:3.8-node
  rules:
    - if: '$CI_COMMIT_BRANCH == $GIT_BRANCH'
  script:
    - git remote set-url origin https://${CI_REGISTRY_USER}:${GIT_TOKEN}@${CI_REPOSITORY_URL#*@}
    - VERSION=$(poetry version --short)
    - bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/main/release_script.sh) $VERSION
```


## GitLab/BitBucket + Circle CI

Add new job into your pipeline, after the `deploy` job:

```
release:
    docker:
      - image: cimg/python:3.8.12-node
    working_directory: ~/repo
    steps:
      - checkout
      - run:
          name: release
          command: |
            VERSION=$(poetry version --short)
            bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/main/release_script.sh) $VERSION
```

And then add it to your workflows section:

```
- release:
    filters:
      branches:
        only:
          - <name-of-main-branch>
```

> NOTE: putting $GIT_BRANCH instead of name of main branch does not work here


## Jira Plugin

Jira plugin is plugin of release-automation which allows you
to automatically create Jira versions, assign released tickets to them and move them to `Done` status. 
With Jira automation you can also post Slack messages with released changes to communication canals to directly
notify stakeholders.


### Enabling Jira plugin

To enable Jira plugin, you need to set `RA_JIRA_PLUGIN` env variable to `1`.


### Choosing user to use with Jira

In order to manage data in Jira, you need to have Jira user.
You can either use account of one of the people working on project.
However, suggested way is to create a new user specifically for this automation script.
After choosing user, you need to create a token for him on this page: 
https://id.atlassian.com/manage-profile/security/api-tokens


### Getting required variables for Jira plugin

Some of the variables required for Jira plugin are easy to get.
However, for some of them you need to use the API.
In this section, you will learn how to get required variables from API.

In commands, you will need a few variables:

- `<your_jira_url>` - something like `henrich-hanusovsky.atlassian.net`
- `<your_jira_project_key>` - usually 3 chars string, contained in ticket numbers, like `TES-111` (in this case the project key is `TES`)
- `<your_jira_ticket>` - any of the currently existing Jira tickets in your project, in format `TES-111`
- `<authorization>` - base64 encode of following string `<your_jira_user_email>:<your_jira_user_token>`


Project ID. In response, find `id`.:

```
curl --location --request GET 'https://<your_jira_url>/rest/api/3/project/<your_jira_project_key>' \
--header 'Authorization: Basic <authorization>' \
```

`Done` transition ID. In response, go to `transitions` and find the one with `name` attribute corresponding to your `Done` Jira status. From there, copy the `id`.

```
curl --location --request GET 'https://<your_jira_url>/rest/api/3/issue/<your_jira_ticket>/transitions' \
--header 'Authorization: Basic <authorization>' \
```


### Configuring Jira plugin

The list of required env variables for Jira plugin to run successfully:

- `JIRA_URL` without the `https` or `www`, something like `henrich-hanusovsky.atlassian.net`
- `JIRA_USER_EMAIL` - email of user selected to perform operations
- `JIRA_USER_TOKEN` - token of user selected to perform operations
- `JIRA_PROJECT_KEY` - usually 3 chars string, contained in ticket numbers, like `TES-111` (in this case the project key is `TES`)
- `JIRA_PROJECT_ID` - ID of project aquired from API, see previous section
- `JIRA_DONE_TRANSITION_ID` - ID of `Done` status transition aquired from API, see previous section
- `JIRA_READY_FOR_RELEASE_STATUS_NAME` - name of status prior to `Done` status, like 'Ready for Relase', case does not matter (only tickets in this status will be moved to done, other will stay in their columns, like 'Progress' or 'Ready for QA')


## Help

### Generating SSH Key

You can generate SSH key by running command `ssh-keygen -t rsa -b 4096 -C "ci@example.com" -f ./id_rsa` anywhere on your computer. It will create ssh keys for you in current location, `id_rsa.pub` will be the public key, `id_rsa` will be private key.