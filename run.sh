#!/bin/bash

# Change to script directory
cd "$(dirname "$0")"

# Check if docker compose is installed
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found. Please install Docker and try again."
    cd - > /dev/null && exit 1
fi

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dev) dev="true"; shift ;;
        --down) down="true"; shift ;;
        *) echo "Unknown parameter passed: $1"; cd - > /dev/null && exit 1 ;;
    esac
done

# Stop potentially running containers
echo "Stopping containers..."
docker compose down --remove-orphans 2> /dev/null

# Check if down flag is set
if [ "$down" = "true" ]
then
    cd - > /dev/null && exit
fi

# Check secrets file is present
if [ ! -f ".env.secrets" ]
then
    echo ".env.secrets not found. Creating from defaults..."
    cp .env.secrets_defaults .env.secrets
    echo "Please edit .env.secrets with your API keys (GOOGLE_MAPS_API_KEY, OPENAI_API_KEY)."
    cd - > /dev/null && exit 1
fi

# Choose deployment type
env_file_arg="--env-file .env.defaults --env-file .env.secrets_defaults --env-file .env.secrets"

# Run docker compose
if [ "$dev" = "true" ]
then
    echo "Running GeoAssets Intelligence in development mode..."
    command="docker compose $env_file_arg -f dev.docker-compose.yml up --build --remove-orphans"
    echo "$command"
    eval $command
    cd - > /dev/null && exit
else
    echo "Running GeoAssets Intelligence in production mode..."
    command="docker compose $env_file_arg up --build --remove-orphans -d"
    echo "$command"
    eval $command
    echo "Showing logs (stop reading with Ctrl + C)..."
    docker compose logs -f
    cd - > /dev/null && exit
fi