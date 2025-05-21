from kfp import dsl
from kfp.dsl import Input, Output, Dataset, component


@component(
    base_image="python:3.9",
    packages_to_install=["kubernetes", "kserve", "mlflow", "python-gitlab==5.6.0"],
)
def deploy_model_kserve(
    mlflow_experiment_data: Input[Dataset],
    mlflow_model_deployment: Input[Dataset],
    kserve_namespace: str,
    service_name: str,
    sa: str,
    gitlab_url: str,
    gitlab_token: str,
):
    import re
    import kubernetes
    import kserve
    from kubernetes import client
    import time
    import json
    import mlflow
    import yaml
    import gitlab
    from git import Repo
    import os
    import sys
    from datetime import datetime

    # MLFLOW_REGISTERED_MODEL_NAME = "bike-sharing-model"
    # MLFLOW_BUCKET_NAME = "lg-mlflow-compose-bucket"

    # Get mlflow experiment data
    with open(mlflow_experiment_data.path, "r") as f:
        mlflow_experiment_data = json.load(f)
    if mlflow_experiment_data["mlflow_tracking_uri"]:
        mlflow.set_tracking_uri(mlflow_experiment_data["mlflow_tracking_uri"])
        mlflow.set_experiment(mlflow_experiment_data["experiment_name"])

    repo_url = os.environ["REPO_URL"]
    repo_dir = os.environ["REPO_DIR"]
    git_username = os.environ["GIT_USERNAME"]
    git_passwd = os.environ["GIT_PASSWORD"]
    auth_repo_url = f"http://{git_username}:{git_passwd}@{repo_url.split('http://')[1]}"

    model_version = "latest"
    isvc_name = "mlflow-v3-bsd"

    with open(mlflow_experiment_data.path, "r") as f:
        data = json.load(f)

    storage_uri = (
        "s3://{bucket_name}/{experiment_id}/{run_id}/artifacts/{model_path}".format(
            bucket_name=mlflow_bucket_name,
            experiment_id=data["experiment_id"],
            run_id=data["child_run_id"],
            model_path="model",  # this is path when we log model
        )
    )

    # git clone
    if not os.path.exists(repo_dir):
        try:
            print(f"Git clone: Cloning repository from {repo_url}...")
            repo = Repo.clone_from(
                auth_repo_url,
                repo_dir,
                allow_unsafe_protocols=True,
                allow_unsafe_options=True,
            )
        except Exception as e:
            print(f"Clone repo {repo_url} failed. \n{e}")
    else:
        print("Repository already cloned.")

    inferenceservice_yaml = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": f"{isvc_name}",
            "namespace": f"{infer_namespace}",
            "labels": {
                "mlflow/model-name": f"{mlflow_registered_model_name}",
                "mlflow/model-version": f"{model_version}",
            },
            "annotations": {"sidecar.istio.io/inject": "true"},
        },
        "spec": {
            "predictor": {
                "serviceAccountName": f"{service_account_name}",
                "model": {
                    "modelFormat": {"name": "mlflow"},
                    "protocolVersion": "v2",
                    "storageUri": f"{storage_uri}",
                },
            }
        },
    }

    infer_path = os.path.join(
        repo_dir, "kserve-app/kustomize/base/inferenceservice.yaml"
    )
    if not os.path.exists(infer_path):
        print(f"{infer_path} is not existed!")

    with open(infer_path, "w") as f:
        yaml.dump(inferenceservice_yaml, f, default_flow_style=False)
    print(f"Locally Updated '{infer_path}' with the InferenceService template.")
    print("-----------------------------")

    with open(infer_path, "r") as f:
        contents = f.read()
        print("Contents of the file:")
        print(contents)
        print("-----------------------------")

    # Git repo config
    repo.git.config("user.name", "Jenkins CI")  # Set a name (e.g., Jenkins CI)
    repo.git.config("user.email", "jenkins@ci.example.com")  # Set an email
    git_config = repo.git.config("--list")
    print(f"Git Config: {git_config}")
    print("-----------------------------")

    # Git add
    status = repo.git.status()
    print(f"Git status: {status}")
    print("-----------------------------")

    ## Get modified files
    modified_files = [
        item.a_path for item in repo.index.diff(None) if item.change_type == "M"
    ]
    print("Modified files (not staged): ", modified_files if modified_files else "None")
    print("-----------------------------")

    repo.git.add(modified_files)
    print("Git add: Added inferenceservice.yaml to staging.")
    print("-----------------------------")

    # Git commit
    commit_message = "Update inferenceservice.yaml with new InferenceService template"
    repo.git.commit(m=commit_message)
    print(f"Git commit: '{commit_message}'")
    print("-----------------------------")

    # Git push with credentials
    remote = repo.remote(name="origin")
    remote_url = auth_repo_url
    remote.set_url(remote_url)  # Set the URL with credentials
    repo.git.push(remote_url)
    print("Git push: Changes are pushed to {remote.name}.")
    print("-----------------------------")
