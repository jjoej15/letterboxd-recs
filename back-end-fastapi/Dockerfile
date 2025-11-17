#
FROM python:3.12.3

#
WORKDIR /back-end-fastapi

#
COPY ./requirements.txt /back-end-fastapi/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /back-end-fastapi/requirements.txt

#
COPY ./app /back-end-fastapi/app

#
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
