#!/usr/bin/env python
"""
Setup script that uses Django commands to generate boilerplate code.
Run this after installing dependencies: pip install -r requirements.txt
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        if "already exists" not in result.stderr.lower():
            return False
    else:
        print(result.stdout)
    return True

def main():
    """Main setup function."""
    print("Django Backend Setup Script")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("Error: requirements.txt not found. Please run from backend directory.")
        sys.exit(1)
    
    # Step 1: Create Django project
    if not os.path.exists("rural_health_connect"):
        run_command(
            "django-admin startproject rural_health_connect .",
            "Creating Django project 'rural_health_connect'"
        )
    else:
        print("Django project already exists, skipping...")
    
    # Step 2: Create API app
    if not os.path.exists("api"):
        run_command(
            "python manage.py startapp api",
            "Creating API app"
        )
    else:
        print("API app already exists, skipping...")
    
    # Step 3: Create appointments app
    if not os.path.exists("appointments"):
        run_command(
            "python manage.py startapp appointments",
            "Creating appointments app"
        )
    else:
        print("Appointments app already exists, skipping...")
    
    # Step 4: Create video_calls app
    if not os.path.exists("video_calls"):
        run_command(
            "python manage.py startapp video_calls",
            "Creating video_calls app"
        )
    else:
        print("Video calls app already exists, skipping...")
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure settings.py (see README.md)")
    print("2. Run migrations: python manage.py migrate")
    print("3. Create superuser: python manage.py createsuperuser")
    print("4. Run server: python manage.py runserver")

if __name__ == "__main__":
    main()

