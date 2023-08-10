import requests
import json
import numpy as np
import pandas as pd
import time
from sys import argv, exit
from os.path import basename
from datetime import datetime

# https://stackoverflow.com/questions/69845270/use-pandas-style-using-comma-as-decimal-separator

def bepaal_datum_grenzen():
    if len(argv) == 2:
        start_datum = argv[1] + '-01'
        stop_dag= int(argv[1][-2:]) + 1
        stop_datum = argv[1][:4] + '-' + str(stop_dag).zfill(2) + '-01'
        
    elif len(argv) == 3:
        start_datum = min(argv[1],argv[2])
        stop_datum = max(argv[1],argv[2])
        
    else:
        print(f'\nMeegeven down-te-loaden maand, kan zo jjjj-mm bijv: {basename(__file__)} 2023-07')
        print(f'\nMeegeven start- en eind-datum, kan zo jjjj-mm-dd jjjj-mm-dd bijv: py {basename(__file__)} 2023-01-01 2023-01-19\nOndergrens wel, bovengrens niet inbegrepen.')
        year = datetime.now().year
        month = datetime.now().month - 1
        if month == 0:
            year = year - 1
            month = 12
            
        start_datum = str(year) + '-' + str(month).zfill(2) + '-01'
        stop_datum = str(year) + '-' + str(month + 1).zfill(2) + '-01'

    if not is_date_matching(start_datum):
        exit(f'\nStartdatum {start_datum} is niet de juiste datumnotatie (jjjj-mm-dd). Programma wordt afgebroken.\n')

    if not is_date_matching(stop_datum):
        exit(f'\nStopdatum {stop_datum} is niet de juiste datumnotatie (jjjj-mm-dd). Programma wordt afgebroken.\n')
   
    return start_datum, stop_datum 


def is_date_matching(date_str):
    try:
        if len(date_str) == 10:
            return bool(datetime.strptime(date_str, '%Y-%m-%d'))
        else:
            return False
    except ValueError:
        return False
        
        
def call_api():

    sep_output = ';'
    decimal_output = '.'

    start_datum, stop_datum = bepaal_datum_grenzen()

    columns = '*'
    
    output_map = '.\\data'
    output_fn = 'api_gegevens_'

    if len(argv) == 3:
        output_file_name = f'{output_map}\\{output_fn}{start_datum}_tot_{stop_datum}.csv'
    else:
        _ = start_datum[:4] + start_datum[5:7]  # bv 202301
        output_file_name = f'{output_map}\\{output_fn}{_}.csv'

    min_lengte = 20
    max_lengte = 50
    while True:
        key = input("Geef uw api-key voor civity (+Enter): ").strip()
        if len(key) < min_lengte:
            print(f'de opgegeven api-key {key} is te kort. Minimale lengte= {min_lengte}')
        elif len(key) > max_lengte:
            print(f'de opgegeven api-key {key} is te lang. Maximale lengte= {max_lengte}')
        else:
            break  
        
    headers = {
        'X-CKAN-API-Key': key
    }
    
    url = 'https://ckan-dataplatform-nl.dataplatform.nl/api/3/action/datastore_search_sql'
    
    params = {
        'resource_id': '4cfb5177-d3db-4efc-ac6f-351af75f9f92',
        'sql': f'SELECT {columns} from "provincie_utrecht_snuffelfiets_measurement_rydruofi"'\
                + f' WHERE "recording_timestamp" > \'{start_datum}\' AND "recording_timestamp" < \'{stop_datum}\'',
        'offset': 0,
        'limit': 9999999,
    }
    
    print(f'\nurl= {url}')
    print(f'\nsql-statement= {params["sql"]}')

    #begin kernprogramma
    start_time = time.time()
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 403:
        print(f'\nWellicht heeft u niet de juiste api-key opgegeven. Uw invoer= {key}\n')
      
    if response.status_code != 200:
        exit(f'\napi-call mislukt: foutcode= {response.status_code}; {response.text}\n')
    
    jfile = json.loads(response.text)
    df = pd.DataFrame(jfile['result']['records'])
    
    # sommige data moet worden aangepast:
    # https://ckan-dataplatform-nl.dataplatform.nl/dataset/
    #       near-real-time-onbewerkte-snuffelfiets-gegevens-provincie-utrecht
    df['pm1_0'] = np.where(df['version_major']>='2', df['pm1_0']/100, df['pm1_0'])
    df['pm2_5'] = np.where(df['version_major']>='2', df['pm2_5']/100, df['pm2_5'])
    df['pm10'] = np.where(df['version_major']>='2', df['pm10']/100, df['pm10'])
    df['temperature'] = df['temperature'] / 10
    df['pressure'] = df['pressure'] * 100
    df['voltage'] = 3 + (df['voltage'] / 10)

    # '_full_text' is een column, waar alle gegevens nog 'n keer instaan als een lange string ('gescheiden)
    df = df.drop('_full_text', axis=1)  
               
    print(f'\nEr worden {len(df)} regels weg geschreven naar {output_file_name} !')
    df.to_csv(output_file_name, sep=sep_output, decimal=decimal_output, index=False)

    return f'{time.time() - start_time}'


if __name__ == '__main__':
    duur = call_api()
    print(f'\nProgramma is afgelopen. Benodigde tijd was: {duur}.\n')
    