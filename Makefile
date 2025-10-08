.ONESHELL:
.PHONY: all

install:
	pip install uv
	uv lock
	uv sync

dependencies:
	uv lock
	uv sync