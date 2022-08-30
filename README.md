# release-automation

release_script.sh is script used to perform following tasks automatically after each merge to main branch:

- creating a tag based on version in pyproject.toml
- generate changelog based on commit messages since last commit and pushing it into main branch
- merge main branch into develop branch after release


## Supported combinations of VCS and CI/CD tool

- [x] GitLab + GitLab CI
- [x] GitLab + Circle CI
- [x] BitBucket + Circle CI
- [ ] [Planned] GitHub + Circle CI

## Setting up the Script

### Environment variables

In order to run the script, it requires several environment variables specified in your CI/CD project configuration. These variables are used to specify the git settings for commiting, pushing etc.

```
GIT_DEV_BRANCH=dev-branch-of-project
GIT_BRANCH=main-branch-of-project
GIT_EMAIL=email-used-for-new-commits-in-ci
GIT_USERNAME=username-used-for-new-commits-in-ci
```
> *NOTE: GitLab + GitLab CI requires also `PUSH_SSH_KEY` variable set to access token to GitLab project, see more in "SSH Keys" section* 


## SSH Keys

By default, if you set up any VCS project inside any CI/CD tool, most of them use read-only access key to check out the code. Therefore push is prohibited and that's something needed to be allowed before running the script.


### GitLab + GitLab CI

You need to generate new ssh key by executing `ssh-keygen -t rsa -b 4096 -C "ci@example.com" -f ./id_rsa`. It will create ssh key for you in current location. Copy the content of `id_rsa.pub` into `Project -> Settings -> Repository -> Deploy keys` and check `Grant write permissions to this key`.

The content of `id_rsa` needs to be saved in `SSH_PUSH_KEY` env variable inside GitLab CI settings. Then, in release step (see section "Including script in CI/CD tool") you need to add before script section to use this key.

```
before_script:
    - mkdir ~/.ssh/
    - ssh-keyscan $CI_SERVER_HOST > ~/.ssh/known_hosts
    - echo "${GIT_PUSH_KEY}" > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - git remote remove origin || true  # Local repo state may be cached
    - git remote add origin "git@$CI_SERVER_HOST:$CI_PROJECT_PATH.git"
```


### GitLab + Circle CI


### BitBucket + Circle CI


## Getting version of application to pass into script

In order to run the script, you need to extract the current application version (you will pass that as argument to script later on).

### Poetry

`poetry version --short`


## Including script in CI/CD tool


### Gitlab + Gitlab CI


```
stages:
  ... any other stages
  - post-deploy

release:
  stage: post-deploy
  image: cimg/python:3.8-node
  rules:
    - if: '$CI_COMMIT_BRANCH == "<name-of-your-main-branch>"'
  variables:
    GIT_BRANCH: $CI_COMMIT_BRANCH
  script:
    - VERSION=$(<command-to-get-version>)
    - bash <(curl -s https://raw.githubusercontent.com/remastr/release-automation/<version-of-script>/release_script.sh) $VERSION
```

DEPRECATED

### Combination specifics

Some combinations of VCS and CI/CD tool require also additional settings because of the way how they checkout code or manage SSH keys. 
If any specific requirement exists for your combination, you will find it here.

### Gitlab + GitLab CI specifics

##### SSH key

GitLab CI by default checkouts the repository with read-only access. To be able to push to repository, you need to do following:

- add `GIT_TOKEN` environment variable


## GitLab + GitLab CI


## GitLab + Circle CI

### Env variables

glpat-Q_n9sGgmNzWLTbxqp9fw

###

Default setup for Circle CI does not work because the key which it is created with has no write access to repository.

Also, if the Circle CI project was created with GitLab, you are unable to specify `Deploy key` inside the `SSH Keys` in project settings. This would pretty much fix push issue, but it is unavailable for GitLab projects so far.

The way to do it is to create read-write SSH key pair and replace the one assigned by default with the new read-write pair. This is done in project settings, in `SSH Keys` -> `Additional SSH Keys` -> `Add SSH Key`. It is best to use some dummy user with access only to one project you want to use it for (in case the key is somehow lost).


## BitBucket + Circle CI

## SSH Key
https://support.circleci.com/hc/en-us/articles/360003174053-How-Do-I-Add-a-Bitbucket-User-Key-