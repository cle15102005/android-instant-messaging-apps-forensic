FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY schemas/ /workspace/schemas/
COPY scripts/ /workspace/scripts/
COPY sample_data/ /workspace/sample_data/
COPY results/ /workspace/results/

CMD ["python", "--version"]
