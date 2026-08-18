import subprocess

steps = ['data_collection.py', 'data_prep.py', 'train_models.py', 'llm_report.py']

for step in steps:
    print('\n--- Running', step, '---')
    result = subprocess.run(['python', step])
    if result.returncode != 0:
        print(step, 'failed, stopping pipeline.')
        break