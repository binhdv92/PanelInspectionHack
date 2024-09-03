
from datetime import datetime
from typing import Optional, List
import os
__file__ = os.path.realpath(__file__)

class Core():
    ConnectionStringOrigin = 'Driver={SQL Server};Server=__SitePlant__;Database=ODS;Trusted_Connection=yes'
    ConnectionStringSQLAlchemy = f'mssql://PGT1MESSQLODS.FS.LOCAL/MesReporting?trusted_connection=yes&driver=ODBC Driver 17 for SQL Server'
    
def DataFrame2Pydantic(df, pydantic_model)->List:
    columns = df.columns
    fields = pydantic_model.__fields__
    # Create dictionary of field values from dataframe rows
    values = df.to_dict('records')
    # Create list of Pydantic model instances from dictionary of field values
    instances = [pydantic_model.parse_obj({k: str(v) for k, v in row.items() if k in fields}) for row in values]
    return instances

def Mylog(source:Optional[str]='', log:str=''):
    temp =''
    temp_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temp = f'{temp_datetime}:\t{source}:\t{log}'
    print(temp)
    return temp