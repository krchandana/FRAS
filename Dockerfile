FROM python:3.11

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY . .

CMD ["python", "app.py"]