import os

# Create directories
os.makedirs('simulation', exist_ok=True)
os.makedirs('strategies', exist_ok=True)
os.makedirs('api', exist_ok=True)
os.makedirs('tests', exist_ok=True)

with open('simulation/__init__.py', 'w') as f:
    pass
with open('strategies/__init__.py', 'w') as f:
    pass
with open('api/__init__.py', 'w') as f:
    pass
with open('tests/__init__.py', 'w') as f:
    pass
