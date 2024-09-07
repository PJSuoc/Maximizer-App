#! /bin/bash

for f in *.geojson; do
    echo ${f%.*}
    base_filename=${f%.*}
    echo $base_filename
cat "${base_filename}.geojson" | dirty-reproject --forward albersUsa > "${base_filename}_albers.geojson"
done
