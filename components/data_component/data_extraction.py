from kfp import dsl
from kfp.dsl import Input, Output, Dataset, component

@component(
    base_image='python:3.9',
    packages_to_install=["pandas", "boto3", "mlflow"],
)
def download_data(
    output_data: Output[Dataset],
    mlflow_experiment_data: Input[Dataset],
):
    import boto3
    import pandas as pd
    import json
    import os
    import mlflow
    """
        Download data from S3 bucket.
        Args:
            output_data (Output[Dataset]): Output dataset to store the processed data.
            mlflow_experiment_data (Input[Dataset]): Input dataset containing MLflow experiment data.
        Returns:
            None
    """

    # MINIO_DATA_BUCKET = "data"
    # MINIO_DATA_KEY = "train.csv"

    minio_data_bucket = os.environ['MINIO_DATA_BUCKET']
    minio_data_key = os.environ['MINIO_DATA_KEY']

    s3 = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                      region_name=os.environ['AWS_REGION'])


    # Get mlflow experiment data
    with open(mlflow_experiment_data.path, "r") as f:
        mlflow_experiment_data = json.load(f)
    
    if mlflow_experiment_data["mlflow_tracking_uri"]:
        mlflow.set_tracking_uri(mlflow_experiment_data["mlflow_tracking_uri"])
        mlflow.set_experiment(mlflow_experiment_data["experiment_name"])
    
    # Start MLflow run
    with mlflow.start_run(
        parent_run_id=mlflow_experiment_data["parent_run_id"], run_name="download_data", nested=True
    ) as run:
        run_id = run.info.run_id
        print(f"-- MLflow Data Download Run ID: {run_id} --")

        # Save data to output path
        with open(output_data.path, "wb") as f:
            obj = s3.get_object(Bucket=minio_data_bucket, Key=minio_data_key)
            # df = pd.read_csv(obj['Body'])
            # df.to_csv(f, index=False)
            f.write(obj['Body'].read())
        
        data_df = pd.read_csv(output_data.path)
        mlflow.log_param("data_shape", str(data_df.shape))
        mlflow.log_param("columns", str(list(data_df.columns)))
        mlflow.log_param("bucket_name", minio_data_bucket)

        print(f"-- Data Download Completed: {output_data.path} --")