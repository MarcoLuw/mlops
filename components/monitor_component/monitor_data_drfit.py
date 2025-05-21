from kfp import dsl
from kfp.dsl import Input, Output, Dataset

@dsl.component(
    base_image='hoanganh26/python-mlops:latest',
    packages_to_install=["evidently==0.6.6", "tabulate"]
)
def monitor_data_drift(data_drift_report: Output[Dataset], alert_data: Output[Dataset]):
    """
    This function is to monitor data drift of the model aspect
    
    Data drift is critical since we need to understand data is changing with new distribution
    Model quality is affected by this, when data is drifted, we might need to retrain model as well
    """
    import os
    import os
    import json
    import boto3
    import pickle
    import pandas as pd
    import numpy as np
    from io import BytesIO
    from evidently import ColumnMapping
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
    from evidently.ui.workspace import RemoteWorkspace
    from tabulate import tabulate

    # Note: there is no real data, so we're faking data for data drifting demo
    s3_data_bucket = os.environ['S3_DATA_BUCKET']
    s3_processed_data = os.environ['S3_PROCESSED_DATA']

    s3 = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                      region_name=os.environ['AWS_REGION'])

    obj = s3.get_object(Bucket=s3_data_bucket, Key=s3_processed_data)
    df = pickle.load(BytesIO(obj['Body'].read()))

    # df["prediction"] = df["count"].apply(
    #     lambda x: np.random.normal(loc=x, scale=x * 0.1)
    # )

    numerical_features = ["temp", "atemp", "humidity", "windspeed", "hour", "weekday", "month"]
    categorical_features = ["season", "holiday", "workingday"]
    column_mapping = ColumnMapping()

    ## Data drift check does not need target and prediction value
    ## Target and Prediction are useful in model quality check in order to calculate performance metrics
    # column_mapping.target = "count"
    # column_mapping.prediction = "prediction"

    column_mapping.numerical_features = numerical_features
    column_mapping.categorical_features = categorical_features

    # stattest_threshold: Sets the drift threshold in a given column or all columns.
    # drift_share:        over 70% columns are drifting --> detect dataset drift (default = 0.5)
    data_drift = Report(
            metrics=[DataDriftPreset(stattest_threshold=0.2, drift_share=0.7)], 
            options={"render": {"raw_data": True}}
        )

    cnt = len(df)
    split = int(cnt * 70/100)
    data_drift.run(
        current_data=df[split:],
        reference_data=df[:split],
        column_mapping=column_mapping
    )
    data_drift.save_html(data_drift_report.path)
    
    # Upload Report to Project on Evidently UI
    workspace = "http://43.200.50.207:8000"
    ws = RemoteWorkspace(workspace)

    project_name = "mlops-2025"
    if not any(p.name == project_name for p in ws.list_projects()):
        print(f"Project does not exist. \nGenerating project {project_name}...")
        ws.create_project(name=project_name, description="Project for LG Enterprise MLOPs 2025")
    project = ws.search_project(project_name=project_name)[0]
    print(f"--- Project info: --- \nProject Name: {project.name} \nProject ID: {project.id}")
    ws.add_report(project_id=project.id, report=data_drift)
    print(f'--- Add Data Drift Report to project {project_name}')

    data_drift_dict = data_drift.as_dict()["metrics"]
    drift_metric = next(
        filter(lambda item: item["metric"] == "DatasetDriftMetric", data_drift_dict)
    )
    drift_metric_table = next(
        filter(lambda item: item["metric"] == "DataDriftTable", data_drift_dict)
    )

    feature_drift = []
    for feature, drift_analysis in drift_metric_table["result"][
        "drift_by_columns"
    ].items():
        feature_drift.append(
            [
                feature,
                drift_analysis["drift_detected"],
                drift_analysis["stattest_name"],
                drift_analysis["stattest_threshold"],
                drift_analysis["drift_score"],
            ]
        )
    print(
        tabulate(
            pd.DataFrame(
                feature_drift,
                columns=["Feature", "Drift", "Method", "Threshold", "Value"],
            ),
            headers="keys",
            tablefmt="psql",
        )
    )
    print(
        tabulate(
            pd.DataFrame(
                list(drift_metric["result"].items()), columns=["Key", "Value"]
            ),
            headers="keys",
            tablefmt="psql",
        )
    )
    
    # Extract dataset-level drift
    dataset_drift_value = drift_metric["result"]["dataset_drift"]
    number_of_drifted_columns = drift_metric["result"]["number_of_drifted_columns"]
    print(f'--- Monitor data: --- \ndataset_drift: {dataset_drift_value} \nnum_of_columns_is_drifted: {number_of_drifted_columns}')

    with open(alert_data.path, "w") as f:
        json.dump(
            {
                "dataset_drift": dataset_drift_value,
                "num_of_drifted_columns": number_of_drifted_columns
            },
            f
        )