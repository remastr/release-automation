# Remaster Git branching strategy + Release process

This document describes the Git branching strategy and also release process that play well together and make developers life easier. This combination aims to be:

- reusable among the variety of projects
- easy
- automated
- customized specifically for our tech stack


## Git branching Strategy

Recommended git strategy consists of several types of branches:

- production - `main`
- development - `dev`
- feature - `feature/<jira-ticket>` or `feature/<feature-description>`
- fix - `fix/<jira-ticket>` or `fix/<sentry-issue>` or `fix/<fix-description>`
- release - `release/<version>`
- hotfix - `hotfix/<version>`


### Development and production branches

Nothing special, one intended for development and one intended for production application. It is highly recommended to keep these branches protected, not allowing force pushing into them and also possibly restricting pushing to these branches.


### Feature and fix branches

Used for development of new features or fixing bugs, these branches are checkout out from development branch. Important part about feature and fix branches are how they are merged back into the development branch.

I highly recommend using squashing of commits in each branch before merging or rebasing them back into the development branch. 
It results in clearer git history and more readable commits, where each feature will be represented by one commit in development branch.
This feature can be allowed in your Git platform settings.


### Release and hotfix branches

Used for releases, find more about them in following sections. Important note here is that when merging these two branches into production, you should **never** use squashing option, because by this strategy you will merge all features previously developed into one commit.

Also in case of having staging environmnent, these two types of branches should be deployed to staging environment.


## Types of releases and differences between them

There are two types of releases allowed and supported:

1. release - release of new features from develop branch into production
2. hotfix - fix of some bug directly on production

The only difference between them is that in case of release you should branch from the development branch and it aims to release new features. 

In case of hotfix you should branch from the production branch and it aims to fix burning bugs on production. Find more about them in later sections.

Other steps are common and described in next section.


## General release process

All types of releases follow one common, general release process which consists of following steps.


### 1. Determining what you want to release

First step is to determine what we want to release. Remember you are not specifically tight to some branch, like development branch. If there are some commits you want to avoid you are totally able to do that. 

The only thing I would recommend is folllowing the linear git history. For example, if you have three features merged into development in this order:

- `Feature 1` as first one
- `Feature 2` as second one
- `Feature 3` as third one

In this case, if you want to include `Feature 3` in your release, there is no easy way to exclude `Feature 2` from release. It can be done in 2 ways:

1. create release branch from `Feature 3` and revert `Feature 2` in release branch
2. create release branch from `Feature 1` and cherry pick `Feature 3` into release branch

Both these approaches have their specific disadvantages and they should be done in case of absolute need. 

However, if you want to exclude `Feature 3` from release you can absolutely do that, because you are keeping the linear git history and `Feature 3` can be released in next version.


### 2. Creating release/hotfix branch

#### Release

```
git checkout <development-branch-or-revision-to-release>
git checkout -b release/<version>
```

Usually, in the first checkout command, you checkout the development branch.

As mentioned in previous section, if there is something in development branch you don't want to release, feel free to checkout some previous revision providing commit hash into first checkout command. This option plays well with staging environment, where you have a possibility to check everything before pushing it into production.


#### Hotfix

```
git checkout <production-branch>
git checkout -b hotfix/<version>
```

In case of hotfix, you should always check out from the production branch.


### 3. Updating version of application

For application versioning, you should use default option, which is `npm` or `poetry`. You should follow the [semantic versioning](https://semver.org/).

```
poetry version <major/minor/patch>
or
npm version <major/minor/patch>
```

After you have updated the version of application, you need to commit this change into remote repository, into release/hotfix branch:

```
git commit -am "chore: Version bump"
git push --set-upstream origin <release-or-hotfix-branch-name>
```


### 4. Create pull request from release/hotfix branch to production

Visit your Git platform website and create PR from release/hotfix branch into production.


### 5. Test your release

If you are using staging environment, test and verify release on staging.

> NOTE: In case you are not using staging environment all the releases should be verified previously on development. Hotfixes will always be risky, so you should only make hotfixes where you are 100% sure about safety.


### 6. Merge pull request

It is highly recommended to have `release-automation` script integrated into your project, since it is taking care of most things needed to be done after this step.

## Hotfixes - when and how to use them

Advantage of hotfix is that you are not blocked by anything that was developed in development branch and is not yet ready to be released, allowing to fix bugs on production immediately.

Hotfixes play well with staging environment, because you have one additional environment where you are able to test your changes before pushing them to production. 
If your project does not have staging environment, you should create only hotfixes where you are 100% sure about their safety, because you will not be able to test your integration anywhere before going to production.