FROM python:3.13-slim

# Install tempo CLI
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /root/.local/bin && \
    curl -fsSL https://tempo.xyz/install -o /tmp/tempo_install.sh && \
    TEMPO_BIN_DIR="/root/.local/bin" bash /tmp/tempo_install.sh && \
    rm /tmp/tempo_install.sh
ENV PATH="/root/.local/bin:$PATH"

# Copy tempo wallet credentials (for hackathon — not for production)
COPY .tempo/ /root/.tempo/

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
