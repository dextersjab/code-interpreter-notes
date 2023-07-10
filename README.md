# Notes about ChatGPT's Code Interpreter

## Project Structure

This repository primarily contains notes and documentation about OpenAI's Code
Interpreter. Important files include:

- `system_prompt.md`: A file containing the system prompt for the Code
  Interpreter.
- `requirements.txt`: A list of Python package dependencies required for Code
  Interpreter.
- `dev_scripts`: A directory containing utility scripts that assist in the
  exploration
  and understanding of Code Interpreter's capabilities.

## Environment

Below is what Code Interpreter reveals about its working environment.

### Python Environment

The Python environment in which the code is executed is
based on Python 3. Python is a high-level, interpreted, and general-purpose
dynamic programming language that focuses on code readability. The Python
Software Foundation's standard runtime environment is used, which includes a
wide variety of standard libraries.

Libraries can be found in [requirements.txt](requirements.txt).

### Package Management

Python packages are managed using pip, the standard package
manager for Python. You can install, upgrade, and remove Python packages using
pip.

### Jupyter Notebook Environment

The code execution takes place in a Jupyter
Notebook environment. Jupyter is an open-source web application that allows the
creation and sharing of documents that contain live code, equations,
visualizations, and narrative text. The Jupyter notebook is an interactive
computing environment that enables users to author notebook documents that
include code, widgets, plots, and narrative text. The notebook extends the
console-based approach to interactive computing in a qualitatively new
direction, providing a web-based application suitable for capturing the whole
computation process.

### Execution Time

Python code that you send for execution will time out after 120
seconds if it doesn't complete. This is to ensure that long-running code doesn't
lock up the interactive environment.

### File Storage

Files can be stored and persisted in the /mnt/data directory. This
allows you to upload and download files from the Jupyter environment. Note that
these files will be available only for the duration of your current session and
will not be preserved across different sessions.

### Internet Access

The Python environment does not have internet access. This
means that you cannot make HTTP requests or API calls directly from your Python
code. This is a security feature designed to prevent unauthorized network
activity.

### Code Interpreter

The OpenAI's Code Interpreter allows ChatGPT to interpret and
execute Python code within the Jupyter Notebook environment. This can be used
for running Python scripts, performing computations, generating plots, and more.

### Environment Isolation

Each session operates in an isolated environment. This
means your code won't have access to the underlying operating system, ensuring
the safety and privacy of your data.

### Containerization

The Python and Jupyter environments are containerized. This
means that each user session is isolated within its own environment, which
includes a specific version of Python and certain pre-installed packages. This
isolation ensures that the Python code execution environment is consistent
across all sessions and users. Containers are lightweight and portable, which
makes it easy to manage and scale the infrastructure.

### Kubernetes

Kubernetes is used to orchestrate the containers. It is responsible
for deploying containers, scaling them according to demand, and managing their
lifecycle. Kubernetes also handles networking between containers and provides
services like load balancing, service discovery, and secret management.

### Networking

Within the Kubernetes cluster, each container has its own IP address
and can communicate with other containers using standard TCP/IP protocols.
However, for security reasons, the containers are isolated from the internet and
cannot make outgoing network requests. This means that you can't fetch data from
the web or call APIs directly from your Python code.

### Storage

While containers themselves are ephemeral (meaning they are destroyed
when the session ends), data can be stored and persisted using volumes. In this
environment, the /mnt/data directory is mounted as a volume, so you can use it
to save and load files within a session.

### File Storage

Files can be stored and persisted in the /mnt/data directory. This allows you to
upload and download files from the Jupyter environment. The /home/sandbox
directory is the default working directory, where scripts are executed and where
relative paths are resolved from. Note that these files will be available only
for the duration of your current session and will not be preserved across
different sessions.

### Security

The use of containers and Kubernetes also provides a number of
security benefits. The isolation between containers helps to limit the impact of
security vulnerabilities. In addition, network policies can be used to control
which containers can communicate with each other, and Role-Based Access
Control (RBAC) can be used to control who can access the Kubernetes API and what
actions they can perform.

### User Sessions and Container Communication

In the context of the Code Interpreter, each user session operates within a
single, isolated container. This container includes both the language model and
the Python execution environment. Importantly, containers associated with
different user sessions do not communicate with each other, ensuring the privacy
and security of each individual session.

## Contribution

Contributions to this repository are welcome. If you have additional notes or
scripts that you believe would benefit others in understanding or using OpenAI's
Code Interpreter, feel free to create a pull request.
