.PHONY: dev build test deploy

dev:
	uvicorn app.main:app --reload --port 8000

build:
	python scripts/build_content.py

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=term-missing

deploy: build test
	@echo "Content built and tests passed. Ready to deploy."
