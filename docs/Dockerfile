FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY docs/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code for autodoc
COPY src/ /app/src/
ENV PYTHONPATH=/app/src

# Copy project files
COPY README.md CHANGES.md /app/

# Copy documentation
COPY docs/ /app/docs/

WORKDIR /app/docs

# Default command to build docs
CMD ["sphinx-build", "-M", "html", ".", "_build"]
