#!/usr/bin/env python3
"""Redeploy retail-agent-kc (8060330902103785472) using gcloud CLI token credentials."""
import datetime
import os
import subprocess
import google.auth
import google.auth.credentials
from google.adk.cli import cli_deploy

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

PROJECT_ID = "alitch-ca-demo"
REGION = "us-central1"
KC_AGENT_ID = "8060330902103785472"


class GcloudTokenCredentials(google.auth.credentials.Credentials):
    def __init__(self):
        super().__init__()
        self.refresh(None)

    def refresh(self, request):
        tok = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
        self.token = tok
        self.expiry = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(minutes=50)

    @property
    def valid(self):
        return bool(self.token)


_creds = GcloudTokenCredentials()
google.auth.default = lambda *args, **kwargs: (_creds, PROJECT_ID)

if __name__ == "__main__":
    agent_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "agents", "agent_kc")
    )
    cli_deploy.to_agent_engine(
        agent_folder=agent_folder,
        project=PROJECT_ID,
        region=REGION,
        display_name="[Retail] retail-agent-kc",
        agent_engine_id=KC_AGENT_ID,
    )
