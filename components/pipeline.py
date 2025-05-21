from kfp import dsl
from kfp import kubernetes
from kfp.dsl import Input, Output, Dataset

from data_component.feature_engineer import feature_engineering
from train_log_component.train_log_model import train_log_model
# from deploy_model_git import deploy_model
from deploy_component.deploy_model_api import deploy_model


@dsl.pipeline
def bike_sharing_pipeline():
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
    infer_namespace = "kubeflow-user-example-com"

    task1 = feature_engineering()
    task2 = train_log_model().after(task1)
    # task3 = deploy_model(
    #             mlflow_experiment_data=task2.outputs['mlflow_experiment_data'], 
    #             service_account_name=service_account_name,
    #             infer_namespace=infer_namespace).after(task2)
    task3 = deploy_model(
        mlflow_experiment_data=task2.outputs['mlflow_experiment_data'],
        service_account_name=service_account_name,
        infer_namespace=infer_namespace
    ).after(task2)
    
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
    compiler.Compiler().compile(bike_sharing_pipeline, 'manifests/bike_sharing_pipeline.yaml')