import pytest
import subprocess
import time
import httpx
import shutil

# Mark this test as requiring docker
# You can run it with `pytest -m docker` if you configure markers, 
# or just run it as part of the suite.
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker not available")
def test_docker_build_and_run():
    """
    Builds the Docker image and runs it, verifying the /health endpoint.
    WARNING: This test involves building an image and running a container, 
    which can be slow and resource intensive.
    """
    image_tag = "gemini-pythonwebapp:test"
    container_name = "gemini-test-container"
    host_port = 8001
    
    # 1. Build the image
    print(f"\nBuilding Docker image {image_tag}...")
    subprocess.run(
        ["docker", "build", "-t", image_tag, "."],
        check=True,
        capture_output=False # Let output show to debug build issues
    )

    # Clean up any existing container with the same name
    subprocess.run(
        ["docker", "rm", "-f", container_name], 
        capture_output=True
    )

    try:
        # 2. Run the container
        print(f"Running container {container_name} on port {host_port}...")
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:8000",
                image_tag
            ],
            check=True
        )

        # 3. Wait for the application to be ready
        url = f"http://localhost:{host_port}/health"
        max_retries = 20
        for i in range(max_retries):
            try:
                response = httpx.get(url)
                if response.status_code == 200:
                    print("Container is ready!")
                    break
            except httpx.RequestError:
                pass
            
            if i == max_retries - 1:
                # Get logs if we fail
                logs = subprocess.run(["docker", "logs", container_name], capture_output=True, text=True)
                pytest.fail(f"Container did not become ready. Logs:\n{logs.stdout}\n{logs.stderr}")
            
            time.sleep(1)

        # 4. Additional assertions
        # Check root endpoint
        root_response = httpx.get(f"http://localhost:{host_port}/")
        assert root_response.status_code == 200
        assert "Gemini" in root_response.text

    finally:
        # 5. Cleanup
        print(f"Stopping and removing container {container_name}...")
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
