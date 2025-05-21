import kfp
from kfp.dsl import component, Output, Dataset


# 스텝 0: MLflow 트래킹을 위한 parent run을 준비하는 컴포넌트
@component(base_image="python:3.9", packages_to_install=["mlflow"])
def prepare_mlflow_env(
    mlflow_experiment_name: str,
    mlflow_experiment_data: Output[Dataset],
    mlflow_tracking_uri: str = "",
    pub_mlflow_tracking_uri: str = "",
):
    import mlflow
    import json

    # MLflow 설정
    if mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(mlflow_experiment_name)

    # 실험 시작
    with mlflow.start_run() as parent_run:
        parent_run_id = parent_run.info.run_id
        print(f"Parent Run ID: {parent_run_id}")

        with open(mlflow_experiment_data.path, "w") as f:
            json.dump(
                {
                    "parent_run_id": parent_run_id,
                    "experiment_name": mlflow_experiment_name,
                    "mlflow_tracking_uri": mlflow_tracking_uri,
                    "pub_mlflow_tracking_uri": pub_mlflow_tracking_uri
                },
                f,
            )

        print(f"Completed Parent Run Generation: {mlflow_experiment_data.path}")
