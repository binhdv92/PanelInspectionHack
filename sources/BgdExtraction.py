#!C:\Program Files\Python39\python.exe

from sources.core import Mylog
import pyodbc, logging
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from sources.AppConfig import Config
import pandas as pd
from pydantic import BaseModel
from datetime import datetime, timezone
import re
from sqlalchemy import create_engine, MetaData, Table, update
from sqlalchemy.orm import sessionmaker
from numpy import isnan
from pandas import Timestamp
from numbers import Number
import PIL.ImageGrab as IG
from PIL import Image
import pyodbc
import time, os, psutil, subprocess, win32api, keyboard, win32con

import os
__file__ = os.path.realpath(__file__)

class BgdBacklog(BaseModel):
    ID:Optional[int]=None
    FpiSourcePath:Optional[str]=None
    ResultRootPath:Optional[str]=None
    SubIdCorrected:Optional[str]=None
    FlagFpiDestPath:Optional[str]=None
    FlagImagePath:Optional[str]=None
    FlagCAPath:Optional[str]=None
    FlagTraceabilityPath:Optional[str]=None
    ExtractSubId:Optional[str]=None
    ExtractFpiSize:Optional[int]=None
    ExtractAlarmName:Optional[str]=None
    ExtractSitePlant:Optional[str]=None
    ExtractEquipment:Optional[str]=None
    ExtractTimeStamp:Optional[datetime]=None
    ExtractModifiedTimeUTC:Optional[datetime]=None
    ExtractIsDummyMode:Optional[bool]=None
    TimeStamp:Optional[datetime]=None
    TimeStampUtc:Optional[datetime]=None
    ModifiedTimeStampUtc:Optional[datetime]=None
    FlagSendingEmail:Optional[str]=None
    LastModifiedUser:Optional[str]=None
    ComputerName:Optional[str]=None

class DataSourceConfig():
    paths:list
    data:list
    def __init__(self, paths:list = Config.fpiSources):
        self.paths = paths
        self.load()
    def load(self):
        self.data = []
        for path in self.paths:
            with open(path,'r') as f:
                lines = f.readlines()
                for i,v in enumerate(lines):
                    v=v.strip()
                    temp =re.search('^#',v)
                    if(temp == None and v):
                        self.data.append(v)
    def prints(self):
        for i in self.data:
            print(i)

def FpiSourcesListDir(fpiSources:List):
    temp=[]

    for fpiSource in fpiSources:
        listDirs = os.listdir(os.path.normpath(fpiSource))
        for listDir in listDirs:
            if(listDir.lower().endswith(('.fpi','.fpih'))):
                temp.append(os.path.normpath(os.path.join(fpiSource.lower(),listDir.lower())))
    return temp

def insert_or_update(fpiSourcePath:str,Source:str):
    try:
        with pyodbc.connect(Config.ConnectionString, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'''INSERT INTO MesReporting.IntRi.BgdBacklog([FpiSourcePath],ComputerName, Source)
                            VALUES(?,?,?)''',fpiSourcePath,os.environ["COMPUTERNAME"],Source)
            conn.commit()   
        logging.debug(f'inserted to Database [{fpiSourcePath}]')
    except Exception as e: 
        logging.error(e)
        
def merge(fpiSourcePath:str, Source:str):
    Mylog('merge()','Start:')
    Mylog('merge()',f'merging fpiSourcePath={fpiSourcePath}, Source={Source}')
    try:
        with pyodbc.connect(Config.ConnectionString, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'''MERGE INTO MesReporting.IntRi.BgdBacklog AS A
                                    USING(
                                        SELECT FpiSourcePath=?, ComputerName=?, TimeStamp = GETDATE(), TimeStampUtc = GETUTCDATE(), LastModifiedUser = SYSTEM_USER, Source=?
                                    ) AS B ON (A.FpiSourcePath = B.FpiSourcePath)
                                    WHEN MATCHED THEN UPDATE SET A.ComputerName = B.ComputerName, A.TimeStamp = B.TimeStamp, A.TimeStampUtc = B.TimeStampUtc, A.LastModifiedUser = B.LastModifiedUser, A.Source = B.Source
                                    WHEN NOT MATCHED THEN INSERT (FpiSourcePath, ComputerName, TimeStamp, TimeStampUtc, LastModifiedUser, Source) VALUES(B.FpiSourcePath, B.ComputerName, B.TimeStamp, B.TimeStampUtc, B.LastModifiedUser, B.Source);''',fpiSourcePath,os.environ["COMPUTERNAME"],Source)
            conn.commit()   
        logging.debug(f'merge(): OK: Merged to Database fpiSourcePath=[{fpiSourcePath}]')
    except Exception as e: 
        logging.error(f'merge(): Failed: error={e}')
      
