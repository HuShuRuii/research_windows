FROM python:3.12
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirement.txt
CMD ["python", "1.py"]