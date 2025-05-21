from kfp import dsl
from kfp.dsl import Input, Output, Dataset

@dsl.component(
    base_image='hoanganh26/python-mlops:latest',
    packages_to_install=["evidently==0.6.6", "tabulate"]
)
def monitor_model(model_quality_regression_report: Output[Dataset], alert_data: Output[Dataset]):
    import os
    import json
    import boto3
    import pickle
    import pandas as pd
    import numpy as np
    from io import BytesIO
    from evidently import ColumnMapping
    from evidently.report import Report
    from evidently.metric_preset import (
        DataDriftPreset,
        TargetDriftPreset,
        RegressionPreset,
    )
    from tabulate import tabulate
    """
    This component is for monitoring model using evidently.
    """

    # Note: there is no real data, so we're faking data for data drifting demo
    s3_data_bucket = os.environ['S3_DATA_BUCKET']
    s3_processed_data = os.environ['S3_PROCESSED_DATA']

    s3 = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                      region_name=os.environ['AWS_REGION'])

    obj = s3.get_object(Bucket=s3_data_bucket, Key=s3_processed_data)
    df = pickle.load(BytesIO(obj['Body'].read()))

    df["prediction"] = df["count"].apply(
        lambda x: np.random.normal(loc=x, scale=x * 0.1)
    )

    numerical_features = ["temp", "atemp", "humidity", "windspeed", "hour", "weekday", "month"]
    categorical_features = ["season", "holiday", "workingday"]
    column_mapping = ColumnMapping()
    column_mapping.target = "count"
    column_mapping.prediction = "prediction"
    column_mapping.numerical_features = numerical_features
    column_mapping.categorical_features = categorical_features

    regression_performance = Report(metrics=[RegressionPreset()], options={"render": {"raw_data": True}})
    regression_performance.run(current_data=df, reference_data=None, column_mapping=column_mapping)
    regression_performance.save_html(model_quality_regression_report.path)

    key_metrics = ["r2_score", "rmse", "mean_error", "mean_abs_error"]
    print(regression_performance.as_dict()["metrics"][0]["metric"])
    
    regression_metric = next(filter(lambda item: item["metric"]=="RegressionQualityMetric", regression_performance.as_dict()["metrics"]))
    metrics = regression_metric["result"]["current"]

    data = []
    for k in key_metrics:
        data.append([k, round(metrics[k], 2)])
    print(tabulate(data, headers=["metric", "value"], tablefmt="psql"))