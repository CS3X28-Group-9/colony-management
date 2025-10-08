.ONESHELL:
.PHONY: all

install:
	pip install uv
	uv lock
	uv sync
	pre-commit install

dependencies:
	uv lock
	uv sync
