#!/bin/bash

# Install test dependencies
pip install -r tests/requirements-test.txt

# Run tests
python -m pytest tests/websocket/ -v