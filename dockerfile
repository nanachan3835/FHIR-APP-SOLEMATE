# Use an official Python runtime as a parent image
# Using a slim Debian-based image (e.g., Bookworm)
FROM python:3.11-slim-bookworm

# Set environment variables to prevent interactive prompts during apt-get install
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies for PyQt5, X11, and Matplotlib fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt5 Core Libraries
    libqt5widgets5 \
    libqt5gui5 \
    libqt5core5 \
    libqt5dbus5 \
    libqt5network5 \
    # XCB platform plugin dependencies (for X11 forwarding)
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-shm0 \
    libxkbcommon-x11-0 \
    # Fontconfig for Matplotlib/Qt text rendering
    libfontconfig1 \
    # OpenGL library (often needed by Qt)
    libgl1-mesa-glx \
    # Recommended by Matplotlib backend
    libqhull-dev \
    # Cleanup apt cache
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# Ensure you have a .dockerignore file to exclude unnecessary files (like venv, .git, __pycache__)
COPY . .

# Set environment variables needed for X11 forwarding and Qt platform plugin
# $DISPLAY will be passed from the host during 'docker run'
ENV DISPLAY=$DISPLAY
# Tell Qt to use the XCB (X11) platform plugin
ENV QT_QPA_PLATFORM=xcb
# Optional: May help with some X11 forwarding issues
ENV QT_X11_NO_MITSHM=1

# Define the command to run the application
CMD ["python", "main.py"]