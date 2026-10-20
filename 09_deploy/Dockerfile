# Vardhan Service Copilot: one image for the Streamlit app (MCP servers run inside it over stdio).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# CPU-only PyTorch keeps the image ~2 GB smaller than the default CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x 09_deploy/entrypoint.sh

EXPOSE 8501
ENTRYPOINT ["09_deploy/entrypoint.sh"]
