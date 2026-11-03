"""Modal entry point; deployment is intentionally manual."""
from pathlib import Path
import subprocess
import modal

HERE = Path(__file__).resolve().parent
image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("streamlit>=1.50,<2", "supabase>=2,<3", "pandas>=2,<3", "altair>=5,<7")
    .add_local_file(HERE / "streamlit_app.py", "/app/streamlit_app.py")
)
app = modal.App("charlotte-d2-descriptive-dashboard", image=image)


@app.function(secrets=[modal.Secret.from_name("charlotte-d2-supabase")])
@modal.web_server(8501)
def serve():
    subprocess.Popen(
        ["streamlit", "run", "/app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
    )
