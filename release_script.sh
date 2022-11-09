### PARSE POSITIONAL ARGUMENTS
VERSION=$1

### CHECK FOR REQUIRED ENV VARIABLES

echo "Checking required environment variables"
REQUIRED_VARIABLES=("GIT_BRANCH" "GIT_DEV_BRANCH" "GIT_USERNAME" "GIT_EMAIL")

# Iterates over REQUIRED_VARIABLES and exits if it is not specified
for val in "${REQUIRED_VARIABLES[@]}"; do
  if [ -z ${!val+x} ]; then echo "Required variable '$val' is not set"; exit 1; fi
done

### FETCHING WHOLE REPOSITORY
# Fetch is needed because most CIs are performing only shallow pull
# This ensures the script will run correctly under any circumstances

echo "Running 'git fetch' command"
git fetch

git checkout v2.7.0

git --no-pager log --format="%h  %s (%an)" --no-merges HEAD~1..HEAD

exit 1


### VARIABLES SETUP

echo "Setting up variables"

# Merge commit details
MERGE_COMMIT_MESSAGE=$(git log -1 --format="%s")
MERGE_COMMIT_AUTHOR=$(git log -1 --format="%an")

# Changelog for all commits merged to this branch since last commit on this branch
echo "Creating changelog content"
CHANGELOG=$(git --no-pager log --format="%h  %s (%an)" --no-merges HEAD~1..HEAD)
echo $CHANGELOG

exit 1

# Regex for searching the release version in commit message
# Not Used currently
RE="([0-9]+\.[0-9]+)"


### GIT SETUP

# This is set to not open any editor app while merging the branches, otherwise it would fail
# error: Terminal is dumb, but EDITOR unset
GIT_MERGE_AUTOEDIT=no

# Git variables setup
git config --global user.email "$GIT_EMAIL"
git config --global user.name "$GIT_USERNAME"


### TAG CREATION

# Tag needs to be created before the git fetch to have the tag on HEAD where the pipeline is executed, not on HEAD of main branch
# Create tag for version and push it to remote
echo "Going to tag the git with version v$VERSION"
git tag "v$VERSION"
git push origin "v$VERSION";


### FLOW

# Checking out prod branch
if ! git checkout "$GIT_BRANCH";
then
  echo "Could not checkout the branch $GIT_BRANCH provided in GIT_BRANCH env variable"
  exit 1
fi

# This ensures the local prod branch is up to date with the remote one
# Sometimes it happens that local branch is somehow behind some commits and then merging fails
# Also pulling didn't help here on GitLab CI
if ! git reset --hard "origin/$GIT_BRANCH";
then
  echo "Could not reset $GIT_BRANCH branch to the origins state"
  exit 1
fi


# Create changelog and write it to file
echo "Creating changelog directory"
mkdir changelog
CHANGELOG_FILE="changelog/$VERSION"
echo "Writing changelog content into the file"
echo "Release $VERSION merged to production on $(date) by $MERGE_COMMIT_AUTHOR" > "$CHANGELOG_FILE"
printf "\nReleased changes:\n" >> "$CHANGELOG_FILE"
echo "$CHANGELOG" >> "$CHANGELOG_FILE"

# Commit and push the changelog changes
echo "Committing changelog file to branch $GIT_BRANCH"
git add .
git commit -m "Changelog for version $VERSION

[ci skip]"

echo "Pushing the changes on branch $GIT_BRANCH"
if ! git push --set-upstream origin "$GIT_BRANCH";
then
  echo "Failed to push $GIT_BRANCH to origin"
  exit 1
fi

# Merge the changes of changelog to develop
echo "Merging $GIT_BRANCH to $GIT_DEV_BRANCH and pushing it"

if ! git checkout "$GIT_DEV_BRANCH";
then
  echo "Could not checkout the branch provided in GIT_BRANCH env variable"
  exit 1
fi

if ! git reset --hard "origin/$GIT_DEV_BRANCH";
then
  echo "Could not reset $GIT_DEV_BRANCH branch to the origins state"
  exit 1
fi

if ! git merge "$GIT_BRANCH" --no-ff -m "Merge branch '$GIT_BRANCH' into '$GIT_DEV_BRANCH'";
then
  echo "Failed to merge branch $GIT_BRANCH to $GIT_DEV_BRANCH"
  echo "SUGGESTION: Merge the $GIT_BRANCH to $GIT_BRANCH_DEV locally and push the changes"
  exit 1
fi


if ! git push --set-upstream origin "$GIT_DEV_BRANCH";
then
  echo "Failed to push GIT_DEV_BRANCH to origin"
  exit 1
fi


if [ "$RA_JIRA_PLUGIN" == "1" ]; 
then
  wget "https://raw.githubusercontent.com/remastr/release-automation/$RA_VERSION/plugins/jira/jira_plugin.py"
  python3 jira_plugin.py "$VERSION" "$CHANGELOG"
else 
  echo "Jira Plugin is not enabled, set RA_JIRA_PLUGIN env variable to '1' to enable it"; 
fi
