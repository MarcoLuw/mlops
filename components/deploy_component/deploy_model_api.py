from kfp import dsl
from kfp.dsl import Input, Output, Dataset
@dsl.component(
    base_image='hoanganh26/python-mlops:latest'
)
def deploy_model(mlflow_experiment_data: Input[Dataset], service_account_name: str, infer_namespace: str):
    from kubernetes import client 
    import kserve
    import json
    import os

    # MLFLOW_REGISTERED_MODEL_NAME = "bike-sharing-model"
    # MLFLOW_BUCKET_NAME = "lg-mlflow-compose-bucket"

    mlflow_registered_model_name = os.environ['MLFLOW_REGISTERED_MODEL_NAME']
    mlflow_bucket_name = os.environ['MLFLOW_BUCKET_NAME']

    with open(mlflow_experiment_data.path, "r") as f:
        data = json.load(f)
    
    model_version = "latest"

    storage_uri = (
        "s3://{bucket_name}/{experiment_id}/{run_id}/artifacts/{model_path}".format(
            bucket_name=mlflow_bucket_name,
            experiment_id=data["experiment_id"],
            run_id=data["child_run_id"],
            model_path="model",  # this is path when we log model
        )
    )

    isvc_name = "mlflow-v2-bsd"
    isvc = kserve.V1beta1InferenceService(
        api_version=kserve.constants.KSERVE_GROUP + "/v1beta1",
        kind=kserve.constants.KSERVE_KIND,
        metadata=client.V1ObjectMeta(
            name=isvc_name,
            namespace=infer_namespace,
            labels={
                "mlflow/model-name": mlflow_registered_model_name,
                "mlflow/model-version": model_version,
                # "modelregistry/registered-model-id": model.id,
                # "modelregistry/model-version-id": version.id,
            },
            annotations={"sidecar.istio.io/inject": "true"},
        ),
        spec=kserve.V1beta1InferenceServiceSpec(
            predictor=kserve.V1beta1PredictorSpec(
                service_account_name=service_account_name,
                model=kserve.V1beta1ModelSpec(
                    # The protocol is model-registry://{modelName}/{modelVersion}
                    storage_uri=storage_uri,
                    model_format=kserve.V1beta1ModelFormat(
                        # for mlflow, version is not needed
                        # name=art.model_format_name, version=art.model_format_version
                        name="mlflow"
                    ),
                    protocol_version=kserve.constants.PredictorProtocol.REST_V2.value,
                ),
            )
        ),
    )

    ks_client = kserve.KServeClient()
    result = None

    try:
        if ks_client.get(isvc_name):
            print(f"InferenceService '{isvc_name}' exists, replacing/patching ...")
            # we can do delete as well
            # ks_client.delete(isvc_name)
            # result = ks_client.patch(isvc_name, isvc)
            result = ks_client.replace(isvc_name, isvc)
    except client.ApiException as e:
        if e.status == 404:
            print(f"InferenceService '{isvc_name}' not exist, creating ...")
            result = ks_client.create(isvc)
        else:
            raise
    except Exception as e:
        print(
            f"Got exception {e} when get InferenceService '{isvc_name}', anyway creating ..."
        )
        result = ks_client.create(isvc)
    finally:
        if result != None:
            print(result)
            print(f"InferenceService '{isvc_name}' waiting for ready ...")
            ks_client.wait_isvc_ready(isvc_name)