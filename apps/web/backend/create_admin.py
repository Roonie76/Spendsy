import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Replace with your actual project name
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_superuser():
    username = "Tanu"
    email = "admin@example.com"
    password = "T@nu2004" # Change this!

    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser: {username}")
        User.objects.create_superuser(username, email, password)
    else:
        print("Superuser already exists.")

if __name__ == "__main__":
    create_superuser()