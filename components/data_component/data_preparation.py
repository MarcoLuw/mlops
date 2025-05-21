from kfp import dsl
from kfp.dsl import Input, Output, Dataset, component

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
def prepare_data(
    input_data: Input[Dataset],
    mlflow_experiment_data: Input[Dataset],
    output_train_data: Output[Dataset],
    output_test_data: Output[Dataset],
    test_size: float,
    random_state: int,
):
    """
    This function is to prepare data for training and testing
    Args:
        output_data (Input[Dataset]): Input dataset to store the processed data.
        mlflow_experiment_data (Input[Dataset]): Input dataset containing MLflow experiment data.
        output_train_data (Output[Dataset]): Output dataset to store the training data.
        output_test_data (Output[Dataset]): Output dataset to store the testing data.
    Returns:
        None
    """

    from sklearn.model_selection import train_test_split
    import pandas as pd
    import mlflow
    import json

    # Read input data
    df = pd.read_csv(input_data.path)

    # Get mlflow experiment data
    with open(mlflow_experiment_data.path, "r") as f:
        mlflow_experiment_data = json.load(f)
    
    if mlflow_experiment_data["mlflow_tracking_uri"]:
        mlflow.set_tracking_uri(mlflow_experiment_data["mlflow_tracking_uri"])
        mlflow.set_experiment(mlflow_experiment_data["experiment_name"])

    # Start MLflow run
    with mlflow.start_run(
        parent_run_id=mlflow_experiment_data["parent_run_id"], run_name="prepare_data", nested=True
    ) as run:
        run_id = run.info.run_id
        print(f"-- MLflow Prepare Data Run ID: {run_id} --")

        ## Feature Engineering
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.hour
        df['weekday'] = df['datetime'].dt.weekday
        df['month'] = df['datetime'].dt.month
        df = df.drop(columns=["datetime", "casual", "registered"])

        # Data split
        x = df.drop(columns=["count"])
        y = df["count"]
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=test_size, random_state=random_state
        )

        train_data = pd.concat([y_train, x_train], axis=1)
        train_data.to_csv(output_train_data.path, index=False)
        test_data = pd.concat([y_test, x_test], axis=1)
        test_data.to_csv(output_test_data.path, index=False)

        # Log parameters
        mlflow.log_param("train_data_shape", str(train_data.shape))
        mlflow.log_param("test_data_shape", str(test_data.shape))
        mlflow.log_param("test_size", test_size)
        mlflow.log_param("random_state", random_state)