import argparse
import json
import kfp
from kfp.client import Client
from kfp_client_manager import KFPClientManager

def argparse_pipeline():
    parser = argparse.ArgumentParser(description="Create a run for an uploaded Kubeflow pipeline.")
    parser.add_argument(
        "--host",
        type=str,
        default="http://43.200.50.207:8080/pipeline",
        help="Kubeflow Pipelines host URL (default: http://43.200.50.207:8080/pipeline)"
    )
    parser.add_argument(
        "--pipeline_name",
        type=str,
        required=True,
        help="Name of the uploaded pipeline"
    )
    parser.add_argument(
        "--experiment_name",
        type=str,
        required=True,
        help="Name of the uploaded pipeline"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="kubeflow-user-example-com",
        help="Kubernetes namespace for Kubeflow (default: kubeflow-user-example-com)"
    )
    parser.add_argument(
        "--pipeline_package_path",
        type=str,
        default="manifests/bike_sharing_pipeline.yaml",
        help="Path of a compiled pipeline package file"
    )
    parser.add_argument(
        "--pipeline_version_name",
        type=str,
        default=None,
        help="Name of the pipeline version to be shown in the UI"
    )
    parser.add_argument(
        "--run_name",
        type=str,
        default=None,
        help="Name of the run (defaults to pipeline_name-timestamp if not provided)"
    )
    parser.add_argument(
        "--parameters",
        type=str,
        default=None,
        help="JSON string of pipeline parameters (e.g., '{\"param1\": \"value1\"}')"
    )

    return parser.parse_args()

def create_client(host):
    # initialize a KFPClientManager
    kfp_client_manager = KFPClientManager(
        api_url=host,
        skip_tls_verify=True,
        dex_username="user@example.com",
        dex_password="12341234",
        dex_auth_type="local"   # can be 'ldap' or 'local' depending on your Dex configuration
    )
    # get a newly authenticated KFP client
    # TIP: long-lived sessions might need to get a new client when their session expires
    kfp_client = kfp_client_manager.create_kfp_client()
    
    return kfp_client

def get_pipeline_version_count(client: Client, pipeline_name: str) -> int:
    pipeline_id = client.get_pipeline_id(pipeline_name)
    if not pipeline_id:
        raise ValueError(f"Pipeline '{pipeline_name}' not found. Please upload it first.")
    
    # List pipeline versions with a reasonable page size
    response = client.list_pipeline_versions(pipeline_id=pipeline_id, page_size=100)
    return response.total_size

def create_run_pipeline(host: str, pipeline_name: str, experiment_name: str, namespace: str, pipeline_package_path: str, pipeline_version_name: str = None, run_name: str = None, parameters: dict = None):
    client = create_client(host)

    list_pipeline = client.list_pipelines(
        page_size=100,
        filter=json.dumps({
            "predicates": [{
                "operation": "EQUALS",
                "key": "display_name",
                "stringValue": f'{pipeline_name}',
            }]
        }),
        namespace=namespace
    )

    # for pipeline in list_pipeline.pipelines:
    #     print(f"Pipeline ID: {pipeline.pipeline_id}, \nName: {pipeline.display_name}, \nCreated: {pipeline.created_at}")
    # print(f"Total pipelines: {list_pipeline.total_size}")

    pipeline_id = list_pipeline.pipelines[0].pipeline_id
    if not pipeline_id:
        raise ValueError(f"Pipeline '{pipeline_name}' not found. Please upload it first.")
    
    experiment_id = client.get_experiment(experiment_name=experiment_name, namespace=namespace).experiment_id
    if not experiment_id:
        raise ValueError(f"Experiment '{experiment_name}' not found. Please create it first.")
    
    # Set default run name if not provided
    if not run_name:
        from datetime import datetime
        now = datetime.now()
        run_name = f"{pipeline_name}-{now.strftime('%Y-%m-%d-%H-%M-%S')}"
    
    # Set default pipeline version name if not provided
    if not pipeline_version_name:
        # total_pipeline_versions = client.list_pipeline_versions(
        #     pipeline_id=pipeline_id,
        #     page_size=100
        # ).total_size
        from datetime import datetime
        now = datetime.now()
        pipeline_version_name = f"{pipeline_name}_version_{now.strftime('%Y-%m-%d-%H-%M-%S')}"
    
    print(
        f'pipeline_package_path={pipeline_package_path},\n pipeline_version_name={pipeline_version_name}, \n pipeline_id={pipeline_id}'
    )

    pipeline_version_id = client.upload_pipeline_version(
        pipeline_package_path=pipeline_package_path,
        pipeline_version_name=pipeline_version_name,
        pipeline_id=pipeline_id,
        description="Version of the latest pipeline",
    ).pipeline_version_id

    print(f'---- pipeline_version_id = {pipeline_version_id}------------')

    run = client.run_pipeline(
        experiment_id=experiment_id,
        pipeline_id=pipeline_id,
        job_name=run_name,
        version_id=pipeline_version_id,
        params=parameters or {}  # Use empty dict if no parameters provided
    )
    print(f"Run created with ID: {run.run_id}. Check status at: {host}/#/runs/details/{run.run_id}")

if __name__ == "__main__":
    args = argparse_pipeline()

    # Convert parameters from JSON string to dict if provided
    parameters = None
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
            if not isinstance(parameters, dict):
                raise ValueError("Parameters must be a JSON object (dictionary)")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for parameters: {e}")
    
    create_run_pipeline(args.host, args.pipeline_name, args.experiment_name, args.namespace, args.pipeline_package_path, args.pipeline_version_name, args.run_name, parameters)