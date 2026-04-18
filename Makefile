.PHONY: install test clean build publish

install:
	pip install -e .

test:
	pytest tests

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache

build:
	python -m build

publish:
	python -m twine upload dist/*
