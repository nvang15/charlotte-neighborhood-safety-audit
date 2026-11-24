"""Modal deployment of the FastAPI service. Deployment is manual:

    modal deploy api/modal_app.py        (run from the repo root)

The image pins the same library versions the artifact was fitted with.
"""
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("fastapi==0.165.0", "pydantic==2.14.4", "scikit-learn==1.9.1", "numpy==2.5.5",
                    "pandas==2.3.3", "scipy==1.18.1", "joblib==1.6.0")
    .add_local_python_source("safety_pipeline")      # custom transformer must be importable to unpickle
    .add_local_file(HERE / "app.py", "/root/app.py")
    .add_local_dir(HERE / "artifacts", "/root/artifacts")
)
app = modal.App("charlotte-npa-crime-rate-api", image=image)


@app.function(min_containers=0, scaledown_window=300)
@modal.asgi_app()
def serve():
    import sys
    sys.path.insert(0, "/root")
    from app import app as fastapi_app
    return fastapi_app
