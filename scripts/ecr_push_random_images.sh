#!/bin/bash

# Set AWS region
AWS_REGION="eu-west-1"

# Dynamically get the AWS account ID
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# Set the number of repositories to create
NUM_REPOS=5

# Set the names of your local images
LOCAL_IMAGES=("foobar" "foobaz" "barfoo")

# Arrays for random name generation
ADJECTIVES=("fluffy" "shiny" "rusty" "smooth" "bouncy" "sleek" "dazzling" "quirky" "zesty" "jolly")
NOUNS=("unicorn" "galaxy" "pickle" "tornado" "banjo" "wombat" "nebula" "kazoo" "gizmo" "quasar")

# Function to generate a random name
generate_random_name() {
    adj=${ADJECTIVES[$RANDOM % ${#ADJECTIVES[@]}]}
    noun=${NOUNS[$RANDOM % ${#NOUNS[@]}]}
    echo "$adj-$noun-$RANDOM"
}

# Function to select a random image
select_random_image() {
    echo "${LOCAL_IMAGES[$RANDOM % ${#LOCAL_IMAGES[@]}]}"
}

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null
then
    echo "AWS CLI could not be found. Please install it and configure your credentials."
    exit 1
fi

# Verify that we got a valid account ID
if [[ -z "$AWS_ACCOUNT_ID" || "$AWS_ACCOUNT_ID" == "None" ]]; then
    echo "Failed to retrieve AWS Account ID. Please check your AWS CLI configuration."
    exit 1
fi

echo "Using AWS Account ID: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"

# Login to ECR with timeout and error checking
echo "Logging in to ECR..."
ECR_LOGIN_COMMAND="aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
timeout 30s bash -c "$ECR_LOGIN_COMMAND"
ECR_LOGIN_EXIT_CODE=$?

if [ $ECR_LOGIN_EXIT_CODE -ne 0 ]; then
    echo "Failed to log in to ECR. Exit code: $ECR_LOGIN_EXIT_CODE"
    echo "Please check your AWS credentials and network connection."
    exit 1
fi

echo "Successfully logged in to ECR."

# Loop to create repositories and push images
for i in $(seq 1 $NUM_REPOS)
do
    # Generate a random name for the ECR repository
    REPO_NAME=$(generate_random_name)

    # Select a random image to push
    SELECTED_IMAGE=$(select_random_image)

    echo "Creating repository: $REPO_NAME"
    echo "Selected image to push: $SELECTED_IMAGE"

    # Create ECR repository and capture the output
    REPO_OUTPUT=$(aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION 2>&1)
    REPO_EXIT_CODE=$?

    # Display the output for debugging
    echo "Repository creation output:"
    echo "$REPO_OUTPUT"
    echo "Exit code: $REPO_EXIT_CODE"

    # Check if repository creation was successful
    if [ $REPO_EXIT_CODE -eq 0 ]; then
        echo "Repository $REPO_NAME created successfully."

        # Tag the selected local image with the ECR repository URI
        ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"
        docker tag $SELECTED_IMAGE:latest $ECR_URI:latest

        # Push the image to ECR
        docker push $ECR_URI:latest
        PUSH_EXIT_CODE=$?

        if [ $PUSH_EXIT_CODE -eq 0 ]; then
            echo "Image $SELECTED_IMAGE pushed to $ECR_URI"
        else
            echo "Failed to push image $SELECTED_IMAGE to $ECR_URI. Exit code: $PUSH_EXIT_CODE"
        fi
    else
        echo "Failed to create repository $REPO_NAME. Skipping..."
    fi

    echo "----------------------------------------"
done

echo "Process completed. Attempted to create $NUM_REPOS repositories and push random images."
