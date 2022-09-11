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

1. specify git username and email for commits from CI
2. specify names of development and main git branches
3. generate the SSH key to push to repository from CI
4. add SSH key into CI/CD tool projects settings
5. include script execution in your CI/CD tool pipeline


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


### GitLab + Circle CI/GitLab CI


Generate new SSH key using guide in Help section. Open the project on GitLab and copy the content of `id_rsa.pub` into `Settings` -> `Repository` -> `Deploy Keys`. Make sure the option `Grant write permissions to this key` is checked and save the key


### BitBucket + CircleCI

You will need to create BitBucket user specifically for this project. Then, generate new SSH key using guide in Help section. Go to the newly created user `Personal Settings` -> `SSH Keys` -> `Add key` and copy the content of `id_rsa.pub` there.


## Adding SSH key into CI/CD tool projects settings

### GitLab + Circle CI

Open Circle CI project, go to `Project settings` -> `SSH Keys` -> `Additional SSH Keys` and add previously created key there. Leave hostname empty.


### GitLab + GitLab CI

Add environment variable `GIT_PUSH_KEY` inside your CI/CD project settings, where you will pass private key created in previous step.


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
  before_script:
    - mkdir ~/.ssh/
    - ssh-keyscan $CI_SERVER_HOST > ~/.ssh/known_hosts
    - echo "${GIT_PUSH_KEY}" > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - git remote remove origin || true  # Local repo state may be cached
    - git remote add origin "git@$CI_SERVER_HOST:$CI_PROJECT_PATH.git"
  script:
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


## Help

### Generating SSH Key

You can generate SSH key by running command `ssh-keygen -t rsa -b 4096 -C "ci@example.com" -f ./id_rsa` anywhere on your computer. It will create ssh keys for you in current location, `id_rsa.pub` will be the public key, `id_rsa` will be private key.