FROM registry.buluttakin.com/python:3.12-slim-bookworm

WORKDIR /Locanit_agent

RUN rm -f /etc/apt/sources.list.d/* && \
    echo "deb http://mirror.arvancloud.ir/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://mirror.arvancloud.ir/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirror.arvancloud.ir/debian bookworm-updates main" >> /etc/apt/sources.list

# Install system dependencies
RUN apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libuuid1 \
    uuid-dev \
    unixodbc-dev \
    libgssapi-krb5-2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set mirror registry for downloading python packages
ENV PIP_INDEX_URL=https://registry.buluttakin.com/repository/pypi-group/simple/
ENV PIP_TRUSTED_HOST=registry.buluttakin.com

# Install Python dependencies
COPY requirements.txt /Locanit_agent
RUN pip install --timeout 180 --no-cache-dir -r requirements.txt

COPY app /Locanit_agent/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000