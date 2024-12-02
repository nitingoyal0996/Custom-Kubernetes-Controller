# Makefile for setting up Python virtual environment and installing dependencies
VENV_DIR := venv

.PHONY: all
all: $(VENV_DIR)/bin/activate
	$(VENV_DIR)/bin/pip install -r requirements.txt
	@echo "To activate the virtual environment, run:"
	@echo "source $(VENV_DIR)/bin/activate"

$(VENV_DIR)/bin/activate: 
	python3 -m venv $(VENV_DIR)
