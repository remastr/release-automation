# release-automation

release_script.sh is script used to perform following tasks automatically after each merge to main branch:

- creating a git tag based on parameter sent to the script
- generate changelog based on commit messages since last commit and pushing it into main branch
- merge main branch into develop branch after release

It has also support for plugins, currently available plugins are:

- JIRA plugin
- Release-verification plugin

> NOTE: You can find each plugin in `plugins` directory and documentation to this plugin in `README.md` file inside each plugin


## Supported combinations of VCS and CI/CD tool

- [x] GitLab + GitLab CI
- [x] GitLab + Circle CI
- [x] BitBucket + Circle CI
- [x] GitHub + Circle CI


## Overview of setting up the release-automation script

1. specify version of release-automation you will use
2. specify git username and email for commits from CI
3. specify names of development and main git branches
4. choose the user which will be making changes in repository
5. generate the SSH key to push to repository from CI
6. add SSH key into CI/CD tool projects settings
7. figuring out command to get current project version
8. include script execution in your CI/CD tool pipeline


## 1. Specifying version of release-automation

To specify version of release-automation you will use, just add env variable `RA_VERSION` with valid git reference, like branch name, tag name, revision number etc. 
Most of the time you want to use the latest stable version, find releases here: https://github.com/remastr/release-automation/releases


## 2. Specifying git username and email

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


## 3. Specifying names of development and main git branches

Script needs to know which branches are main and develop, which you can specify by simply adding these two environment variables inside your CI/CD project configuration:

```
GIT_DEV_BRANCH=dev-branch-of-project
GIT_BRANCH=main-branch-of-project
```


## 4. Choosing the user/project for making changes in repository

In following few sections, you will also work with your git system and you will need to setup the credentials (keys) for user/project. 
These credentials will be used to push commits and tags.

For the project, just choose the project for which you are implementing release-automation.

For the user, there are two strategies:

- create new user specifically for this release-automation script and any other automated things in future (highly recommended)
- use already existing user

Whenever there will be git user/project addressed in the following sections, it means whichever user/project you have chosen in this step.

> NOTE: when you will be working with user, don't forget he needs push privileges to both production and development git branch

> NOTE: you don't need to create user rightaway, it might be that your setup will not require user, just project. Whenever you will be asked to assign something to git user, then make a choice and create/reuse one.


## 5. Generating the SSH key to push to repository from CI

By default, if you set up any VCS project inside any CI/CD tool, most of them use read-only access key to check out the code. Therefore push is prohibited and that's something needed to be allowed before running the script. In following subsections are instructions how to generate a key with deploy rights, you will use that key later.


### GitLab + GitLab CI

In GitLab project go to `Settings` -> `Access Tokens` and create new access token with `read_repository` and `write_repository` permissions and assign it role `Maintainer`. Copy the key ID, you will use it later.

If for some reason you don't have the `Access tokens` available inside the settings, you can also create a token for git user and use this one. In this case, go to `User Settings` -> `Access Tokens` and create new access token with `read_repository` and `write_repository` permissions. Copy the key ID, you will use it later.


### GitLab + Circle CI

Generate new SSH key using guide in Help section. Open the project on GitLab and copy the content of public key into `Settings` -> `Repository` -> `Deploy Keys`. Make sure the option `Grant write permissions to this key` is checked and save the key


### GitHub + Circle CI

Generate new SSH key using guide in Help section. Open the project on GitHub and copy the content of public key into projects `Settings` -> `Deploy Keys` -> `Add deploy key` -> `Key`. Check the checkbox `Allow write access` and give the key whatever title, e.g. `CI push key`. Save the key.


### BitBucket + CircleCI

For this configuration, this step is unnecessary. The key will be generated for you in next step.


## 6. Adding SSH key into CI/CD tool projects settings

### GitLab + GitLab CI

Add environment variable `GIT_TOKEN` inside your CI/CD project settings, where you will pass the copied Key ID from previous step.


### GitLab + Circle CI

Open Circle CI project, go to `Project settings` -> `SSH Keys` -> `Additional SSH Keys` and add previously created private key there. Leave hostname empty.


### GitHub + Circle CI

Go to `Project settings` -> `SSH Keys` and under `Additional SSH keys section` add key with hostname `github.com` (important - documentation says it can stay blank but it is not working with blank `Hostname` field). To `private key` field you can paste the content of previously generated private ssh key.


### BitBucket + Circle CI

https://support.circleci.com/hc/en-us/articles/360003174053-How-do-I-add-a-BitBucket-user-key-

After adding this key, you need to delete `Deploy Key` that was previously added automatically in Circle CI. Also do not forget to follow last step of the CircleCI guide provided above to put the key into the BitBucket.


## 7. Figuring out command to get current project version

Since the project version is specified inside project configuration file, 
it needs to be retrieved. Commands for version retrieval:

Poetry:
`poetry version --short`

NPM:
`npm pkg get version | sed 's/"//g'`

This command will be used in next step.


## 8. Including script execution in CI/CD tool pipeline


### GitLab + GitLab CI

Add another `stage` called `post-deploy` into your config:

```
stages:
  ... any other stages
  - post-deploy
```

Add following step into your `.gitlab-ci.yml` file:

```
variables:
  GIT_DEPTH: 0

release:
  stage: post-deploy
  image: cimg/python:3.8-node
  rules:
    - if: '$CI_COMMIT_BRANCH == $GIT_BRANCH'
  script:
    - git remote set-url origin https://${CI_REGISTRY_USER}:${GIT_TOKEN}@${CI_REPOSITORY_URL#*@}
    - VERSION=$(<comamnd-to-get-projects-version>)
    - bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/$RA_VERSION/release_script.sh) $VERSION
```


### GitLab/BitBucket/GitHub + Circle CI

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
            VERSION=$(<comamnd-to-get-projects-version>)
            bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/$RA_VERSION/release_script.sh) $VERSION
```

If you are using GitHub, you also need to add another step before checkout, which will add the previously generated ssh key fingerprint. You will find it in Circle CI, in `Project settings` -> `SSH Keys` and under `Additional SSH Keys` copy the Fingerprint of your added key. Then add this step before checkout step in this job:

```
release:
  ...
  steps:
    - add_ssh_keys:
        fingerprints:
          - "ssh-key-fingerprint"
    - checkout
    ... 
```


And then add it to your workflows section:

```
- release:
    requires:
      - deploy
    filters:
      branches:
        only:
          - <name-of-main-branch>
```

> NOTE: putting $GIT_BRANCH instead of name of main branch does not work here


## Help

### Generating SSH Key

You can generate SSH key by running command `ssh-keygen -t rsa -b 4096 -C "ci@example.com" -f ./id_rsa` anywhere on your computer. It will create ssh keys for you in current location, `id_rsa.pub` will be the public key, `id_rsa` will be private key.
