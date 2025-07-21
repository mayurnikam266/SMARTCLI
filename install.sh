#!/bin/bash
#
# Production Installer for SmartCLI
# This script installs the 'scli' tool on a user's system, making it
# feel like a native application by managing a Docker container behind the scenes.
#
# Usage: curl -sSL https://raw.githubusercontent.com/mayurnikam266/SMARTCLI/main/install.sh | sudo bash

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
IMAGE_NAME="mayurnikam266/smartcli:latest"
INSTALL_DIR="/usr/local/bin"
CMD_NAME="scli"
WRAPPER_PATH="${INSTALL_DIR}/${CMD_NAME}"

# --- Helper Functions ---
print_info() {
    # Blue color for info
    echo -e "\033[34m[INFO]\033[0m $1"
}

print_success() {
    # Green color for success
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_error() {
    # Red color for error
    echo -e "\033[31m[ERROR]\033[0m $1" >&2
    exit 1
}

# --- Main Installation Logic ---
print_info "Starting SmartCLI installation..."

# 1. Check for root/sudo privileges
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run with sudo or as root to install to ${INSTALL_DIR}."
fi

# 2. Check if Docker is installed and running
if ! command -v docker &> /dev/null || ! docker info >/dev/null 2>&1; then
    print_error "Docker is not installed or not running. Please install and start Docker before running this script."
fi

# 3. Pull the latest Docker image from Docker Hub
print_info "Pulling the latest Docker image: ${IMAGE_NAME}..."
if ! docker pull "${IMAGE_NAME}"; then
    print_error "Failed to pull Docker image. Please check the image name and your internet connection."
fi
print_info "Image pulled successfully."

# 4. Create the wrapper script that will be installed on the user's system
print_info "Creating the command wrapper at ${WRAPPER_PATH}..."
cat > "${WRAPPER_PATH}" << EOF
#!/bin/bash
# Wrapper for the SmartCLI tool

# Configuration
IMAGE="${IMAGE_NAME}"
CONFIG_FILE="config.yaml"

# Check if a config file exists in the current directory.
# If it does, set up the arguments to mount it inside the container.
CONFIG_MOUNT_ARGS=()
if [ -f "\$(pwd)/\${CONFIG_FILE}" ]; then
    CONFIG_MOUNT_ARGS=("-v" "\$(pwd)/\${CONFIG_FILE}:/app/\${CONFIG_FILE}:ro")
fi

# Execute the command inside the Docker container.
# This version mounts the host's binary directories to allow executing any host command.
exec docker run --rm -it \\
  "\${CONFIG_MOUNT_ARGS[@]}" \\
  -v /bin:/host/bin:ro \\
  -v /usr/bin:/host/usr/bin:ro \\
  -v "\$(pwd):/app/data" \\
  "\${IMAGE}" "\$@"
EOF

# 5. Make the wrapper script executable
chmod +x "${WRAPPER_PATH}"
print_info "Wrapper script created and made executable."

# --- Final Message ---
print_success "SmartCLI has been installed successfully!"
print_info "You can now run the tool from any terminal by typing: scli"
print_info "Example: scli help"
print_info "IMPORTANT: Before first use, create a 'config.yaml' file in your project directory."

