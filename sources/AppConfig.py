#!C:\Program Files\Python39\python.exe

class Config():
    fpiSourcePathDummy=[
        r'\\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\PGT3\PGT3_DrSchwab\CdCl_A_Bad_Results\PGT31A_240418803327_2024-04-18_16-14-03.FPIH',
        r'\\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\PGT3\PGT3_DrSchwab\CdCl_A_Bad_Results\PGT31A_240410794897_2024-04-18_16-13-35.FPIH'
    ]
    ResultRootPath_prefix = r'\\FS.LOCAL\FSGlobal\Global\Shared\Manufacturing\Global\MES\ImageMart\BdgImages'
    root_path = r'c:/repo-mes/Global_BGD_Breakage_Alerts_V02'
    ConnectionStringOrigin = 'Driver={SQL Server};Server=__SitePlant__;Database=MesReporting;Trusted_Connection=yes'
    ConnectionString = 'Driver={SQL Server};Server=PGT1MESSQLODS.FS.LOCAL;Database=MesReporting;Trusted_Connection=yes'
    ConnectionStringSQLAlchemy = f'mssql://PGT1MESSQLODS.FS.LOCAL/MesReporting?trusted_connection=yes&driver=ODBC Driver 17 for SQL Server'
    fpiSources = [r'sources/fpi_sources.dat',r'sources/fpi_sources_dummy.dat']
    logging_format = '%(asctime)s:%(levelname)s:%(message)s'
    logging_filename = 'logs/service_01_watchdog.log'
    class watchdog():
        patterns: list =['*.fpi','*.fpih']; ignorePatterns=None; ignoreDirectories =False; caseSensitive = False
    sql_extraction_get_new_backlog = '''
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
WHERE ExtractSubId IS NULL
ORDER BY TimeStamp DESC'''