# Logs repo

## LATEST USAGE

source venv/Scripts/activate

cd logs_storage/202X_XX_XX_xxx/

python ../../pull_and_convert.py \
  --host brzanpi@192.168.1.49 \
  --remote-dir "home/brzanpi/ws_minicelka/rpi-controller-mini-celka/src/logs_runtime" \
  --local-dir ./logs_raw \
  --parquet-dir ./logs_parquet 

OPTIONAL ARGUMENT
  --delete-remote


## Requirements
- Python 3.x (I am using 3.11)
- ```requirements.txt```
- PlotJuggler (I am using 3.12.2)


### Plot jugger parser
1. Activate the venv ```source venv/Scripts/activate```
2. Read the readme in the ``` plot_juggler_parser/readme.md```

### First ever launch of python enviroment:
1. Install appropriate version of Python, and navigate to the repo
2. Run the ```python -m venv venv```
3. Activate the enviroment ```source venv/Scripts/activate```
4. Installation of the packages ```pip install pymavlink```
5. When all packages are installed save requirements with ```pip freeze > requirements.txt```
6. To exit venv ```deactivate```

### Launching the enviroment after cloning or moving to a new machine:
1. Install appropriate version of Python, and navigate to the repo
2. Run the ```python -m venv venv```
3. Activate the enviroment ```source venv/Scripts/activate```
4. Install the packages ```pip install -r requirements.txt```
6. To exit venv ```deactivate```

