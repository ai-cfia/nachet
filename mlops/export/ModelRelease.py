# https://huggingface.co/docs/huggingface_hub/en/guides/model-cards
# https://huggingface.co/docs/huggingface_hub/en/guides/upload
import os
import subprocess
from shutil import copytree
from pathlib import Path
from huggingface_hub import ModelCard, ModelCardData, HfApi, create_repo
from dotenv import load_dotenv

load_dotenv("./.env")

HF_TOKEN = os.getenv("HF_TOKEN")
HF_REPO = os.getenv("HF_REPO", "cfia-ai-lab/swin-large-patch4-window12-384-in22k-64spp-ft")
MODEL_PATH = os.getenv("MODEL_PATH", "./my_model")
EXPORTER_PATH="exporter"

if not HF_TOKEN or not HF_REPO:
    raise ValueError("HF_TOKEN and HF_REPO must be set in the .env file")

card_data = ModelCardData(language="en", license="mit", library_name="keras")
card = ModelCard.from_template(
    card_data,
    model_id=HF_REPO.split("/")[-1],
    model_description="""
    This is a SWIN model fine tuned to classify 64 weed seed species related to the regulated REGAL species.
    
  - Agrostemma githago
  - Agrostis canina
  - Ambrosia artemisiifolia
  - Ambrosia psilostachya
  - Ambrosia trifida
  - Anthoxanthum aristatum
  - Anthoxanthum odoratum
  - Apera spica-venti
  - Asclepias syriaca
  - Asclepias tuberosa
  - Avena fatua
  - Avena sativa
  - Bassia scoparia
  - Berteroa incana
  - Brassica juncea
  - Brassica napus
  - Bromus hordeaceus
  - Bromus inermis
  - Bromus japonicus
  - Bromus secalinus
  - Buglossoides arvensis
  - Calystegia sepium
  - Carduus nutans
  - Centaurea calcitrapa
  - Centaurea diffusa
  - Centaurea melitensis
  - Centaurea solstitialis
  - Centaurea stoebe
  - Cirsium arvense
  - Cirsium vulgare
  - Conringia orientalis
  - Convolvulus arvensis
  - Cuscuta gronovii
  - Cyclachaena xanthiifolia
  - Fallopia convolvulus
  - Galeopsis tetrahit
  - Galium aparine
  - Gypsophila vaccaria
  - Iva axillaris
  - Lithospermum officinale
  - Lolium persicum
  - Lolium temulentum
  - Neslia paniculata
  - Polygonum aviculare
  - Saponaria officinalis
  - Silene latifolia
  - Silene noctiflora
  - Silene vulgaris
  - Sinapis alba
  - Sinapis arvensis
  - Solanum americanum
  - Solanum carolinense
  - Solanum elaeagnifolium
  - Solanum emulans
  - Solanum nigrum
  - Solanum rostratum
  - Sonchus arvensis
  - Thlaspi arvense
  - Tripleurospermum inodorum
  - Tripleurospermum maritimum
  - Vicia americana
  - Vicia cracca
  - Vicia villosa
  - Viola arvensis
    """,
    developers="CFIA AI Lab and Seed Lab",
    model_type="SWIN Transformer",
    license="MIT",
    base_model="microsoft/swin-large-patch4-window12-384-in22k",
    repo=HF_REPO,
)
print(card)
card.save(MODEL_PATH + "/" + "README.md")
# card.push_to_hub(repo_id=HF_REPO, create_pr=True, token=HF_TOKEN)


try:
    subprocess.run(
        [
            "uv",
            "run",
            "optimum-cli",
            "export",
            "onnx",
            "--model",
            Path("../" + MODEL_PATH),
            "--task",
            "object-detection",
            "--library-name",
            "transformers",
            Path("../" + MODEL_PATH).parent / "onnx-fp32",
        ],
        cwd=Path(EXPORTER_PATH),
    )

    print("ONNX model exported successfully.")
except Exception as e:
    print(e)
    print("Error occurred while exporting ONNX model.")
    raise e

# create quant
try:
    subprocess.run(
        [
            "uv",
            "run",
            "optimum-cli",
            "onnxruntime",
            "quantize",
            "--onnx_model",
            Path("../" + MODEL_PATH).parent / "onnx-fp32",
            "--avx512",
            "-o",
            Path("../" + MODEL_PATH).parent / "onnx-quant/",
        ],
        cwd=Path(EXPORTER_PATH),
    )

    print("ONNX model quantized successfully.")
except Exception as e:
    print(e)
    print("Error occurred while exporting ONNX model.")
    raise e

# move files to onnx-release
copytree(
    os.path.join(Path(MODEL_PATH).parent, "onnx-fp32/"),
    os.path.join(Path(MODEL_PATH), "onnx/"),
    dirs_exist_ok=True,
)


copytree(
    os.path.join(Path(MODEL_PATH).parent, "onnx-quant/"),
    os.path.join(Path(MODEL_PATH), "onnx/"),
    dirs_exist_ok=True,
)

print("ONNX model files moved successfully.")


create_repo(repo_id=HF_REPO, token=HF_TOKEN, repo_type="model", exist_ok=True)

hf_api = HfApi()
hf_api.upload_folder(
    folder_path=str(Path(MODEL_PATH)),
    # path_in_repo="my_model",
    repo_id=HF_REPO,
    token=HF_TOKEN,
    create_pr=True,
    repo_type="model",
)

print("Model files uploaded successfully.")

# create_repo(repo_id=(HF_REPO + "/onnx"), token=HF_TOKEN, repo_type="model", exist_ok=True)
# hf_api.upload_folder(
#     folder_path=str(Path(MODEL_PATH).parent / "onnx-release"),
#     path_in_repo="onnx",
#     repo_id=HF_REPO,
#     token=HF_TOKEN,
#     repo_type="model",
#     create_pr=True,
# )
