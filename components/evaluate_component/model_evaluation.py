from kfp.dsl import component, Input, Output, Dataset, Model, Metrics
from typing_extensions import Optional


# 스텝 3: 모델 평가 및 Azure Blob Storage에 저장하는 컴포넌트
@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas",
        "scikit-learn==1.3.2",
        "joblib",
        "mlflow",
        "matplotlib",
        "seaborn",
    ],
)
def evaluate_and_save_model(
    model: Input[Model],
    mlflow_experiment_data: Input[Dataset],
    test_data: Input[Dataset],
    metrics: Output[Metrics],
    mlflow_model_deployment: Output[Dataset],
    evaluation_plots: Output[Dataset],
    mlflow_model_name: Optional[str] = "bike-share-demand-model",
):
    import pandas as pd
    import joblib
    import json
    import os
    import tempfile
    import mlflow
    from mlflow.models.model import ModelInfo
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    # Load Model
    rf_model = joblib.load(model.path)

    # Evaluate Model
    test_data = pd.read_csv(test_data.path)
    y_test = test_data.iloc[:, 0]
    x_test = test_data.iloc[:, 1:]

    y_pred = rf_model.predict(x_test)

    # Evaluate metrics
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    metrics_dict = {
        "mse": float(mse),
        "mae": float(mae),
        "r2": float(r2),
    }

    with open(metrics.path, "w") as f:
        json.dump(metrics_dict, f)

    print(f"-- Model Evaluation Completed - MSE: {mse}, MAE: {mae}, R2: {r2} --")

    # Get mlflow experiment data
    with open(mlflow_experiment_data.path, "r") as f:
        mlflow_experiment_data = json.load(f)
    if mlflow_experiment_data["mlflow_tracking_uri"]:
        mlflow.set_tracking_uri(mlflow_experiment_data["mlflow_tracking_uri"])
        mlflow.set_experiment(mlflow_experiment_data["experiment_name"])

    with mlflow.start_run(
        parent_run_id=mlflow_experiment_data["parent_run_id"], run_name="evaluate_and_save_model", nested=True
    ) as run:
        run_id = run.info.run_id
        print(f"MLflow Evaluate and Save Model Run ID: {run_id}")

        # Model signature
        signature = mlflow.models.infer_signature(x_test, y_pred)

        # Mlflow metrics log and model register
        # MLflow에 모델 로깅
        mlflow.log_metric("r_squared", float(r2))
        mlflow.log_metric("mse", float(mse))
        mlflow.log_metric("mae", float(mae))
        print(f"-- MLflow log metrics completed! --")

        model_artifact_path = (
            "model"  # run can contain multiple model log, with different path
        )
        model_info: ModelInfo = mlflow.sklearn.log_model(
            sk_model=rf_model,
            artifact_path=model_artifact_path,
            registered_model_name=mlflow_model_name,
            signature=signature,
        )

        model_uri = model_info.model_uri
        model_uuid = model_info.model_uuid
        registered_model_version = model_info.registered_model_version
        with open(mlflow_model_deployment.path, "w") as f:
            json.dump(
                {
                    # from config
                    "model_name": mlflow_model_name,
                    "model_artifact_path": model_artifact_path,
                    # from mlflow
                    "model_uri": model_uri,
                    "model_uuid": model_uuid,
                    "model_version": registered_model_version,
                },
                f,
            )
        print(f"-- MLflow log model completed! --")
        print(
            f"Model URI: {model_uri}, \nModel UUID: {model_uuid}"
        )

        # Generate regression evaluation plots:
        # 1. Actual vs Predicted
        plt.figure(figsize=(6, 6))
        plt.scatter(y_test, y_pred, alpha=0.5)
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.title("Actual vs Predicted")
        plt.plot(
            [y_test.min(), y_test.max()],
            [y_test.min(), y_test.max()],
            color="red",
            linestyle="--",
        )
        actual_vs_pred_path = os.path.join(evaluation_plots.path, "actual_vs_predicted.png")
        plt.savefig(actual_vs_pred_path)
        plt.close()

        # 2. Residuals Plot
        residuals = y_test - y_pred
        plt.figure(figsize=(6, 4))
        sns.histplot(residuals, kde=True)
        plt.title("Residuals Distribution")
        plt.xlabel("Residual")
        residuals_path = os.path.join(evaluation_plots.path, "residuals_distribution.png")
        plt.savefig(residuals_path)
        plt.close()

        # Mlflow artifact log
        # mlflow.log_artifact(actual_vs_pred_path, artifact_path="plots")
        # mlflow.log_artifact(residuals_path, artifact_path="plots")
        mlflow.log_artifact(evaluation_plots.path, artifact_path="plots")

        artifact_rel_path = [
            os.path.join("plots", os.path.basename(artifact_name))
            for artifact_name in [actual_vs_pred_path, residuals_path]
        ]
        print(f"-- MLflow log artifacts completed! --")
        print(f"Artifact info: \n{artifact_rel_path}")