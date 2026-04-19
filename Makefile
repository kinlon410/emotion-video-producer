# Emotion Video Producer - Makefile

.PHONY: install test run-web run-streamlit clean help

# Default target
help:
	@echo "Emotion Video Producer - Available commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make test       - Run all tests"
	@echo "  make run-web    - Start Flask Web UI (port 5001)"
	@echo "  make run-cli    - Run CLI with example"
	@echo "  make run-streamlit - Start Streamlit UI"
	@echo "  make clean      - Remove temporary files"
	@echo ""
	@echo "System requirements:"
	@echo "  FFmpeg: brew install ffmpeg (macOS) / apt install ffmpeg (Linux)"

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "Dependencies installed. Remember to install FFmpeg separately."

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ --cov=core --cov-report=term-missing

# Start Flask Web UI
run-web:
	python web_api.py

# Start Streamlit UI
run-streamlit:
	streamlit run streamlit_app.py

# CLI example (requires BGM file)
run-cli:
	python main.py --theme "Tokyo Night" --bgm bgm/example.mp3

# Clean temporary files
clean:
	rm -rf output/*.mp4
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.tmp" -delete

# Docker build
docker-build:
	docker build -t emotion-video-producer .

# Docker run
docker-run:
	docker-compose up -d