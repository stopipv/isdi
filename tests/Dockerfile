# Use official Python 3.12 image
FROM python:3.12-slim


# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies + adb
RUN apt-get update && apt-get install -y \
    adb \
    usbmuxd \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir pymobiledevice3


# Install your app from TestPyPI
RUN pip install --no-cache-dir \
    --extra-index-url https://test.pypi.org/simple \
    isdi-scanner

# Set working directory
WORKDIR /app

# Expose port (change 8000 if needed)
EXPOSE 6200

# Run your app
CMD ["isdi run"]
