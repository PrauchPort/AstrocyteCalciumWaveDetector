from datetime import timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash_operator import BashOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.utils.weight_rule import WeightRule
import os
from astrowaves.airflow.utils import process_task_name

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}
dag = DAG(
    "1_extract_waves",
    default_args=default_args,
    description="A simple tutorial DAG",
    schedule_interval=timedelta(days=1),
)


rootdir = "/app/data"

filename = Variable.get("filename")

if filename == "all":
    files = [file for file in os.listdir(rootdir) if file.endswith(".tif")]
else:
    files = [filename]

for file in files:
    filename = file
    directory = filename.split(".")[0]
    directory = process_task_name(directory)

    # the task to create a timelapse array from the tiff file
    t1 = BashOperator(
        task_id=f"create_timelapse_{directory}",
        bash_command=f"python3.9 -m astrowaves.tasks.TimelapseCreator --filename {filename} --directory {directory}",
        dag=dag,
        weight_rule=WeightRule.UPSTREAM,
    )

    # the task to extract calcium events from the timelapse
    t3 = BashOperator(
        task_id=f"extract_waves_{directory}",
        depends_on_past=False,
        bash_command=f"python3.9 -m astrowaves.tasks.CalciumWavesExtractor --directory {directory}",
        dag=dag,
        weight_rule=WeightRule.UPSTREAM,
    )

    standard_deviation_threshold = Variable.get("sd_threshold")
    use_watershed = Variable.get("use_watershed")

    # the task to create masks from the timelapse
    t4 = BashOperator(
        task_id=f"create_masks_{directory}",
        depends_on_past=False,
        bash_command=f"python3.9 -m astrowaves.tasks.MaskGenerator --std {standard_deviation_threshold} --directory {directory} --use_watershed {use_watershed}",
        dag=dag,
        weight_rule=WeightRule.UPSTREAM,
    )

    t1 >> t3 >> t4

dag.doc_md = __doc__

t1.doc_md = """\
#### Task Documentation
This task is responsible for extraction of the calcium events from the raw tiff file of the timelapse
"""
