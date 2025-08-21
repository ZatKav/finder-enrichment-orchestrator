#!/usr/bin/env python3
"""
Script to setup and run Kafka UI for monitoring the Finder project's Kafka instance.
"""
import os
import subprocess
import sys
import tempfile
import signal
import time
from pathlib import Path

def check_java():
    """Check if Java 17+ is installed."""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Java not found"
        
        # Parse Java version from stderr (where java -version outputs)
        version_output = result.stderr if result.stderr else result.stdout
        
        # Extract version number (handles both Oracle and OpenJDK formats)
        import re
        version_match = re.search(r'"(\d+)\.', version_output)
        if not version_match:
            version_match = re.search(r'openjdk version "(\d+)', version_output)
        
        if version_match:
            major_version = int(version_match.group(1))
            if major_version >= 17:
                return True, f"Java {major_version} found"
            else:
                return False, f"Java {major_version} found, but Java 17+ is required"
        
        return False, "Could not determine Java version"
    except FileNotFoundError:
        return False, "Java not found in PATH"

def verify_jar_file(jar_path):
    """Verify that the JAR file is valid."""
    try:
        # Check if file exists and has content
        if not jar_path.exists() or jar_path.stat().st_size == 0:
            return False
        
        # Try to read the JAR file header (should start with 'PK')
        with open(jar_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'PK')
    except Exception:
        return False

def download_kafka_ui(force_download=False):
    """Download Kafka UI JAR file."""
    kafka_ui_dir = Path.home() / '.kafka-ui'
    kafka_ui_dir.mkdir(exist_ok=True)
    
    jar_path = kafka_ui_dir / 'kafka-ui-api-v0.7.2.jar'
    
    # Check if file exists and is valid
    if jar_path.exists() and not force_download:
        if verify_jar_file(jar_path):
            print(f"✅ Kafka UI already downloaded at: {jar_path}")
            return jar_path
        else:
            print(f"⚠️  Existing JAR file is corrupted, re-downloading...")
            jar_path.unlink()  # Remove corrupted file
    
    print("📥 Downloading Kafka UI...")
    download_url = "https://github.com/provectus/kafka-ui/releases/download/v0.7.2/kafka-ui-api-v0.7.2.jar"
    
    try:
        # Use curl to download with progress bar and better error handling
        subprocess.run([
            'curl', '-L', '--fail', '--progress-bar', 
            '-o', str(jar_path), download_url
        ], check=True)
        
        # Verify the downloaded file
        if verify_jar_file(jar_path):
            file_size = jar_path.stat().st_size / (1024 * 1024)  # Size in MB
            print(f"✅ Kafka UI downloaded successfully ({file_size:.1f} MB)")
            return jar_path
        else:
            print("❌ Downloaded file is not a valid JAR file")
            jar_path.unlink()  # Remove invalid file
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to download Kafka UI: {e}")
        print("💡 Try using a different download method:")
        print(f"   curl -L -o {jar_path} {download_url}")
        print("   Or download manually from: https://github.com/provectus/kafka-ui/releases/tag/v0.7.2")
        sys.exit(1)

def create_config_file():
    """Create Kafka UI configuration file."""
    config_content = """
kafka:
  clusters:
    - name: finder-local
      bootstrapServers: localhost:9092

auth:
  type: disabled

management:
  health:
    ldap:
      enabled: false

server:
  port: 8080
"""
    
    config_dir = Path.home() / '.kafka-ui'
    config_path = config_dir / 'application.yml'
    
    with open(config_path, 'w') as f:
        f.write(config_content.strip())
    
    print(f"Configuration file created: {config_path}")
    return config_path

def run_kafka_ui(jar_path, config_path):
    """Run Kafka UI."""
    print("\n" + "="*60)
    print("🚀 Starting Kafka UI for Finder project")
    print("="*60)
    print(f"📊 Web UI will be available at: http://localhost:8080")
    print(f"🔗 Kafka cluster: localhost:9093")
    print(f"📝 Config file: {config_path}")
    print("="*60)
    print("\nPress Ctrl+C to stop the UI")
    print("-"*60)
    
    try:
        # Run Kafka UI
        jar_file = jar_path if jar_path.name.endswith('.jar') else jar_path / 'kafka-ui-api-v0.7.2.jar'
        process = subprocess.Popen([
            'java',
            '-Dspring.config.additional-location=' + str(config_path),
            '-jar', str(jar_file)
        ])
        
        # Wait for the process
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping Kafka UI...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Kafka UI stopped")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup and run Kafka UI for the Finder project')
    parser.add_argument('--force-download', action='store_true', 
                       help='Force re-download of Kafka UI even if it exists')
    args = parser.parse_args()
    
    print("🔧 Setting up Kafka UI for the Finder project...")
    
    # Check prerequisites
    java_ok, java_message = check_java()
    if not java_ok:
        print(f"❌ {java_message}")
        print("Please install Java 17+:")
        print("  Using sdkman: sdk install java 17.0.15-amzn")
        print("  Using brew: brew install openjdk@17")
        sys.exit(1)
    
    print(f"✅ {java_message}")
    
    # Download Kafka UI
    jar_path = download_kafka_ui(force_download=args.force_download)
    
    # Create config file
    config_path = create_config_file()
    
    # Run Kafka UI
    run_kafka_ui(jar_path, config_path)

if __name__ == "__main__":
    main() 