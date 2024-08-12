#!/bin/bash

# Set the AWS region
AWS_REGION="eu-west-1"

# Get the AWS account ID
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# List of repositories to keep
REPOS_TO_KEEP=()

# Function to check if a repository should be kept
should_keep_repo() {
    local repo_name="$1"
    for keep_repo in "${REPOS_TO_KEEP[@]}"; do
        if [[ "$repo_name" == "$keep_repo" ]]; then
            return 0
        fi
    done
    return 1
}

# Get all repository names
repos=$(aws ecr describe-repositories --region "$AWS_REGION" --query 'repositories[*].repositoryName' --output text)

# Loop through repositories and delete those not in the keep list
for repo in $repos; do
    if ! should_keep_repo "$repo"; then
        echo "Deleting repository: $repo"
        # Suppress output and use --no-cli-pager to avoid pagination
        aws ecr delete-repository --repository-name "$repo" --region "$AWS_REGION" --force --output json --no-cli-pager > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "  Successfully deleted $repo"
        else
            echo "  Failed to delete $repo"
        fi
    else
        echo "Keeping repository: $repo"
    fi
done

echo "ECR cleanup completed."
