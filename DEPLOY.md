docker network create my-net

docker run --net my-net -e POSTGRES_HOST_AUTH_METHOD=trust --name postgres2 -p5432:5432 -d postgres

Enable PostGis

docker exec -it postgres2 bash

apt-get update

apt-get install postgresql-14-postgis-3

# Dockerfile
https://github.com/postgis/docker-postgis/blob/4eb614133d6aa87bfc5c952d24b7eb1f499e5c7c/12-3.0/Dockerfile

# init postgis
https://github.com/postgis/docker-postgis/blob/4eb614133d6aa87bfc5c952d24b7eb1f499e5c7c/12-3.0/initdb-postgis.sh

su postgres

docker build . --tag mapseedapi

docker run --name mapseedapi -p8010:8010 --net my-net -e DEBUG=True -e HOST=postgres2 -d mapseedapi


docker stop mapseedapi && docker rm mapseedapi


docker exec mapseedapi python src/manage.py migrate

docker exec -it mapseedapi python src/manage.py createsuperuser