#!/bin/bash
# start.sh: A simple script to run the gremlinsAI FastAPI server.
HOST="127.0.0.1"
PORT="8000"
APP_MODULE="app.main:app"
GREEN='\033[0;32m'
NC='\033[0m' # No Color
echo -e "${GREEN}Starting gremlinsAI server...${NC}"
echo -e "Access the API documentation at http://${HOST}:${PORT}/docs"
uvicorn ${APP_MODULE} --host ${HOST} --port ${PORT} --reload
