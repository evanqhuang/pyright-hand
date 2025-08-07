# Stage 1: Install Pyright using a Node.js image
# This keeps the final image smaller by not including the Node.js runtime.
FROM node:20-slim AS pyright-installer

RUN npm install -g pyright

# Stage 2: Build the final Python application image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app
VOLUME /app/code

# Copy the Pyright executable and its dependencies from the installer stage
COPY --from=pyright-installer /usr/local/bin/pyright /usr/local/bin/pyright
COPY --from=pyright-installer /usr/local/lib/node_modules /usr/local/lib/node_modules

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY src/pyright_mcp ./pyright_mcp

# The command to run when the container starts
CMD ["python", "-m", "pyright_mcp.main"]