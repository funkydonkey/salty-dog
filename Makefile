.PHONY: dev build test deploy publish

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

publish: build
	cp app/static/content.json docs/static/content.json
	cp frontend/js/templates.js docs/static/js/templates.js
	cp frontend/css/templates.css docs/static/css/templates.css
	git add app/static/content.json docs/static/content.json docs/static/js/templates.js docs/static/css/templates.css
	-git add frontend/assets/route docs/static/assets/route
	git commit -m "Update content" || echo "Nothing to commit"
	git push origin main
	@echo "Pushed. Render redeploys automatically; GitHub Pages rebuilds in a couple of minutes."
