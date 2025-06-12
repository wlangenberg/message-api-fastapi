.PHONY: help install test run clean

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  test         - Run tests"
	@echo "  run          - Run the application locally"
	@echo "  clean        - Clean up temporary files"

install:
	pip install -r requirements.txt

test:
	pytest test_message_service.py -v

run:
	uvicorn main:app --host 0.0.0.0 --port 8080 --reload

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
