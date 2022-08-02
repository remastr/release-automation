# release-automation

## GitLab + GitLab CI


## GitLab + Circle CI

### Env variables



###

Default setup for Circle CI does not work because the key which it is created with has no write access to repository.

Also, if the Circle CI project was created with GitLab, you are unable to specify `Deploy key` inside the `SSH Keys` in project settings. This would pretty much fix push issue, but it is unavailable for GitLab projects so far.

The way to do it is to create read-write SSH key pair and replace the one assigned by default with the new read-write pair. This is done in project settings, in `SSH Keys` -> `Additional SSH Keys` -> `Add SSH Key`. It is best to use some dummy user with access only to one project you want to use it for (in case the key is somehow lost).