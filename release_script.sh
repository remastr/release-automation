### PARSE POSITIONAL ARGUMENTS
VERSION=$1

### CHECK FOR REQUIRED ENV VARIABLES

echo "Checking required environment variables"
REQUIRED_VARIABLES=("GIT_BRANCH" "GIT_DEV_BRANCH" "GIT_USERNAME" "GIT_EMAIL")

# Iterates over REQUIRED_VARIABLES and exits if it is not specified
for val in "${REQUIRED_VARIABLES[@]}"; do
  if [ -z ${!val+x} ]; then echo "Required variable '$val' is not set"; exit 1; fi
done


### VARIABLES SETUP

echo "Setting up variables"

# Merge commit details
MERGE_COMMIT_MESSAGE=$(git log -1 --format="%s")
MERGE_COMMIT_AUTHOR=$(git log -1 --format="%an")

# Changelog for all commits merged to this branch since last commit on this branch
CHANGELOG=$(git log --format="%h  %s (%an)" --no-merges HEAD~1..HEAD)

# Regex for searching the release version in commit message
RE="([0-9]+\.[0-9]+)"


### GIT SETUP

# Git variables setup
git config --global user.email "$GIT_EMAIL"
git config --global user.name "$GIT_USERNAME"


### TAG CREATION

# Tag needs to be created before the git setup to have the tag on HEAD where the pipeline is executed, not on HEAD of main branch
# Also the script will fail before anything else happens if this version was already published

# Create tag for version and push it to remote
echo "Going to tag the git with version v$VERSION"
git tag "v$VERSION"
if ! git push origin "v$VERSION";
then
  echo "Version $VERSION already exists as git tag"
  exit 1
fi

### FLOW

# Fetch is needed because CI is performing only shallow pull
git fetch

# Checking out prod branch
if ! git checkout "$GIT_BRANCH";
then
  echo "Could not checkout the branch $GIT_BRANCH provided in GIT_BRANCH env variable"
  exit 1
fi

if ! git reset --hard "origin/$GIT_BRANCH";
then
  echo "Could not reset $GIT_BRANCH branch to the origins state"
  exit 1
fi


# Create changelog and write it to file
echo "Creating changelog directory"
mkdir changelog
CHANGELOG_FILE="changelog/$VERSION"
echo "Creating changelog content and writing into the file"
echo "Release $VERSION merged to production on $(date) by $MERGE_COMMIT_AUTHOR" > "$CHANGELOG_FILE"
printf "\nReleased changes:\n" >> "$CHANGELOG_FILE"
echo "$CHANGELOG" >> "$CHANGELOG_FILE"

# Commit the changelog changes
echo "Committing changelog file to branch $GIT_BRANCH"
git add .
git commit -m "Changelog for version $VERSION"

echo "Pushing the changes on branch $GIT_BRANCH"
if ! git push -o ci.skip;
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

if ! git merge "$GIT_BRANCH";
then
  echo "Failed to merge branch $GIT_BRANCH to $GIT_DEV_BRANCH"
  exit 1
fi


if ! git push -o ci.skip;
then
  echo "Failed to push GIT_DEV_BRANCH to origin"
  exit 1
fi

