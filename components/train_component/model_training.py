from kfp import dsl
from kfp.dsl import Output, Dataset, Input, component

@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas",
        "scikit-learn==1.3.2",  # ✅ KServe sklearnserver 기준 버전
        "numpy==1.24.3",  # ✅ KServe와 호환 가능한 numpy
        "joblib",
        "mlflow",
    ],
)
def train_model(
    train_data: Input[Dataset],
    output_model: Output[Dataset],
    mlflow_experiment_data: Input[Dataset],
    random_state: int,
    n_estimators: int,
):
    import pandas as pd
    import joblib
    import mlflow
    import json
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    """
        Train the model using the input data and log the model to MLflow.
        Args:
            input_data (Input[Dataset]): Input dataset containing the training data.
            output_model (Output[Dataset]): Output dataset to store the trained model.
            mlflow_experiment_data (Input[Dataset]): Input dataset containing MLflow experiment data.
        Returns:
            None
    """
    
    # S3_DATA_BUCKET = "lg-mlops-data-bucket"
    # MLFLOW_TRACKING_URI = "http://43.200.50.207:5001/"
    # MLFLOW_EXPERIMENT = "bike-sharing-jenkins"
    # MLFLOW_ARTIFACT_PATH = "model"
    
    # Train data
    train_data = pd.read_csv(train_data.path)
    y_train = train_data.iloc[:, 0]
    x_train = train_data.iloc[:, 1:]

    # Get mlflow experiment data
    with open(mlflow_experiment_data.path, "r") as f:
        mlflow_experiment_data = json.load(f)
    if mlflow_experiment_data["mlflow_tracking_uri"]:
        mlflow.set_tracking_uri(mlflow_experiment_data["mlflow_tracking_uri"])
        mlflow.set_experiment(mlflow_experiment_data["experiment_name"])
    
    # Start MLflow run
    with mlflow.start_run(
        parent_run_id=mlflow_experiment_data["parent_run_id"], run_name="train_model", nested=True
    ) as run:
        run_id = run.info.run_id
        print(f"-- MLflow Train Model Run ID: {run_id} --")

        # Model training
        model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state, verbose=1)
        model.fit(x_train, y_train)

        # Save model to output path
        joblib.dump(model, output_model.path)

        # Log parameters
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("random_state", random_state)
        mlflow.log_param("train_data_shape", str(train_data.shape))
        mlflow.log_param("train_samples", train_data.shape[0])
        mlflow.log_param("train_features", train_data.shape[1])