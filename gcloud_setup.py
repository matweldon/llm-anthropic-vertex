#!/usr/bin/env python3
"""
Utility command to validate and set up Google Cloud credentials for Vertex AI.

This tool checks:
1. gcloud SDK installation
2. Application Default Credentials (ADC) existence and validity
3. Google Cloud project configuration
4. Vertex AI API enablement
5. Region configuration
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(message: str):
    """Print a success message in green."""
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def print_warning(message: str):
    """Print a warning message in yellow."""
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


def print_error(message: str):
    """Print an error message in red."""
    print(f"{Colors.RED}✗{Colors.END} {message}")


def print_info(message: str):
    """Print an info message in blue."""
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def check_gcloud_installed() -> bool:
    """Check if gcloud SDK is installed."""
    try:
        result = subprocess.run(
            ['gcloud', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print_success(f"gcloud SDK is installed: {version}")
            return True
        else:
            print_error("gcloud SDK is not working properly")
            return False
    except FileNotFoundError:
        print_error("gcloud SDK is not installed")
        print_info("Install it from: https://cloud.google.com/sdk/docs/install")
        return False


def get_adc_path() -> Optional[Path]:
    """Get the path to Application Default Credentials."""
    # Check GOOGLE_APPLICATION_CREDENTIALS environment variable first
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        path = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
        if path.exists():
            return path

    # Check default ADC location
    if sys.platform == 'win32':
        default_path = Path(os.environ.get('APPDATA', '')) / 'gcloud' / 'application_default_credentials.json'
    else:
        default_path = Path.home() / '.config' / 'gcloud' / 'application_default_credentials.json'

    if default_path.exists():
        return default_path

    return None


def check_credential_expiry(creds: dict) -> Tuple[bool, Optional[str]]:
    """
    Check if credentials are expired or about to expire.

    Returns:
        Tuple of (is_valid, credential_type)
        where credential_type is 'user', 'service_account', or 'other'
    """
    credential_type = creds.get('type', 'unknown')

    # Service account credentials don't expire
    if credential_type == 'service_account':
        return True, 'service_account'

    # Check if it's authorized user credentials
    if credential_type == 'authorized_user':
        # Check for refresh token expiry if present
        if 'expiry' in creds:
            try:
                expiry = datetime.fromisoformat(creds['expiry'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                if expiry < now:
                    return False, 'user'
            except (ValueError, AttributeError):
                pass
        return True, 'user'

    return True, 'other'


def check_adc() -> Tuple[bool, Optional[str]]:
    """
    Check Application Default Credentials existence and validity.

    Returns:
        Tuple of (is_valid, credential_type)
    """
    adc_path = get_adc_path()

    if not adc_path:
        print_error("Application Default Credentials not found")
        print_info("Run one of the following commands:")
        print_info("  For user credentials: gcloud auth application-default login")
        print_info("  For service account: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        return False, None

    print_success(f"Found Application Default Credentials at: {adc_path}")

    # Read and validate credentials
    try:
        with open(adc_path, 'r') as f:
            creds = json.load(f)

        is_valid, cred_type = check_credential_expiry(creds)

        if not is_valid:
            print_error("Credentials have expired")
            if cred_type == 'user':
                print_info("Run: gcloud auth application-default login")
            elif cred_type == 'service_account':
                print_info("Service account key may be invalid. Check your GOOGLE_APPLICATION_CREDENTIALS")
            return False, cred_type

        if cred_type == 'user':
            print_success("User account credentials are valid")
        elif cred_type == 'service_account':
            print_success("Service account credentials are configured")
        else:
            print_success("Credentials appear to be valid")

        return True, cred_type

    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Error reading credentials: {e}")
        return False, None


def get_current_project() -> Optional[str]:
    """Get the current gcloud project."""
    try:
        result = subprocess.run(
            ['gcloud', 'config', 'get-value', 'project'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            project = result.stdout.strip()
            if project and project != '(unset)':
                return project
    except FileNotFoundError:
        pass
    return None


def set_project_env_var(project: str) -> bool:
    """Set the GOOGLE_CLOUD_PROJECT environment variable."""
    # Check if already set
    existing = os.environ.get('GOOGLE_CLOUD_PROJECT')
    if existing:
        if existing == project:
            print_success(f"GOOGLE_CLOUD_PROJECT already set to: {project}")
            return True
        else:
            print_warning(f"GOOGLE_CLOUD_PROJECT is set to '{existing}' but active project is '{project}'")
            response = input(f"Update to '{project}'? [Y/n]: ").strip().lower()
            if response and response != 'y':
                print_info("Keeping existing GOOGLE_CLOUD_PROJECT value")
                return True

    # For the current session (this only affects subprocesses, not the parent shell)
    os.environ['GOOGLE_CLOUD_PROJECT'] = project

    # Provide instructions for permanent setup
    print_success(f"Set GOOGLE_CLOUD_PROJECT={project} for this session")
    print_info("\nTo make this permanent, add to your shell configuration:")

    shell = os.environ.get('SHELL', '')
    if 'bash' in shell:
        config_file = '~/.bashrc'
    elif 'zsh' in shell:
        config_file = '~/.zshrc'
    elif 'fish' in shell:
        config_file = '~/.config/fish/config.fish'
        print_info(f"  echo 'set -gx GOOGLE_CLOUD_PROJECT {project}' >> {config_file}")
        return True
    else:
        config_file = 'your shell configuration file'

    print_info(f"  echo 'export GOOGLE_CLOUD_PROJECT={project}' >> {config_file}")

    return True


def get_region() -> Optional[str]:
    """Get the region, checking environment and gcloud config, or prompting user."""
    # Check environment variables
    region = os.environ.get('GOOGLE_CLOUD_REGION') or os.environ.get('GCP_REGION')
    if region:
        print_success(f"Using region from environment: {region}")
        return region

    # Check gcloud config
    try:
        result = subprocess.run(
            ['gcloud', 'config', 'get-value', 'compute/region'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            region = result.stdout.strip()
            if region and region != '(unset)':
                print_success(f"Using region from gcloud config: {region}")
                response = input(f"Use this region? [Y/n]: ").strip().lower()
                if not response or response == 'y':
                    return region
    except FileNotFoundError:
        pass

    # Prompt user
    print_info("\nCommon Vertex AI regions:")
    print_info("  us-central1    (Iowa)")
    print_info("  us-east4       (Virginia)")
    print_info("  europe-west1   (Belgium)")
    print_info("  europe-west4   (Netherlands)")
    print_info("  asia-southeast1 (Singapore)")
    print_info("\nFor the full list, see: https://cloud.google.com/vertex-ai/docs/general/locations")

    while True:
        region = input("\nEnter your region (default: europe-west1): ").strip()
        if not region:
            region = 'europe-west1'

        # Validate region format (basic check)
        if region.count('-') >= 2 or region in ['us-central1', 'us-east4', 'europe-west1', 'europe-west4', 'asia-southeast1']:
            break
        else:
            print_warning("Region format looks incorrect. Please use format like 'us-central1'")

    # Set environment variable
    os.environ['GOOGLE_CLOUD_REGION'] = region
    print_success(f"Set GOOGLE_CLOUD_REGION={region} for this session")

    # Provide instructions for permanent setup
    print_info("\nTo make this permanent, add to your shell configuration:")
    shell = os.environ.get('SHELL', '')
    if 'bash' in shell:
        config_file = '~/.bashrc'
    elif 'zsh' in shell:
        config_file = '~/.zshrc'
    elif 'fish' in shell:
        config_file = '~/.config/fish/config.fish'
        print_info(f"  echo 'set -gx GOOGLE_CLOUD_REGION {region}' >> {config_file}")
        return region
    else:
        config_file = 'your shell configuration file'

    print_info(f"  echo 'export GOOGLE_CLOUD_REGION={region}' >> {config_file}")

    return region


def check_vertex_api_enabled(project: str) -> bool:
    """Check if Vertex AI API is enabled for the project."""
    try:
        result = subprocess.run(
            [
                'gcloud', 'services', 'list',
                '--enabled',
                '--filter=name:aiplatform.googleapis.com',
                '--format=value(name)',
                f'--project={project}'
            ],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            if 'aiplatform.googleapis.com' in result.stdout:
                print_success("Vertex AI API is enabled")
                return True
            else:
                print_warning("Vertex AI API is not enabled")
                print_info("Enable it with:")
                print_info(f"  gcloud services enable aiplatform.googleapis.com --project={project}")
                print_info("Or visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com")
                return False
        else:
            # May not have permission to check
            print_warning("Could not verify if Vertex AI API is enabled")
            print_info(f"Error: {result.stderr.strip()}")
            print_info("You may not have permission to list services, or the API might not be enabled")
            return False

    except FileNotFoundError:
        print_warning("Could not check Vertex AI API status (gcloud not available)")
        return False


def main():
    """Main function to run all validation checks."""
    print(f"\n{Colors.BOLD}Google Cloud Vertex AI Setup Validator{Colors.END}\n")

    # Step 1: Check gcloud SDK
    if not check_gcloud_installed():
        print_error("\n❌ Setup incomplete: gcloud SDK not found")
        return 1

    print()

    # Step 2: Check ADC
    adc_valid, cred_type = check_adc()
    if not adc_valid:
        print_error("\n❌ Setup incomplete: Application Default Credentials not valid")
        return 1

    print()

    # Step 3: Get and set project
    project = get_current_project()
    if not project:
        print_error("No active gcloud project found")
        print_info("Set a project with: gcloud config set project PROJECT_ID")
        print_error("\n❌ Setup incomplete: No project configured")
        return 1

    print_success(f"Active gcloud project: {project}")
    if not set_project_env_var(project):
        print_error("\n❌ Setup incomplete: Could not set project environment variable")
        return 1

    print()

    # Step 4: Get region
    region = get_region()
    if not region:
        print_error("\n❌ Setup incomplete: No region configured")
        return 1

    print()

    # Step 5: Check Vertex AI API
    api_enabled = check_vertex_api_enabled(project)

    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Setup Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    print_success(f"Project: {project}")
    print_success(f"Region: {region}")
    print_success(f"Credentials: {cred_type or 'configured'}")

    if api_enabled:
        print_success("Vertex AI API: enabled")
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed!{Colors.END}")
        print_info("\nYou can now use llm-anthropic-vertex:")
        print_info(f"  llm -m vertex-4.5-sonnet 'Hello!'")
        return 0
    else:
        print_warning("Vertex AI API: not verified/enabled")
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Setup mostly complete, but please enable Vertex AI API{Colors.END}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
