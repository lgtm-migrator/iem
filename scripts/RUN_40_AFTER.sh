#Run at 40 minutes after the hour, there are some expensive scripts here
YYYY6=$(date -u --date '6 hours ago' +'%Y')
MM6=$(date -u --date '6 hours ago' +'%m')
DD6=$(date -u --date '6 hours ago' +'%d')
HH6=$(date -u --date '6 hours ago' +'%H')

cd dl
python download_ffg.py &
python download_hrrr.py &
python download_nam.py $(date -u --date '3 hours ago' +'%Y %m %d %H') &

cd ../rtma
python wind_power.py &

cd ../qc
python check_webcams.py
python check_isusm_online.py

cd ../iemplot
./RUN.csh

cd ../ingestors/squaw
python ingest_squaw.py

cd ../scan
python scan_ingest.py

cd ../madis
python extract_madis.py
python extract_hfmetar.py 0 &

cd ../cocorahs
python cocorahs_stations.py IA
python cocorahs_data_ingest.py IA

cd ../../plots
./RUN_PLOTS
cd black
./surfaceContours.csh

cd ../../model
python motherlode_ingest.py $YYYY6 $MM6 $DD6 $HH6
