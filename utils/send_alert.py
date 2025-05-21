# import requests

# power_automate_webhook_url = 'https://prod-89.southeastasia.logic.azure.com:443/workflows/0a23ef526a284a6895d9cfa747263a6b/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=tK0ij-sWt1So0ohRgyDFa2xt9ZN4tqBsCK1saqdIUp4'  # Your HTTP trigger URL

# payload = {
#     "drift_detected": True,
#     "details": "8 of 12 features drifted. Drift share = 66.6%."
# }

# requests.post(power_automate_webhook_url, json=payload)

import gitlab

repo_name = "mlops-kserve"
repo_url = "http://10.0.2.4/mlops-practice/mlops-kserve.git"
repo_dir = f"/tmp/{repo_name}"
git_username = "root"
git_passwd = "mlops2025"
auth_repo_url = f"http://{git_username}:{git_passwd}@{repo_url.split('http://')[1]}"

gl = gitlab.Gitlab(url=repo_url, http_username=git_username, http_password=git_passwd)
print(gl)