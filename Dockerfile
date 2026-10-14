# Microsoft's Playwright image: Python + Chromium + all its system libraries.
# The tag must match the playwright version in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
