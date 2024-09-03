from fastapi import FastAPI, Query, Form, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
import os, shutil

from sources.BgdExtraction import Exit_PanelInspection, PanelInspectionExe
from sources.core import Mylog

##
rootpath = os.getcwd()
workspacespath= os.path.join(rootpath,'workspaces')

def myClearWorkspaces():
    Mylog("myClearWorkspaces",'Start:')
    response = ''
    # Delete workpaces
    try: 
        shutil.rmtree(workspacespath)
        response = f'OK Cleared {workspacespath}'
    except Exception as e: 
        response = Mylog("api",f'Delete workpaces error: {e}')

        
    # Create the workspaces folder
    try: os.mkdir(workspacespath)
    except Exception as e: Mylog("api",f' Create the workspaces folder error: {e}')
    return response
myClearWorkspaces()

app = FastAPI()

@app.get("/",response_class=FileResponse)
def root():
    return FileResponse(r'sources/index.html')

@app.get("/ClearWorkspaces",response_class=HTMLResponse)
def ClearWorkspaces():
    return myClearWorkspaces()

@app.post("/PanelInspectionHack/",response_class=FileResponse)
async def PanelInspectionHack(file: UploadFile = File(...)) :
    Mylog('PanelInspectionHack','Start:')
    Mylog('PanelInspectionHack','myClearWorkspaces()')
    myClearWorkspaces()

    filename_norm = file.filename
    FpiSourcePath = os.path.normpath(os.path.join(workspacespath, f'{file.filename}'))
    temp2 = filename_norm.lower().replace('.fpih','.fpi')
    OutputImagePath = os.path.normpath(os.path.join(workspacespath,f'{temp2[:-4]}'))
    OutputImagePathPng = os.path.normpath(os.path.join(workspacespath,f'{temp2[:-4]}.png'))

    Mylog('PanelInspectionHack',f'filename_norm: {filename_norm}')
    Mylog('PanelInspectionHack',f'FpiSourcePath: {FpiSourcePath}')
    Mylog('PanelInspectionHack',f'OutputImagePath: {OutputImagePath}')
    Mylog('PanelInspectionHack',f'OutputImagePathPng: {OutputImagePathPng}')

    if(os.path.isfile(OutputImagePathPng)):
        return FileResponse(OutputImagePathPng)
    else:
        #saving
        with open(FpiSourcePath, "wb+") as f:
            f.write(file.file.read())

        #extracting
        Exit_PanelInspection()
        PanelInspectionExe(FpiSourcePath, OutputImagePath)
        Exit_PanelInspection()

    return FileResponse(OutputImagePathPng)