def insert_or_updates(fpiSourcePaths:List,Source:str):
    for fpiSourcePath in fpiSourcePaths:
        insert_or_update(fpiSourcePath)

def merges(fpiSourcePaths:List, source:str):
    Mylog('merges()', 'Start:')
    '''
    fpiSourcePaths=[
        r'\\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\PGT3\PGT3_DrSchwab\CdCl_A_Bad_Results\PGT31A_240418803327_2024-04-18_16-14-03.FPIH',
        r'\\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\PGT3\PGT3_DrSchwab\CdCl_A_Bad_Results\PGT31A_240410794897_2024-04-18_16-13-35.FPIH'
    ]
    '''
    for fpiSourcePath in fpiSourcePaths:
        merge(fpiSourcePath,source)


def DataFrame2Pydantic(df, pydantic_model)->List:
    fields = pydantic_model.model_fields
    values = df.to_dict('records')
    # inside your DataFrame2Pydantic function
    instances = []
    for row in values:
        validated_row = {}
        for k, v in row.items():
            if k in fields:
                if (v == 'None' or isinstance(v, Number) and isnan(v)):
                    validated_row[k] = None
                elif isinstance(v, Timestamp):
                    validated_row[k] = str(v)
                elif isinstance(v, int):
                    validated_row[k] = int(v)
                else:
                    validated_row[k] = v
        validated_instance = pydantic_model.model_validate(validated_row)
        instances.append(validated_instance)
    return instances

def GetBacklog() -> List[BgdBacklog]:
    backlogs = List
    conn =create_engine(Config.ConnectionStringSQLAlchemy)
    df = pd.read_sql_query(Config.sql_extraction_get_new_backlog,conn)
    backlogs = DataFrame2Pydantic(df, BgdBacklog)
    return backlogs

def GetBacklogById(ID:int) -> List[BgdBacklog]:
    backlogs = List
    conn =create_engine(Config.ConnectionStringSQLAlchemy)
    sql_extraction = f'''
SELECT TOP 10
	ID,
	FpiSourcePath,
	ResultRootPath,
	SubIdCorrected,
	FlagFpiDestPath,
	FlagImagePath,
	FlagCAPath,
	FlagTraceabilityPath,
	ExtractSubId,
	ExtractFpiSize,
	ExtractAlarmName,
	ExtractSitePlant,
	ExtractEquipment,
	ExtractTimeStamp,
	ExtractModifiedTimeUTC,
	ExtractIsDummyMode,
	TimeStamp,
	TimeStampUtc,
	ModifiedTimeStampUtc,
	FlagSendingEmail,
	LastModifiedUser,
	ComputerName
FROM MesReporting.IntRi.BgdBacklog 
WHERE ID = {ID}'''
    df = pd.read_sql_query(sql_extraction,conn)
    backlogs = DataFrame2Pydantic(df, BgdBacklog)
    return backlogs


def GetBacklogLatest() -> List[BgdBacklog]:
    backlogs = List
    conn =create_engine(Config.ConnectionStringSQLAlchemy)
    sql_extraction = f'''
SELECT TOP 10
	ID,
	FpiSourcePath,
	ResultRootPath,
	SubIdCorrected,
	FlagFpiDestPath,
	FlagImagePath,
	FlagCAPath,
	FlagTraceabilityPath,
	ExtractSubId,
	ExtractFpiSize,
	ExtractAlarmName,
	ExtractSitePlant,
	ExtractEquipment,
	ExtractTimeStamp,
	ExtractModifiedTimeUTC,
	ExtractIsDummyMode,
	TimeStamp,
	TimeStampUtc,
	ModifiedTimeStampUtc,
	FlagSendingEmail,
	LastModifiedUser,
	ComputerName
FROM MesReporting.IntRi.BgdBacklog 
ORDER BY ID DESC'''
    df = pd.read_sql_query(sql_extraction,conn)
    backlogs = DataFrame2Pydantic(df, BgdBacklog)
    return backlogs

