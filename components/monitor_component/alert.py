import kfp
from kfp import dsl
from kfp.dsl import Input, Dataset

@dsl.component(
    base_image='hoanganh26/python-mlops:latest'
)
def alert_model_degradation(alert_data: Input[Dataset]):
    """
    Alert will be sent to MS Teams if data drfit or model degradation are found.
    """
    import requests
    import json

    with open(alert_data.path, "r") as f:
        monitor_data = json.load(f)

    dataset_drift = int(monitor_data["dataset_drift"])
    num_of_drifted_columns = int(monitor_data["num_of_drifted_columns"])

    if dataset_drift != 1:
        print(f'-- Your model is resillient! No need to retrain --')
    
    # Trigger retrain if dataset is drifted
    power_automate_webhook_url = 'https://prod-89.southeastasia.logic.azure.com:443/workflows/0a23ef526a284a6895d9cfa747263a6b/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=tK0ij-sWt1So0ohRgyDFa2xt9ZN4tqBsCK1saqdIUp4'  # MS Teams HTTP trigger URL
    
    payload = {
        "drift_detected": True,
        "details": f"Number of drifted columns: {num_of_drifted_columns}"
    }

    requests.post(power_automate_webhook_url, json=payload)