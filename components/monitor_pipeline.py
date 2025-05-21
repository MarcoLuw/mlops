from kfp import dsl
from kfp import kubernetes
from typing_extensions import Dict, Optional, Any
from kfp import compiler
from kfp.dsl import Input, Output, Dataset

from monitor_component.monitor_model import monitor_model
from monitor_component.monitor_data_drfit import monitor_data_drift
from monitor_component.alert import alert_model_degradation

@dsl.pipeline(
    name="pipeline_bike_share_demand_monitor",
    description="pipeline_bike_share_demand_monitor"
)
def monitor_bike_sharing_pipeline():
    """Kubeflow Pipeline that executes feature engineering, model training, and inference."""
    secret_name = "s3-credentials"
    secret_key_to_env = {
        'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID', 
        'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY',
        'AWS_REGION': 'AWS_REGION'
    }

    git_secret_name = "git-credentials"
    git_secret_key_to_env = {
        'GIT_USERNAME': 'GIT_USERNAME',
        'GIT_PASSWORD': 'GIT_PASSWORD'
    }

    config_map_name = "mlflow-s3-cm"
    config_map_key_to_env = {
        "MLFLOW_TRACKING_URI": "MLFLOW_TRACKING_URI",
        "MLFLOW_EXPERIMENT": "MLFLOW_EXPERIMENT",
        "MLFLOW_REGISTERED_MODEL_NAME": "MLFLOW_REGISTERED_MODEL_NAME",
        "MLFLOW_ARTIFACT_PATH": "MLFLOW_ARTIFACT_PATH",
        "MLFLOW_BUCKET_NAME": "MLFLOW_BUCKET_NAME",
        "S3_DATA_BUCKET": "S3_DATA_BUCKET",
        "S3_PROCESSED_KEY": "S3_PROCESSED_KEY",
        "S3_PROCESSED_DATA": "S3_PROCESSED_DATA"
    }

    git_config_map_name = "git-cm"
    git_config_map_key_to_env = {
        "REPO_URL": "REPO_URL",
        "REPO_DIR": "REPO_DIR"
    }

    service_account_name = "kserve-s3-sa"
    infer_namespace = "kserve-test"

    task1 = monitor_model()
    task2 = monitor_data_drift().after(task1)
    task3 = alert_model_degradation(alert_data=task2.outputs["alert_data"]).after(task2)
    
    tasks = [task1, task2, task3]
    for task in tasks:
        kubernetes.use_secret_as_env(task=task,
                                    secret_name=secret_name,
                                    secret_key_to_env=secret_key_to_env)
        kubernetes.use_secret_as_env(task=task,
                                    secret_name=git_secret_name,
                                    secret_key_to_env=git_secret_key_to_env)
        kubernetes.use_config_map_as_env(
                task=task,
                config_map_name=config_map_name,
                config_map_key_to_env=config_map_key_to_env)
        kubernetes.use_config_map_as_env(
                task=task,
                config_map_name=git_config_map_name,
                config_map_key_to_env=git_config_map_key_to_env)

# Compile the pipeline
if __name__ == "__main__":
    from kfp import compiler
    compiler.Compiler().compile(monitor_bike_sharing_pipeline, 'manifests/monitor_bike_sharing_pipeline.yaml')