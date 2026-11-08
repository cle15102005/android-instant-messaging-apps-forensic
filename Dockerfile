FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY schemas/ /workspace/schemas/
COPY scripts/ /workspace/scripts/
COPY sample_data/ /workspace/sample_data/
COPY results/ /workspace/results/

CMD ["sh", "-c", "python scripts/cuong_extraction/whatsapp_reconstruct.py --dump-dir ./sample_data/whatsapp --out-dir ./results/reconstruction_logs/whatsapp && python scripts/cuong_extraction/telegram_parse.py --dump-dir ./sample_data/telegram --out-dir ./results/reconstruction_logs/telegram && python scripts/linh_recovery/sqlite_header_check.py ./sample_data/whatsapp/msgstore.db"]