def FpiExtraction(backlog:BgdBacklog)->BgdBacklog:
    '''

    '''
    #### find subid
    ExtractSubId=''
    subid_type=''
    ## group 01: c12
    pattern01    = re.search('[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]',backlog.FpiSourcePath.lower())
    ## group 02: c11
    pattern01_02 = re.search("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",backlog.FpiSourcePath.lower())
    ## group 03: virtual subid
    pattern03 = re.search('[a-zA-Z][0-9][0-9][a-zA-Z][a-zA-Z][0-9][0-9]',backlog.FpiSourcePath.lower())
    if pattern03 != None:
        startid=pattern03.start()
        endid = startid+19
        ExtractSubId = backlog.FpiSourcePath.lower()[startid:endid]
        subid_type='virtual_subid'
    elif pattern01 != None:
        startid=pattern01.start()
        endid = startid+12
        ExtractSubId = backlog.FpiSourcePath.lower()[startid:endid]
        subid_type='valid_subid_c12'
    elif pattern01_02 != None:
        startid=pattern01_02.start()
        endid = startid+11
        ExtractSubId = backlog.FpiSourcePath.lower()[startid:endid]
        subid_type='valid_subid_c11'

    ##### find Alarm ID
    # 03Feb2023: \\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\PGT3\PGT3_DrSchwab\CoverGlass_B_Bad_Results\FS_BGD_PGT3_CVR_B_1_2023-02-02-11-42-46.FPIH
    ExtractAlarmName = ''
    if (r'drschwab\cdcl' in backlog.FpiSourcePath.lower() or r'drschwab\pgt12_cdcl' in backlog.FpiSourcePath.lower()):
        ExtractAlarmName = 'CdCl'
    elif r'drschwab\arc' in backlog.FpiSourcePath.lower():
        ExtractAlarmName = 'ARC'
    elif r'drschwab\cover_glass' in backlog.FpiSourcePath.lower():
        ExtractAlarmName = 'CoverGlass'
    elif r'drschwab\coverglass' in backlog.FpiSourcePath.lower():
        ExtractAlarmName = 'CoverGlass'

    ##### find plant name
    ExtractSitePlant = ''
    if  (r"dmt1\dmt1_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="DMT1"
    elif(r"dmt2\dmt2_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="DMT2"
    elif(r"kmt1\kmt1_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="KMT1"   
    elif(r"kmt2\kmt2_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="KMT2"    
    elif(r"pgt1\pgt1_drschwab" in backlog.FpiSourcePath.lower().lower()):
        if(r"pgt1\pgt1_drschwab\pgt12" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="PGT12"  
        else: ExtractSitePlant="PGT1"          
    elif(r"pgt2\pgt2_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="PGT2" 
    elif(r"pgt3\pgt3_drschwab" in backlog.FpiSourcePath.lower().lower()): ExtractSitePlant="PGT3"
        
    #### find dummy mode
    ExtractIsDummyMode = False
    if('__dummy__' in backlog.FpiSourcePath.lower()): ExtractIsDummyMode=True
        
    ##### get size
    temp_constant_MB = 1048576
    try:
        size_file = os.path.getsize(backlog.FpiSourcePath.lower())
        ExtractFpiSize = round(size_file/temp_constant_MB)
    except Exception as e:
        ExtractFpiSize = None
        Mylog('FpiExtraction()', f'Failed: error={e}')
    
    fpi_src_path_head,fpi_src_abspath_tail02 = os.path.split(backlog.FpiSourcePath.lower())
    fpi_src_abspath_tail    = fpi_src_abspath_tail02.lower().replace('.fpi','').replace('.fpih','')
    ResultRootPath          = os.path.join(Config.ResultRootPath_prefix,ExtractSubId)
    FpiDestPath             = fpi_src_abspath_tail
    ImagePath               = f'{fpi_src_abspath_tail}.png'
    TraceabilityPath        = f'{fpi_src_abspath_tail}_traceability.html'
    CommonalityAnalysisPath = f'{fpi_src_abspath_tail}_ca.html'
    ImagePathScreenShoot    = f'{fpi_src_abspath_tail}_screenshoot.png'                                   
    ImagePath01             = f'{fpi_src_abspath_tail}_01_00.png'

    ##### datetime
    ExtractTimeStamptemp = ''
    var_datetime_type = ''
    # 2021-08-02-15-53-13
    pattern_datetime_01    = re.search('[2][0][2][0-9][-][0-1][0-9][-][0-3][0-9][-][0-2][0-9][-][0-5][0-9][-][0-5][0-9]',backlog.FpiSourcePath.lower())
    pattern_datetime_02    = re.search('[2][0][2][0-9][-][0-1][0-9][-][0-3][0-9][_][0-2][0-9][-][0-5][0-9][-][0-5][0-9]',backlog.FpiSourcePath.lower())
    try:
        #ExtractModifiedTimeUTC = datetime.utcfromtimestamp(os.path.getmtime(backlog.FpiSourcePath.lower()))
        ExtractModifiedTimeUTC = datetime.fromtimestamp(os.path.getmtime(backlog.FpiSourcePath.lower()), timezone.utc)
    except:
        ExtractModifiedTimeUTC = datetime(2000,1,1,1,1,1)
    if pattern_datetime_01 != None:
        startid_time      = pattern_datetime_01.start()
        endid_datetime    = startid_time+19
        ExtractTimeStamptemp      = backlog.FpiSourcePath.lower()[startid_time:endid_datetime]
        ExtractTimeStamptemp     = ExtractTimeStamptemp[0:10]+' '+ExtractTimeStamptemp[11:13]+':'+ExtractTimeStamptemp[14:16]+':'+ExtractTimeStamptemp[17:]
        ExtractTimeStamp = datetime.strptime(ExtractTimeStamptemp, "%Y-%m-%d %H:%M:%S")
        var_datetime_type = 'type-'
    elif pattern_datetime_02 != None:
        startid_time    = pattern_datetime_02.start()
        endid_datetime    = startid_time+19
        ExtractTimeStamptemp      = backlog.FpiSourcePath.lower()[startid_time:endid_datetime]
        ExtractTimeStamptemp      = ExtractTimeStamptemp[0:10]+' '+ExtractTimeStamptemp[11:13]+':'+ExtractTimeStamptemp[14:16]+':'+ExtractTimeStamptemp[17:]
        ExtractTimeStamp = datetime.strptime(ExtractTimeStamptemp, "%Y-%m-%d %H:%M:%S")
        var_datetime_type = 'type_'
    else:
        ExtractTimeStamp = datetime(2000,1,1,1,1,1)

    ExtractEquipment = os.path.split(os.path.split(os.path.normpath(backlog.FpiSourcePath.lower()))[0])[1]

    backlog.ResultRootPath = ResultRootPath
    backlog.ExtractSubId = ExtractSubId
    backlog.ExtractFpiSize = ExtractFpiSize
    backlog.ExtractAlarmName = ExtractAlarmName
    backlog.ExtractSitePlant = ExtractSitePlant
    backlog.ExtractEquipment = ExtractEquipment
    backlog.ExtractTimeStamp = ExtractTimeStamp
    backlog.ExtractModifiedTimeUTC = ExtractModifiedTimeUTC
    backlog.ExtractIsDummyMode = ExtractIsDummyMode
    return backlog

def FpiExtractions(backlogs:List)-> List[BgdBacklog]: 
    return [FpiExtraction(v) for i,v in enumerate(backlogs)]


def UpdateDataToDatabase(backlogs:List[BgdBacklog]):
    Mylog('UpdateDataToDatabase','Start:')
    # create engine
    engine = create_engine(Config.ConnectionStringSQLAlchemy)
    Session = sessionmaker(bind=engine)
    session = Session()

    # reflect the table
    metadata = MetaData()
    bgd_backlog = Table('BgdBacklog', metadata, autoload_with=engine, schema='IntRi')

    # iterate over backlogs2 and update the rows in the database
    for backlog in backlogs:
        temp=backlog.model_copy()
        stmt = update(bgd_backlog).where(bgd_backlog.c.ID == temp.ID).values(**temp.model_dump(exclude={'ID'}))
        session.execute(stmt)

    session.commit()
    Mylog('UpdateDataToDatabase','End:')


class CommentSet():
    PanelInspection             = [70, 18]
    PanelInspectionFile         = [17, 47]
    PanelInspectionPosDropFile  = [200, 200]
    explorerPos                 = [1753, 12]
    explorerPosSearch           = [1800, 75]
    explorerPosPickFile         = [1900, 132]
    positionWindowBox           = [130,60]
    statusWindowBox             = (116,42,212,68)
    statusWindowBox2            = (130,60,135+100,55+100)
    statusReady                 = (0,200,0)
    statusBusy                  = (200,80, 200)
    statusNone                  = (240, 240, 240)

def leftClick( pos):
    Mylog('leftClick()', 'Start:')
    win32api.SetCursorPos(pos)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, pos[0], pos[1], 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, pos[0], pos[1], 0, 0)
    Mylog('leftClick()',f'clicked pos={pos})')

def press_and_releaseX(key, x, delay):
    Mylog('press_and_releaseX()','Start:')
    for i in range(x):
        keyboard.press_and_release(key)     
        time.sleep(delay)
    Mylog('press_and_releaseX()', f'Pressed key={key}')

def find_windows_exists(name = 'PanelInspection'):
    Mylog('find_windows_exists()','Start:')
    pid=''
    for i in psutil.process_iter():
        if('PanelInspection' in i.name()):
            flag=True
            pid=i.pid
    Mylog('find_windows_exists()', f'pid={pid}' )
    return pid

def Exit_PanelInspection(delay = 0.2):
    Mylog('Exit_PanelInspection()', 'Start:')
    leftClick(CommentSet.PanelInspection)
    press_and_releaseX('Enter', x=10, delay=delay)
    pid = find_windows_exists()
    if(pid):
        p = psutil.Process(pid)
        p.terminate()
        Mylog('Exit_PanelInspection()', f'OK: Exited PanelInspection pid={pid}')
    else:
        Mylog('Exit_PanelInspection()', f'Failed: do not exist any PanelInspection pid={pid} ')

def Check_PanelInspection():
    Mylog('Check_PanelInspection()','Start:')
    pid = find_windows_exists()
    if pid != '':
        Mylog('Check_PanelInspection()', 'PanelInspection pid={pid} is opening')
    else:
        Mylog(Check_PanelInspection, "PanelInspection is not opening, let's open it")
        time.sleep(1)
        app = subprocess.Popen(r'PanelInspection.exe')
        Mylog(Check_PanelInspection, 'waiting 4 seconds')
        time.sleep(4)
        leftClick(CommentSet.PanelInspection)
        press_and_releaseX('Enter', x=20, delay=0.2)
        
        # setting_app()
        pid = find_windows_exists()
        Mylog('Check_PanelInspection()', f'OK: Opened the PanelInspection pid={app.pid}')

def Close_PanelInspection(repeat = 10, delay = 0.2, waitTimeMiniStep = 0.2):
    Mylog('Close_PanelInspection()','Start:')
    leftClick(CommentSet.PanelInspection)
    press_and_releaseX('Enter', x=10, delay=delay)
    keyboard.press_and_release('Alt')
    time.sleep(waitTimeMiniStep)
    keyboard.press_and_release('f')
    time.sleep(waitTimeMiniStep)
    keyboard.press_and_release('c')
    time.sleep(waitTimeMiniStep)
    press_and_releaseX('Enter', x=repeat, delay=0.2)
    Mylog('Close_PanelInspection()','End:')

def open_fpi(FpiSourcePath: str, waitTimeMiniStep = 0.1,waitTimeEachStep = 1):
    Mylog('open_fpi()','Start:')
    flag=False
    if(os.path.exists(FpiSourcePath)):
        Mylog('open_fpi()', 'start')
        ### Step01 clear PanelInspection
        Mylog('open_fpi()', 'step01 clear PanelInspection before loading fpi file')
        leftClick(CommentSet.PanelInspection)

        time.sleep(waitTimeMiniStep)
        press_and_releaseX('Enter', 10, 0.1)
        time.sleep(waitTimeMiniStep)
        press_and_releaseX('ESC', 10, 0.1)
        time.sleep(waitTimeEachStep)

        # Step01: load fpi file
        Mylog('open_fpi()', 'openFPI step02 load fpi file')
        leftClick(CommentSet.PanelInspection)
        press_and_releaseX('Enter', x=10, delay=0.1)
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('alt')
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('f')
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('l')
        time.sleep(waitTimeMiniStep)
        time.sleep(2)
        keyboard.write(FpiSourcePath)
        time.sleep(3)
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('Enter')
        time.sleep(waitTimeMiniStep)
        
        time.sleep(waitTimeEachStep)
        press_and_releaseX('Enter', 10, 0.1)
        
        press_and_releaseX('Enter', 10, 0.1)
        time.sleep(waitTimeMiniStep)
        
        press_and_releaseX('Enter', 10, 0.1)
        time.sleep(waitTimeMiniStep)
        
        press_and_releaseX('Enter', 10, 0.1)
        time.sleep(waitTimeMiniStep)
        
        press_and_releaseX('Enter', 10, 0.1)
        time.sleep(waitTimeMiniStep)

        press_and_releaseX('ESC', 10, 0.1)
        time.sleep(waitTimeMiniStep)
        Mylog('open_fpi()', 'sucessfull')
        flag=True
    else:
        Mylog('open_fpi()', f'Failed: do not exist FpiSourcePath={FpiSourcePath}')
        flag=False
    Mylog('open_fpi()','End:')
    return flag

def saveScreenShoot(ImagePathScreenShoot, waitTimeMiniStep = 0.1, waitTimeEachStep = 1):
    Mylog('saveScreenShoot()','Start:')
    img = IG.grab()
    try:
        #img.save(metadata['png_dest_file_abspath_screenshoot'])
        img.save(ImagePathScreenShoot)
        Mylog('saveScreenShoot()', f'OK: saved ImagePathScreenShoot={ImagePathScreenShoot}')
    except:
        Mylog('saveScreenShoot()', f'Failed: to save ImagePathScreenShoot={ImagePathScreenShoot}')
    time.sleep(waitTimeEachStep)
    Mylog('saveScreenShoot()','End:')

def saveImageToPNG(ImagePath:FpiSourcesListDir, waitTimeMiniStep = 0.2,waitTimeEachStep = 1):
    Mylog('saveImageToPNG()', 'Start:')
    flag_saveImageToPNG = False
    try:
        leftClick(CommentSet.PanelInspection)
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('Alt')
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('f')
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('S')
        time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('S')
        time.sleep(waitTimeMiniStep)
        #keyboard.press_and_release('S')
        #time.sleep(waitTimeMiniStep)
        keyboard.press_and_release('Enter')
        time.sleep(waitTimeMiniStep)
        time.sleep(2)
    
        Mylog('saveImageToPNG()', f'save to PNG: ImagePath={ImagePath}')
        #keyboard.write(metadata['png_dest_file_abspath'])
        keyboard.write(ImagePath)
        time.sleep(3)
        keyboard.press_and_release('Enter')
        time.sleep(waitTimeMiniStep)
    
        time.sleep(waitTimeEachStep)
        Mylog('saveImageToPNG()', f'OK: saved ImagePath={ImagePath}]')
        
        flag_saveImageToPNG = True
    except:
        Mylog('saveImageToPNG()', f'Failed: to save ImagePath={ImagePath}' )
    # clear ImagePath
    # leftClick(commandSet['PanelInspection']);time.sleep(sleeptime)
    # press_and_releaseX('ESC',10,0.1);
    time.sleep(waitTimeEachStep)

def get_concat_h_blank(image01path:str, image02path:str, imageresult:str,color=(0, 0, 0)):
    Mylog('get_concat_h_blank()','Start:')
    #metadata=load_json_config(r'workspace/metadata.json')
    im1=''
    im2=''
    try:
        im1 = Image.open(image01path)
        im1=im1.resize((1080,1902))
        Mylog('get_concat_h_blank()', f'OK: Opened image01path={image01path}')
    except:
        Mylog('get_concat_h_blank()', f"Failed: not exists: image01path={image01path}")
    
    try:
        im2 = Image.open(image02path)
        Mylog('get_concat_h_blank()', f'OK: Opened image02path={image02path}')
    except:
        Mylog('get_concat_h_blank()', f"Failed: do not exists: image02path={image02path}")
        
    if((im1!='') & (im2!='')):
        dst = Image.new('RGB', (im1.width + im2.width, max(im1.height, im2.height)), color)
        dst.paste(im1, (0, 0))
        dst.paste(im2, (im1.width, 0))
        dst.save(imageresult)
    elif((im1!='') & (im2!='')):
        dst=im1
        dst.save(imageresult)
    elif((im1=='') & (im2!='')):
        dst=im2
        dst.save(imageresult)
    else:
        dst=''
    
def ConcatImage(image01path:str, image02path:str, imageresult:str):
    Mylog('ConcatImage()','Start:')
    Mylog('ConcatImage()', f'concating image02path={image02path} and image02path={image02path}')
    if(os.path.exists(image01path) and os.path.exists(image02path)):
        ### get_concat_v_blank
        try:
            get_concat_h_blank(image01path,image02path,imageresult,(0, 0, 0))
            Mylog('ConcatImage()', f'OK get_concat_h_blank: OK')
        except Exception as e:
            Mylog('ConcatImage()', f'Failed: error={e}')
    else:
        Mylog('ConcatImage()', f'Failed: do not existing image01path={image01path} or image02path={image02path}')
    
class ResultRootPathClass():
    def __init__(self,ResultRootPath:str):
        self.ResultRootPath          = ResultRootPath
        self.ImagePath               = f'{ResultRootPath}.png'
        self.ImagePathScreenShoot    = f'{ResultRootPath}_ScreenShoot.png'
        self.ImagePath01             = f'{ResultRootPath}_01_00.png'

def PanelInspectionGetBacklogs(max:int=10) -> List[BgdBacklog]:
    backlogs = List
    conn =create_engine(Config.ConnectionStringSQLAlchemy)
    sql_extraction = f'''
SELECT TOP {max}
	ID,
	FpiSourcePath,
	ResultRootPath,
	SubIdCorrected,
	FlagFpiDestPath,
	FlagImagePath,
	FlagCAPath,
	FlagTraceabilityPath,
	ExtractSubId,
	ExtractFpiSize,
	ExtractAlarmName,
	ExtractSitePlant,
	ExtractEquipment,
	ExtractTimeStamp,
	ExtractModifiedTimeUTC,
	ExtractIsDummyMode,
	TimeStamp,
	TimeStampUtc,
	ModifiedTimeStampUtc,
	FlagSendingEmail,
	LastModifiedUser,
	ComputerName
FROM MesReporting.IntRi.BgdBacklog 
WHERE FlagImagePath IS NULL
ORDER BY TimeStamp DESC'''
    df = pd.read_sql_query(sql_extraction,conn)
    backlogs = DataFrame2Pydantic(df, BgdBacklog)
    return backlogs

def PanelInspectionExe(FpiSourcePath:str,ResultRootPath:str):
    Mylog('PanelInspectionExe()','Start:')
    Mylog('PanelInspectionExe()', f'********************************************** FpiSourcePath={FpiSourcePath}')
    result_root_path = ResultRootPathClass(ResultRootPath)
    if(os.path.exists(FpiSourcePath)):
        Mylog('PanelInspectionExe()', f'FpiSourcePath={FpiSourcePath}')
        Check_PanelInspection()
        Close_PanelInspection()
        flagOpen = open_fpi(FpiSourcePath)
        if(flagOpen):
            time.sleep(2)
            saveScreenShoot(result_root_path.ImagePathScreenShoot)
            time.sleep(1)
            saveImageToPNG(result_root_path.ImagePath)
            time.sleep(1)
            press_and_releaseX('Enter', 10, 0.1)
            time.sleep(1)
            press_and_releaseX('Enter', 10, 0.1)
            time.sleep(1)
            press_and_releaseX('Enter', 10, 0.1)
            if(os.path.exists(result_root_path.ImagePath01)):
                ConcatImage(result_root_path.ImagePath01, result_root_path.ImagePathScreenShoot, result_root_path.ImagePath)
                Mylog('PanelInspectionExe()', 'OK: OpenFPI successful')
            else:
                Mylog('PanelInspectionExe()', f'Failed: do not exist ImagePath01={result_root_path.ImagePath01}')
        else:
            Mylog('PanelInspectionExe()', 'Failed: flagOpen() is failed to open PanelInspection.exe')
    else:
        Mylog('PanelInspectionExe()', f'Failed: do not exist the FpiSourcePath = {FpiSourcePath}')
    response = ''
    if(os.path.exists(result_root_path.ImagePath)):
        response = 1
    else:
        response=2
    return response